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
    conditions = "co.docstatus = 1 AND co.employee IS NOT NULL"

    if filters.get("from_date"):
        conditions += f" AND co.order_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND co.order_date <= '{filters['to_date']}'"
    if filters.get("department"):
        conditions += f" AND e.department = '{filters['department']}'"

    return frappe.db.sql(f"""
        SELECT
            co.employee,
            co.employee_name,
            e.department,
            COUNT(co.name) AS total_orders,
            SUM(co.total_amount) AS total_amount,
            SUM(CASE WHEN co.payment_mode = 'Wallet' THEN co.total_amount ELSE 0 END) AS wallet_amount
        FROM `tabCanteen Order` co
        LEFT JOIN `tabEmployee` e ON e.name = co.employee
        WHERE {conditions}
        GROUP BY co.employee
        ORDER BY total_amount DESC
    """, as_dict=True)
