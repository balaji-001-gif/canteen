import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Item Code", "fieldname": "item", "fieldtype": "Link", "options": "Canteen Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "Category", "fieldname": "category", "fieldtype": "Link", "options": "Canteen Category", "width": 120},
        {"label": "Current Stock", "fieldname": "current_quantity", "fieldtype": "Float", "width": 120},
        {"label": "Min Stock", "fieldname": "minimum_quantity", "fieldtype": "Float", "width": 100},
        {"label": "Max Stock", "fieldname": "maximum_quantity", "fieldtype": "Float", "width": 100},
        {"label": "Unit", "fieldname": "unit", "fieldtype": "Link", "options": "UOM", "width": 80},
        {"label": "Status", "fieldname": "stock_status", "fieldtype": "Data", "width": 100},
        {"label": "Last Updated", "fieldname": "last_updated", "fieldtype": "Datetime", "width": 150},
    ]


def get_data(filters):
    conditions = "1=1"

    if filters.get("category"):
        conditions += f" AND ci.category = '{filters['category']}'"
    if filters.get("stock_status") == "Low Stock":
        conditions += " AND inv.current_quantity <= inv.minimum_quantity AND inv.current_quantity > 0"
    elif filters.get("stock_status") == "Out of Stock":
        conditions += " AND inv.current_quantity = 0"
    elif filters.get("stock_status") == "Healthy":
        conditions += " AND inv.current_quantity > inv.minimum_quantity"

    data = frappe.db.sql(f"""
        SELECT
            inv.item,
            inv.item_name,
            ci.category,
            inv.current_quantity,
            inv.minimum_quantity,
            inv.maximum_quantity,
            inv.unit,
            inv.last_updated,
            CASE
                WHEN inv.current_quantity = 0 THEN 'Out of Stock'
                WHEN inv.current_quantity <= inv.minimum_quantity THEN 'Low Stock'
                ELSE 'Healthy'
            END AS stock_status
        FROM `tabCanteen Inventory` inv
        LEFT JOIN `tabCanteen Item` ci ON ci.name = inv.item
        WHERE {conditions}
        ORDER BY inv.item_name ASC
    """, as_dict=True)

    return data
