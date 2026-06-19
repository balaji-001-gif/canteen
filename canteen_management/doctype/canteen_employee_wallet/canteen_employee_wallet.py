import frappe
from frappe.model.document import Document
from frappe.utils import flt

class CanteenEmployeeWallet(Document):
    def validate(self):
        if flt(self.balance) < 0:
            frappe.throw("Wallet balance cannot be negative")
        if flt(self.credit_limit) < 0:
            frappe.throw("Credit limit cannot be negative")

    def get_available_balance(self):
        return flt(self.balance) + flt(self.credit_limit)


@frappe.whitelist()
def get_wallet_balance(employee=None):
    """Get wallet balance for an employee"""
    if not employee:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return None
    
    wallet = frappe.db.get_value(
        "Canteen Employee Wallet",
        {"employee": employee, "is_active": 1},
        ["name", "employee_name", "balance", "credit_limit"],
        as_dict=True
    )
    if wallet:
        wallet["available_balance"] = flt(wallet.balance) + flt(wallet.credit_limit)
    return wallet


@frappe.whitelist()
def topup_wallet(wallet_name, amount, remarks=None):
    """Add funds to an employee wallet"""
    amount = flt(amount)
    if amount <= 0:
        frappe.throw("Amount must be greater than 0")
    
    wallet = frappe.get_doc("Canteen Employee Wallet", wallet_name)
    wallet.balance = flt(wallet.balance) + amount
    wallet.save(ignore_permissions=True)
    
    # Create transaction record
    txn = frappe.new_doc("Canteen Wallet Transaction")
    txn.wallet = wallet.name
    txn.employee = wallet.employee
    txn.transaction_type = "Credit"
    txn.amount = amount
    txn.remarks = remarks or "Wallet top-up"
    txn.insert(ignore_permissions=True)
    
    return {"status": "success", "new_balance": wallet.balance}
