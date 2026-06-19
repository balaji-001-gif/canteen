import frappe
from frappe.model.document import Document

class CanteenPaymentMode(Document):
    def validate(self):
        if not self.mode_label:
            self.mode_label = self.payment_mode
