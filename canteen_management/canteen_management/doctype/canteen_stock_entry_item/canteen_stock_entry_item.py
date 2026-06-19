import frappe
from frappe.model.document import Document

class CanteenStockEntryItem(Document):
    def validate(self):
        if not self.rate:
            item = frappe.get_doc("Canteen Item", self.item)
            self.rate = item.cost_price or item.selling_price
        self.amount = self.quantity * self.rate
