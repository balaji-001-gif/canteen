import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Invoice", "fieldname": "name", "fieldtype": "Link", "options": "POS Invoice", "width": 160},
        {"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 140},
        {"label": "Employee", "fieldname": "canteen_employee_name", "fieldtype": "Data", "width": 140},
        {"label": "Items", "fieldname": "item_count", "fieldtype": "Int", "width": 80},
        {"label": "Subtotal", "fieldname": "net_total", "fieldtype": "Currency", "width": 110},
        {"label": "Tax", "fieldname": "total_taxes_and_charges", "fieldtype": "Currency", "width": 100},
        {"label": "Discount", "fieldname": "discount_amount", "fieldtype": "Currency", "width": 100},
        {"label": "Total", "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
        {"label": "Payment Mode", "fieldname": "payment_modes", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90},
    ]


def get_data(filters):
    conditions = "pi.docstatus = 1 AND pi.is_return = 0"

    if filters.get("from_date"):
        conditions += f" AND pi.posting_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND pi.posting_date <= '{filters['to_date']}'"
    if filters.get("customer"):
        conditions += f" AND pi.customer = '{filters['customer']}'"

    data = frappe.db.sql(f"""
        SELECT
            pi.posting_date,
            pi.name,
            pi.customer_name,
            IF(pi.canteen_employee IS NOT NULL, 
               (SELECT employee_name FROM `tabEmployee` WHERE name = pi.canteen_employee),
               NULL) AS canteen_employee_name,
            (SELECT COUNT(*) FROM `tabPOS Invoice Item` WHERE parent = pi.name) AS item_count,
            pi.net_total,
            pi.total_taxes_and_charges,
            pi.discount_amount,
            pi.grand_total,
            (SELECT GROUP_CONCAT(mode_of_payment SEPARATOR ', ') 
             FROM `tabSales Invoice Payment` WHERE parent = pi.name) AS payment_modes,
            CASE 
                WHEN pi.docstatus = 0 THEN 'Draft'
                WHEN pi.docstatus = 1 THEN 'Submitted'
                WHEN pi.docstatus = 2 THEN 'Cancelled'
            END AS status
        FROM `tabPOS Invoice` pi
        WHERE {conditions}
        ORDER BY pi.posting_date DESC, pi.creation DESC
    """, as_dict=True)

    return data
