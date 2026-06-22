import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Date", "fieldname": "order_date", "fieldtype": "Date", "width": 100},
        {"label": "Order", "fieldname": "name", "fieldtype": "Link", "options": "Canteen Order", "width": 140},
        {"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 140},
        {"label": "Employee", "fieldname": "employee_name", "fieldtype": "Data", "width": 140},
        {"label": "Items", "fieldname": "item_count", "fieldtype": "Int", "width": 80},
        {"label": "Subtotal", "fieldname": "subtotal", "fieldtype": "Currency", "width": 110},
        {"label": "Tax", "fieldname": "tax_amount", "fieldtype": "Currency", "width": 100},
        {"label": "Discount", "fieldname": "discount_amount", "fieldtype": "Currency", "width": 100},
        {"label": "Total", "fieldname": "total_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Payment Mode", "fieldname": "payment_mode", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90},
    ]


def get_data(filters):
    conditions = "docstatus = 1"

    if filters.get("from_date"):
        conditions += f" AND order_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND order_date <= '{filters['to_date']}'"
    if filters.get("payment_mode"):
        conditions += f" AND payment_mode = '{filters['payment_mode']}'"
    if filters.get("cashier"):
        conditions += f" AND cashier = '{filters['cashier']}'"

    data = frappe.db.sql(f"""
        SELECT
            order_date,
            name,
            customer_name,
            employee_name,
            (SELECT COUNT(*) FROM `tabCanteen Order Item` WHERE parent = `tabCanteen Order`.name) AS item_count,
            subtotal,
            tax_amount,
            discount_amount,
            total_amount,
            payment_mode,
            status
        FROM `tabCanteen Order`
        WHERE {conditions}
        ORDER BY order_date DESC, creation DESC
    """, as_dict=True)

    return data
