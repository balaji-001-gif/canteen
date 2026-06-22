import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Item", "fieldname": "item", "fieldtype": "Link", "options": "Canteen Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 130},
        {"label": "Qty Sold", "fieldname": "qty_sold", "fieldtype": "Float", "width": 100},
        {"label": "Revenue", "fieldname": "revenue", "fieldtype": "Currency", "width": 130},
        {"label": "Cost", "fieldname": "cost", "fieldtype": "Currency", "width": 120},
        {"label": "Gross Profit", "fieldname": "gross_profit", "fieldtype": "Currency", "width": 130},
        {"label": "Margin %", "fieldname": "margin_pct", "fieldtype": "Percent", "width": 100},
    ]


def get_data(filters):
    conditions = "co.docstatus = 1"

    if filters.get("from_date"):
        conditions += f" AND co.order_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND co.order_date <= '{filters['to_date']}'"

    return frappe.db.sql(f"""
        SELECT
            coi.item,
            coi.item_name,
            ci.category,
            SUM(coi.quantity) AS qty_sold,
            SUM(coi.amount) AS revenue,
            SUM(coi.quantity * IFNULL(ci.cost_price, 0)) AS cost,
            SUM(coi.amount) - SUM(coi.quantity * IFNULL(ci.cost_price, 0)) AS gross_profit,
            CASE
                WHEN SUM(coi.amount) > 0
                THEN ROUND((SUM(coi.amount) - SUM(coi.quantity * IFNULL(ci.cost_price, 0))) / SUM(coi.amount) * 100, 2)
                ELSE 0
            END AS margin_pct
        FROM `tabCanteen Order Item` coi
        JOIN `tabCanteen Order` co ON co.name = coi.parent
        LEFT JOIN `tabCanteen Item` ci ON ci.name = coi.item
        WHERE {conditions}
        GROUP BY coi.item
        ORDER BY revenue DESC
    """, as_dict=True)
