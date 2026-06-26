import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
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
    conditions = "pi.docstatus = 1 AND pi.is_return = 0"

    if filters.get("from_date"):
        conditions += f" AND pi.posting_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND pi.posting_date <= '{filters['to_date']}'"

    return frappe.db.sql(f"""
        SELECT
            pi.posting_date,
            COUNT(pi.name) AS total_orders,
            SUM(pi.grand_total) AS total_sales,
            SUM(CASE WHEN pm.mode_of_payment = 'Cash' THEN pm.amount ELSE 0 END) AS cash_sales,
            SUM(CASE WHEN pm.mode_of_payment = 'Card' THEN pm.amount ELSE 0 END) AS card_sales,
            SUM(CASE WHEN pm.mode_of_payment = 'UPI' THEN pm.amount ELSE 0 END) AS upi_sales,
            SUM(CASE WHEN pm.mode_of_payment = 'Wallet' THEN pm.amount ELSE 0 END) AS wallet_sales,
            SUM(CASE WHEN pm.mode_of_payment = 'Credit' THEN pm.amount ELSE 0 END) AS credit_sales,
            SUM(pi.total_taxes_and_charges) AS total_tax,
            SUM(pi.discount_amount) AS total_discount
        FROM `tabPOS Invoice` pi
        LEFT JOIN `tabSales Invoice Payment` pm ON pm.parent = pi.name
        WHERE {conditions}
        GROUP BY pi.posting_date
        ORDER BY pi.posting_date DESC
    """, as_dict=True)
