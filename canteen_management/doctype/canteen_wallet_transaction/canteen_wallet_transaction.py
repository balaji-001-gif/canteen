import frappe
from frappe.model.document import Document
from frappe.utils import now


class CanteenWalletTransaction(Document):
    def before_insert(self):
        self.transaction_date = now()
