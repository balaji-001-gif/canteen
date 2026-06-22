import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class CanteenInvoice(Document):
    def validate(self):
        self.calculate_totals()
        self.status = "Paid"

    def calculate_totals(self):
        subtotal = sum(flt(item.amount) for item in self.items)
        tax_total = sum(flt(item.tax_amount) for item in self.items)
        
        self.subtotal = subtotal
        self.tax_amount = tax_total
        self.total_amount = subtotal + tax_total - flt(self.discount_amount)

    def on_submit(self):
        self.status = "Paid"
        self.save()

    def on_cancel(self):
        self.status = "Cancelled"


def on_submit(doc, method):
    pass


def on_cancel(doc, method):
    pass


def has_permission(doc, ptype, user):
    if frappe.has_role("Canteen Admin", user=user):
        return True
    if frappe.has_role("Canteen Manager", user=user):
        return True
    if ptype == "read" and frappe.has_role("Canteen User", user=user):
        if doc.employee:
            emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
            return doc.employee == emp
    return None


@frappe.whitelist()
def get_invoice_html(invoice_name):
    """Generate invoice HTML for printing"""
    invoice = frappe.get_doc("Canteen Invoice", invoice_name)
    settings = frappe.get_single("Canteen Settings")
    
    html = frappe.render_template(
        "canteen_management/templates/invoice.html",
        {
            "invoice": invoice,
            "settings": settings
        }
    )
    return html
