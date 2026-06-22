import frappe
from frappe.model.document import Document
from frappe.utils import flt, now


class CanteenStockEntry(Document):
    def before_insert(self):
        self.entered_by = frappe.session.user

    def validate(self):
        self.calculate_amounts()

    def calculate_amounts(self):
        for item in self.stock_items:
            item.amount = flt(item.quantity) * flt(item.rate)

    def on_submit(self):
        self.update_inventory()

    def on_cancel(self):
        self.reverse_inventory()

    def update_inventory(self):
        for item in self.stock_items:
            inventory = frappe.db.get_value(
                "Canteen Inventory",
                {"item": item.item},
                "name"
            )
            if not inventory:
                frappe.throw(
                    f"No inventory record found for item {item.item_name}. "
                    "Please save the item first to auto-create inventory."
                )

            inv_doc = frappe.get_doc("Canteen Inventory", inventory)

            if self.entry_type in ("Purchase", "Opening Stock", "Return"):
                inv_doc.current_quantity = flt(inv_doc.current_quantity) + flt(item.quantity)
            elif self.entry_type in ("Waste", "Adjustment"):
                inv_doc.current_quantity = flt(inv_doc.current_quantity) - flt(item.quantity)
                if flt(inv_doc.current_quantity) < 0:
                    frappe.throw(
                        f"Stock for {item.item_name} cannot go below zero. "
                        f"Available: {inv_doc.current_quantity + flt(item.quantity)}"
                    )

            inv_doc.last_stock_entry = self.name
            inv_doc.save(ignore_permissions=True)

    def reverse_inventory(self):
        for item in self.stock_items:
            inventory = frappe.db.get_value(
                "Canteen Inventory",
                {"item": item.item},
                "name"
            )
            if inventory:
                inv_doc = frappe.get_doc("Canteen Inventory", inventory)

                if self.entry_type in ("Purchase", "Opening Stock", "Return"):
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) - flt(item.quantity)
                elif self.entry_type in ("Waste", "Adjustment"):
                    inv_doc.current_quantity = flt(inv_doc.current_quantity) + flt(item.quantity)

                inv_doc.save(ignore_permissions=True)


def on_submit(doc, method):
    pass
