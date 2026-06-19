import frappe
from frappe.model.document import Document


class CanteenOrderItem(Document):
    def validate(self):
        if not self.rate:
            item = frappe.get_doc("Canteen Item", self.item)
            self.rate = item.selling_price
            self.tax_rate = item.tax_rate
        
        self.amount = self.quantity * self.rate
        self.tax_amount = self.amount * self.tax_rate / 100
        self.total_amount = self.amount + self.tax_amount
