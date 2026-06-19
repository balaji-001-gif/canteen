import frappe
from frappe.model.document import Document

class CanteenTable(Document):
    def validate(self):
        if self.capacity <= 0:
            frappe.throw("Capacity must be greater than 0")
        if self.table_no <= 0:
            frappe.throw("Table number must be greater than 0")


@frappe.whitelist()
def get_available_tables():
    """Get all available tables"""
    tables = frappe.get_all(
        "Canteen Table",
        filters={"status": "Available"},
        fields=["name", "table_name", "table_no", "capacity", "location"],
        order_by="table_no asc"
    )
    return tables


@frappe.whitelist()
def update_table_status(table_name, status):
    doc = frappe.get_doc("Canteen Table", table_name)
    doc.status = status
    doc.save(ignore_permissions=True)
    return {"status": "success"}
