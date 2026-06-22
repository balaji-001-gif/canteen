import frappe
from frappe.model.document import Document
from frappe.utils import flt, now, nowtime, today


class CanteenStockEntry(Document):
    def before_insert(self):
        self.entered_by = frappe.session.user
        if not self.posting_date:
            self.posting_date = today()
        if not self.posting_time:
            self.posting_time = nowtime()

    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        total_qty = 0
        total_amount = 0
        for item in self.items:
            item.amount = flt(item.quantity) * flt(item.rate)
            total_qty += flt(item.quantity)
            total_amount += flt(item.amount)
        self.total_quantity = total_qty
        self.total_amount = total_amount

    def on_submit(self):
        self.status = "Submitted"
        self.update_inventory()

    def on_cancel(self):
        self.status = "Cancelled"
        self.reverse_inventory()

    def update_inventory(self):
        for item in self.items:
            inventory = frappe.db.get_value(
                "Canteen Inventory", {"item": item.item}, "name"
            )
            if not inventory:
                frappe.throw(
                    f"No inventory record found for item {item.item_name}. "
                    "Please save the item first to auto-create inventory."
                )

            inv_doc = frappe.get_doc("Canteen Inventory", inventory)
            if self.stock_type in ("Purchase", "Opening Stock", "Return"):
                inv_doc.current_quantity = flt(inv_doc.current_quantity) + flt(item.quantity)
            elif self.stock_type in ("Waste", "Adjustment"):
                new_qty = flt(inv_doc.current_quantity) - flt(item.quantity)
                if new_qty < 0:
                    frappe.throw(
                        f"Stock for {item.item_name} cannot go below zero. "
                        f"Available: {inv_doc.current_quantity}, Required: {item.quantity}"
                    )
                inv_doc.current_quantity = new_qty

            inv_doc.last_stock_entry = self.name
            inv_doc.save(ignore_permissions=True)

    def reverse_inventory(self):
        for item in self.items:
            inventory = frappe.db.get_value(
                "Canteen Inventory", {"item": item.item}, "name"
            )
            if inventory:
                inv_doc = frappe.get_doc("Canteen Inventory", inventory)
                if self.stock_type in ("Purchase", "Opening Stock", "Return"):
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) - flt(item.quantity)
                elif self.stock_type in ("Waste", "Adjustment"):
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) + flt(item.quantity)
                inv_doc.save(ignore_permissions=True)


def on_submit(doc, method):
    pass
