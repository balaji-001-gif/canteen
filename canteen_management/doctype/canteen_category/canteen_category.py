import frappe
from frappe.model.document import Document


class CanteenCategory(Document):
    def validate(self):
        if self.parent_category == self.name:
            frappe.throw("Category cannot be its own parent")

    def before_rename(self, old, new, merge=False):
        if merge:
            frappe.throw("Merging categories is not allowed")
