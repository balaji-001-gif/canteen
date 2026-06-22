import frappe
from frappe.model.document import Document


class CanteenSettings(Document):
    def validate(self):
        if self.tax_rate and (self.tax_rate < 0 or self.tax_rate > 100):
            frappe.throw("Tax rate must be between 0 and 100")
        
        if self.max_credit_limit and self.max_credit_limit < 0:
            frappe.throw("Maximum credit limit cannot be negative")

    def on_update(self):
        frappe.cache().delete_value("canteen_settings")
