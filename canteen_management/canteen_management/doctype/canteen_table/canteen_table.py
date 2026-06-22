import frappe
from frappe.model.document import Document


class CanteenTable(Document):
    def validate(self):
        if self.capacity and self.capacity < 1:
            frappe.throw("Table capacity must be at least 1")


@frappe.whitelist()
def get_table_status():
    """Get current status of all tables"""
    tables = frappe.get_all(
        "Canteen Table",
        filters={"is_active": 1},
        fields=["name", "table_number", "table_name", "capacity", "status", "location"],
        order_by="table_number asc"
    )
    return tables


@frappe.whitelist()
def update_table_status(table_name, status):
    """Update table status"""
    frappe.db.set_value("Canteen Table", table_name, "status", status)
    return {"status": "success"}
