import frappe
from frappe.model.document import Document
from frappe.utils import flt, now


class CanteenEmployeeWallet(Document):
    def validate(self):
        if flt(self.balance) < 0:
            frappe.throw("Wallet balance cannot be negative")


@frappe.whitelist()
def credit_wallet(employee, amount, remarks=None):
    """Add credit to employee wallet"""
    amount = flt(amount)
    if amount <= 0:
        frappe.throw("Amount must be greater than 0")

    wallet = frappe.db.get_value(
        "Canteen Employee Wallet",
        {"employee": employee},
        ["name", "balance", "total_credited"],
        as_dict=True
    )

    if not wallet:
        # Auto-create wallet
        wallet_doc = frappe.new_doc("Canteen Employee Wallet")
        wallet_doc.employee = employee
        wallet_doc.balance = 0
        wallet_doc.total_credited = 0
        wallet_doc.total_debited = 0
        wallet_doc.insert(ignore_permissions=True)
        wallet = frappe.db.get_value(
            "Canteen Employee Wallet",
            {"employee": employee},
            ["name", "balance", "total_credited"],
            as_dict=True
        )

    new_balance = flt(wallet.balance) + amount

    frappe.db.set_value("Canteen Employee Wallet", wallet.name, {
        "balance": new_balance,
        "total_credited": flt(wallet.total_credited) + amount,
        "last_transaction_date": now()
    })

    # Create transaction record
    txn = frappe.new_doc("Canteen Wallet Transaction")
    txn.wallet = wallet.name
    txn.employee = employee
    txn.transaction_type = "Credit"
    txn.amount = amount
    txn.balance_after = new_balance
    txn.remarks = remarks or f"Manual credit of {amount}"
    txn.insert(ignore_permissions=True)

    return {"new_balance": new_balance}


@frappe.whitelist()
def get_wallet_balance(employee):
    """Get current wallet balance for employee"""
    balance = frappe.db.get_value(
        "Canteen Employee Wallet",
        {"employee": employee},
        "balance"
    )
    return flt(balance)
