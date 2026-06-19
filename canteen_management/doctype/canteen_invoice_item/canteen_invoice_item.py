import frappe
from frappe.model.document import Document

class CanteenInvoiceItem(Document):
    def validate(self):
        self.amount = self.quantity * self.rate
        self.total_amount = self.amount + (self.tax_amount or 0)
