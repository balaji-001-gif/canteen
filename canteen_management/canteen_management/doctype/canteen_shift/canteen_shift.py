import frappe
from frappe.model.document import Document
from frappe.utils import flt, now, today


class CanteenShift(Document):
    def validate(self):
        self.validate_single_active_shift()

    def validate_single_active_shift(self):
        if self.status == "Active":
            existing = frappe.db.get_value(
                "Canteen Shift",
                {
                    "cashier": self.cashier,
                    "status": "Active",
                    "name": ["!=", self.name or ""]
                },
                "name"
            )
            if existing:
                frappe.throw(
                    f"Cashier already has an active shift: {existing}. "
                    "Please close the existing shift first."
                )

    def on_update(self):
        if self.status == "Closed":
            self.calculate_shift_summary()

    def calculate_shift_summary(self):
        orders = frappe.get_all(
            "Canteen Order",
            filters={"shift": self.name, "docstatus": 1},
            fields=["total_amount", "payment_mode"]
        )

        total_sales = 0
        cash_sales = card_sales = upi_sales = wallet_sales = credit_sales = 0

        for order in orders:
            amt = flt(order.total_amount)
            total_sales += amt
            mode = (order.payment_mode or "").lower()
            if mode == "cash":
                cash_sales += amt
            elif mode == "card":
                card_sales += amt
            elif mode == "upi":
                upi_sales += amt
            elif mode == "wallet":
                wallet_sales += amt
            elif mode == "credit":
                credit_sales += amt

        frappe.db.set_value("Canteen Shift", self.name, {
            "total_sales": total_sales,
            "total_orders": len(orders),
            "cash_sales": cash_sales,
            "card_sales": card_sales,
            "upi_sales": upi_sales,
            "wallet_sales": wallet_sales,
            "credit_sales": credit_sales,
        })


@frappe.whitelist()
def close_shift(shift_name, closing_cash=0):
    """Close a shift"""
    doc = frappe.get_doc("Canteen Shift", shift_name)
    doc.status = "Closed"
    doc.end_time = frappe.utils.nowtime()
    doc.closing_cash = flt(closing_cash)
    doc.save(ignore_permissions=True)
    return {"status": "success"}
