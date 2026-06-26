import frappe
from frappe.model.document import Document
from frappe.utils import flt, now, today, get_datetime, nowtime


class CanteenOrder(Document):
    def before_insert(self):
        self.cashier = frappe.session.user
        self.order_date = today()
        self.order_time = nowtime()

    def validate(self):
        self.validate_items()
        self.calculate_totals()
        self.calculate_change()

    def validate_items(self):
        if not self.items:
            frappe.throw("Please add at least one item to the order")
        
        for item in self.items:
            if flt(item.quantity) <= 0:
                frappe.throw(f"Quantity must be greater than 0 for item {item.item_name}")
            
            # Check stock availability
            inventory = frappe.db.get_value(
                "Canteen Inventory",
                {"item": item.item},
                "current_quantity"
            )
            if inventory is not None and flt(inventory) < flt(item.quantity):
                frappe.throw(
                    f"Insufficient stock for {item.item_name}. "
                    f"Available: {inventory}, Required: {item.quantity}"
                )

    def calculate_totals(self):
        subtotal = 0
        tax_total = 0
        
        for item in self.items:
            item.amount = flt(item.quantity) * flt(item.rate)
            item.tax_amount = flt(item.amount) * flt(item.tax_rate) / 100
            item.total_amount = flt(item.amount) + flt(item.tax_amount)
            subtotal += flt(item.amount)
            tax_total += flt(item.tax_amount)
        
        self.subtotal = subtotal
        self.tax_amount = tax_total
        self.total_amount = subtotal + tax_total - flt(self.discount_amount)

    def calculate_change(self):
        if flt(self.paid_amount) > 0:
            self.change_amount = flt(self.paid_amount) - flt(self.total_amount)
            if self.change_amount < 0:
                frappe.throw("Paid amount is less than total amount")

    def on_submit(self):
        self.update_inventory()
        self.update_wallet_if_applicable()
        self.create_invoice()
        self.status = "Completed"
        self.save()

    def on_cancel(self):
        self.restore_inventory()
        self.status = "Cancelled"
        
        # Cancel related invoice
        invoice = frappe.db.get_value(
            "Canteen Invoice", {"order": self.name, "docstatus": 1}
        )
        if invoice:
            inv_doc = frappe.get_doc("Canteen Invoice", invoice)
            inv_doc.cancel()

    def update_inventory(self):
        for item in self.items:
            inventory = frappe.db.get_value(
                "Canteen Inventory",
                {"item": item.item},
                "name"
            )
            if inventory:
                inv_doc = frappe.get_doc("Canteen Inventory", inventory)
                inv_doc.current_quantity = flt(inv_doc.current_quantity) - flt(item.quantity)
                inv_doc.save(ignore_permissions=True)
                
                # Check low stock
                if flt(inv_doc.current_quantity) <= flt(inv_doc.minimum_quantity):
                    self.send_low_stock_alert(item.item_name, inv_doc.current_quantity)

    def restore_inventory(self):
        for item in self.items:
            inventory = frappe.db.get_value(
                "Canteen Inventory",
                {"item": item.item},
                "name"
            )
            if inventory:
                inv_doc = frappe.get_doc("Canteen Inventory", inventory)
                inv_doc.current_quantity = flt(inv_doc.current_quantity) + flt(item.quantity)
                inv_doc.save(ignore_permissions=True)

    def update_wallet_if_applicable(self):
        if self.payment_mode == "Wallet" and self.employee:
            wallet = frappe.db.get_value(
                "Canteen Employee Wallet",
                {"employee": self.employee},
                ["name", "balance"],
                as_dict=True
            )
            if wallet:
                if flt(wallet.balance) < flt(self.total_amount):
                    frappe.throw("Insufficient wallet balance")
                
                wallet_doc = frappe.get_doc("Canteen Employee Wallet", wallet.name)
                wallet_doc.balance = flt(wallet.balance) - flt(self.total_amount)
                wallet_doc.save(ignore_permissions=True)
                
                # Create wallet transaction
                self.create_wallet_transaction(wallet.name, "Debit")

    def create_wallet_transaction(self, wallet_name, transaction_type):
        txn = frappe.new_doc("Canteen Wallet Transaction")
        txn.wallet = wallet_name
        txn.employee = self.employee
        txn.transaction_type = transaction_type
        txn.amount = self.total_amount
        txn.reference_document = "Canteen Order"
        txn.reference_name = self.name
        txn.remarks = f"Order payment - {self.name}"
        txn.insert(ignore_permissions=True)

    def create_invoice(self):
        invoice = frappe.new_doc("Canteen Invoice")
        invoice.order = self.name
        invoice.invoice_date = today()
        invoice.employee = self.employee
        invoice.customer_name = self.customer_name or self.employee_name
        invoice.payment_mode = self.payment_mode
        invoice.cashier = self.cashier
        invoice.subtotal = self.subtotal
        invoice.tax_amount = self.tax_amount
        invoice.discount_amount = self.discount_amount
        invoice.total_amount = self.total_amount
        invoice.paid_amount = self.paid_amount
        invoice.change_amount = self.change_amount
        
        for item in self.items:
            invoice.append("items", {
                "item": item.item,
                "item_name": item.item_name,
                "quantity": item.quantity,
                "rate": item.rate,
                "amount": item.amount,
                "tax_amount": item.tax_amount,
                "total_amount": item.total_amount
            })
        
        invoice.insert(ignore_permissions=True)
        invoice.submit()

    def send_low_stock_alert(self, item_name, current_qty):
        settings = frappe.get_single("Canteen Settings")
        if settings.low_stock_email:
            frappe.sendmail(
                recipients=[settings.low_stock_email],
                subject=f"Low Stock Alert - {item_name}",
                message=f"Stock for {item_name} is low. Current quantity: {current_qty}"
            )


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
def get_order_status(order_name):
    return frappe.db.get_value("Canteen Order", order_name, "status")


@frappe.whitelist()
def update_order_status(order_name, status):
    doc = frappe.get_doc("Canteen Order", order_name)
    doc.status = status
    doc.save(ignore_permissions=True)
    return {"status": "success", "new_status": status}
