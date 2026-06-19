import frappe
from frappe.model.document import Document
from frappe.utils import now, now_datetime

class CanteenShift(Document):
    def before_insert(self):
        self.opened_at = now()
        if not self.cashier:
            self.cashier = frappe.session.user

    def validate(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            frappe.throw("Shift end time must be after start time")

    def on_update(self):
        if self.status == "Closed" and not self.closed_at:
            self.closed_at = now()
            self.calculate_totals()

    def calculate_totals(self):
        orders = frappe.get_all(
            "Canteen Order",
            filters={"shift": self.name, "docstatus": 1},
            fields=["total_amount"]
        )
        total_sales = sum(o.total_amount for o in orders if o.total_amount)
        self.total_sales = total_sales
        self.total_orders = len(orders)


@frappe.whitelist()
def close_shift(shift_name):
    doc = frappe.get_doc("Canteen Shift", shift_name)
    doc.status = "Closed"
    doc.closed_at = now()
    doc.calculate_totals()
    doc.save(ignore_permissions=True)
    return {"status": "success", "shift": shift_name}


@frappe.whitelist()
def get_active_shift(cashier=None):
    if not cashier:
        cashier = frappe.session.user
    shift = frappe.db.get_value(
        "Canteen Shift",
        {"status": "Active", "cashier": cashier},
        ["name", "shift_name", "start_time", "opening_amount", "opened_at"],
        as_dict=True
    )
    return shift
