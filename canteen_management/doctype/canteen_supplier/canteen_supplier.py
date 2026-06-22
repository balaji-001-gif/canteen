import frappe
from frappe.model.document import Document


class CanteenSupplier(Document):
    def validate(self):
        if self.email and not frappe.utils.validate_email_address(self.email):
            frappe.throw("Please enter a valid email address")
