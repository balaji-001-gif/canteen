import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CanteenInvoiceItem(Document):
    def validate(self):
        self.amount = flt(self.quantity) * flt(self.rate)
        self.total_amount = flt(self.amount) + flt(self.tax_amount)
