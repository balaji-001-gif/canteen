import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CanteenStockEntryItem(Document):
    def validate(self):
        self.amount = flt(self.quantity) * flt(self.rate)
