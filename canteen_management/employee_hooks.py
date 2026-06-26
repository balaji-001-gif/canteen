# -*- coding: utf-8 -*-
"""
Employee Hooks — Auto-create Canteen Employee Wallet

When an Employee is saved with "Enable Canteen Wallet" checked:
  1. Creates a Canteen Employee Wallet if one doesn't exist
  2. Syncs the credit limit from the Employee's wallet_credit_limit field
  3. Sets the initial balance from wallet_credit_limit (on first creation)
  4. Links the wallet back to the Employee's read-only canteen_wallet field
  5. Creates a Canteen Wallet Transaction (Credit) for the initial balance

When "Enable Canteen Wallet" is unchecked:
  1. Deactivates the wallet (is_active = 0)

Usage:
    Registered via hooks.py doc_events -> "Employee"
"""

import frappe
from frappe.utils import flt, now


def sync_wallet_on_save(doc, method):
    """Auto-create or update the Canteen Employee Wallet when an Employee is saved."""
    if not doc.enable_canteen_wallet:
        # Wallet access disabled — deactivate if wallet exists
        _deactivate_wallet(doc)
        return

    # Find existing wallet
    existing = frappe.db.get_value(
        "Canteen Employee Wallet",
        {"employee": doc.name},
        ["name", "balance", "credit_limit"],
        as_dict=True,
    )

    if existing:
        # Wallet exists — sync credit limit only
        wallet = frappe.get_doc("Canteen Employee Wallet", existing.name)
        new_credit_limit = flt(doc.wallet_credit_limit)

        if flt(wallet.credit_limit) != new_credit_limit:
            wallet.credit_limit = new_credit_limit

        wallet.is_active = 1
        wallet.save(ignore_permissions=True)
    else:
        # Create new wallet
        credit_limit = flt(doc.wallet_credit_limit)

        wallet = frappe.new_doc("Canteen Employee Wallet")
        wallet.employee = doc.name
        wallet.employee_name = doc.employee_name
        wallet.department = doc.department
        wallet.balance = 0
        wallet.credit_limit = credit_limit
        wallet.is_active = 1
        wallet.insert(ignore_permissions=True)

        # Create Credit transaction for the initial balance
        if credit_limit > 0:
            txn = frappe.new_doc("Canteen Wallet Transaction")
            txn.wallet = wallet.name
            txn.employee = doc.name
            txn.transaction_type = "Credit"
            txn.amount = credit_limit
            txn.balance_after = credit_limit
            txn.remarks = "Initial wallet credit from Employee setup"
            txn.insert(ignore_permissions=True)

    # Update the read-only link on Employee to point to the wallet
    if doc.canteen_wallet != wallet.name:
        frappe.db.set_value("Employee", doc.name, "canteen_wallet", wallet.name)


def _deactivate_wallet(doc):
    """Deactivate the wallet when enable_canteen_wallet is unchecked."""
    wallet_name = frappe.db.get_value(
        "Canteen Employee Wallet",
        {"employee": doc.name},
        "name",
    )
    if wallet_name:
        wallet = frappe.get_doc("Canteen Employee Wallet", wallet_name)
        wallet.is_active = 0
        wallet.save(ignore_permissions=True)

        # Clear the link on Employee
        if doc.canteen_wallet:
            frappe.db.set_value("Employee", doc.name, "canteen_wallet", None)
