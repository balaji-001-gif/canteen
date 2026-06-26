import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Data", "width": 130},
        {"label": "Qty Sold", "fieldname": "qty_sold", "fieldtype": "Float", "width": 100},
        {"label": "Revenue", "fieldname": "revenue", "fieldtype": "Currency", "width": 130},
        {"label": "Cost", "fieldname": "cost", "fieldtype": "Currency", "width": 120},
        {"label": "Gross Profit", "fieldname": "gross_profit", "fieldtype": "Currency", "width": 130},
        {"label": "Margin %", "fieldname": "margin_pct", "fieldtype": "Percent", "width": 100},
    ]


def get_data(filters):
    conditions = "pi.docstatus = 1 AND pi.is_return = 0"

    if filters.get("from_date"):
        conditions += f" AND pi.posting_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND pi.posting_date <= '{filters['to_date']}'"

    return frappe.db.sql(f"""
        SELECT
            pii.item_code,
            pii.item_name,
            i.item_group,
            SUM(pii.qty) AS qty_sold,
            SUM(pii.amount) AS revenue,
            SUM(pii.qty * IFNULL(i.valuation_rate, 0)) AS cost,
            SUM(pii.amount) - SUM(pii.qty * IFNULL(i.valuation_rate, 0)) AS gross_profit,
            CASE
                WHEN SUM(pii.amount) > 0
                THEN ROUND((SUM(pii.amount) - SUM(pii.qty * IFNULL(i.valuation_rate, 0))) / SUM(pii.amount) * 100, 2)
                ELSE 0
            END AS margin_pct
        FROM `tabPOS Invoice Item` pii
        JOIN `tabPOS Invoice` pi ON pi.name = pii.parent
        LEFT JOIN `tabItem` i ON i.item_code = pii.item_code
        WHERE {conditions}
        GROUP BY pii.item_code
        ORDER BY revenue DESC
    """, as_dict=True)
