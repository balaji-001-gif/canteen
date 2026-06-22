import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Date", "fieldname": "order_date", "fieldtype": "Date", "width": 110},
        {"label": "Total Orders", "fieldname": "total_orders", "fieldtype": "Int", "width": 110},
        {"label": "Total Sales", "fieldname": "total_sales", "fieldtype": "Currency", "width": 130},
        {"label": "Cash", "fieldname": "cash_sales", "fieldtype": "Currency", "width": 120},
        {"label": "Card", "fieldname": "card_sales", "fieldtype": "Currency", "width": 120},
        {"label": "UPI", "fieldname": "upi_sales", "fieldtype": "Currency", "width": 120},
        {"label": "Wallet", "fieldname": "wallet_sales", "fieldtype": "Currency", "width": 120},
        {"label": "Credit", "fieldname": "credit_sales", "fieldtype": "Currency", "width": 120},
        {"label": "Tax", "fieldname": "total_tax", "fieldtype": "Currency", "width": 110},
        {"label": "Discount", "fieldname": "total_discount", "fieldtype": "Currency", "width": 110},
    ]


def get_data(filters):
    conditions = "docstatus = 1"

    if filters.get("from_date"):
        conditions += f" AND order_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND order_date <= '{filters['to_date']}'"

    return frappe.db.sql(f"""
        SELECT
            order_date,
            COUNT(name) AS total_orders,
            SUM(total_amount) AS total_sales,
            SUM(CASE WHEN payment_mode='Cash' THEN total_amount ELSE 0 END) AS cash_sales,
            SUM(CASE WHEN payment_mode='Card' THEN total_amount ELSE 0 END) AS card_sales,
            SUM(CASE WHEN payment_mode='UPI' THEN total_amount ELSE 0 END) AS upi_sales,
            SUM(CASE WHEN payment_mode='Wallet' THEN total_amount ELSE 0 END) AS wallet_sales,
            SUM(CASE WHEN payment_mode='Credit' THEN total_amount ELSE 0 END) AS credit_sales,
            SUM(tax_amount) AS total_tax,
            SUM(discount_amount) AS total_discount
        FROM `tabCanteen Order`
        WHERE {conditions}
        GROUP BY order_date
        ORDER BY order_date DESC
    """, as_dict=True)
