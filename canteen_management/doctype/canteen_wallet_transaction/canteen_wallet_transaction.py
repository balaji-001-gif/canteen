import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

class CanteenWalletTransaction(Document):
    def before_insert(self):
        self.date = today()

    def validate(self):
        if flt(self.amount) <= 0:
            frappe.throw("Transaction amount must be greater than 0")
