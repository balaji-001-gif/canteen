import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 130},
        {"label": "Total Orders", "fieldname": "total_orders", "fieldtype": "Int", "width": 110},
        {"label": "Total Amount", "fieldname": "total_amount", "fieldtype": "Currency", "width": 130},
        {"label": "Wallet Usage", "fieldname": "wallet_amount", "fieldtype": "Currency", "width": 130},
    ]


def get_data(filters):
    conditions = "pi.docstatus = 1 AND pi.is_return = 0 AND pi.canteen_employee IS NOT NULL"
    params = {}

    if filters.get("from_date"):
        conditions += " AND pi.posting_date >= %(from_date)s"
        params["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND pi.posting_date <= %(to_date)s"
        params["to_date"] = filters["to_date"]
    if filters.get("department"):
        conditions += " AND e.department = %(department)s"
        params["department"] = filters["department"]

    return frappe.db.sql(f"""
        SELECT
            pi.canteen_employee AS employee,
            e.employee_name,
            e.department,
            COUNT(pi.name) AS total_orders,
            SUM(pi.grand_total) AS total_amount,
            SUM(CASE 
                WHEN pm.mode_of_payment = 'Wallet' THEN pm.amount 
                ELSE 0 
            END) AS wallet_amount
        FROM `tabPOS Invoice` pi
        LEFT JOIN `tabEmployee` e ON e.name = pi.canteen_employee
        LEFT JOIN `tabPOS Invoice Payments` pm ON pm.parent = pi.name
        WHERE {conditions}
        GROUP BY pi.canteen_employee
        ORDER BY total_amount DESC
    """, params, as_dict=True)
