import frappe
from frappe.model.document import Document
from frappe.utils import flt, today, nowtime

class CanteenStockEntry(Document):
    def before_insert(self):
        self.status = "Draft"
        self.posting_date = today()
        self.posting_time = nowtime()

    def validate(self):
        self.calculate_totals()
        self.validate_items()

    def validate_items(self):
        if not self.items:
            frappe.throw("Please add at least one item to the stock entry")
        for item in self.items:
            if flt(item.quantity) <= 0:
                frappe.throw(f"Quantity must be greater than 0 for item {item.item_name}")

    def calculate_totals(self):
        total_qty = 0
        total_amt = 0
        for item in self.items:
            item.amount = flt(item.quantity) * flt(item.rate)
            total_qty += flt(item.quantity)
            total_amt += flt(item.amount)
        self.total_quantity = total_qty
        self.total_amount = total_amt

    def on_submit(self):
        self.status = "Submitted"
        self.update_inventory()
        self.save()

    def on_cancel(self):
        self.reverse_inventory()
        self.status = "Cancelled"

    def update_inventory(self):
        for item in self.items:
            inventory_name = frappe.db.get_value(
                "Canteen Inventory", {"item": item.item}, "name"
            )
            if inventory_name:
                inv_doc = frappe.get_doc("Canteen Inventory", inventory_name)
                if self.stock_type == "Inward":
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) + flt(item.quantity)
                elif self.stock_type == "Outward":
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) - flt(item.quantity)
                elif self.stock_type == "Adjustment":
                    inv_doc.current_quantity = flt(item.quantity)
                elif self.stock_type == "Wastage":
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) - flt(item.quantity)
                inv_doc.last_stock_entry = self.name
                inv_doc.save(ignore_permissions=True)

    def reverse_inventory(self):
        for item in self.items:
            inventory_name = frappe.db.get_value(
                "Canteen Inventory", {"item": item.item}, "name"
            )
            if inventory_name:
                inv_doc = frappe.get_doc("Canteen Inventory", inventory_name)
                if self.stock_type == "Inward":
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) - flt(item.quantity)
                elif self.stock_type == "Outward":
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) + flt(item.quantity)
                elif self.stock_type == "Adjustment":
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) - flt(item.quantity)
                elif self.stock_type == "Wastage":
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) + flt(item.quantity)
                inv_doc.save(ignore_permissions=True)


def on_submit(doc, method):
    pass


@frappe.whitelist()
def get_stock_balance(item_code):
    """Get current stock balance for an item"""
    inv = frappe.db.get_value(
        "Canteen Inventory",
        {"item": item_code},
        ["current_quantity", "minimum_quantity"],
        as_dict=True
    )
    return inv or {"current_quantity": 0, "minimum_quantity": 0}
