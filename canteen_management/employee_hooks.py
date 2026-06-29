# -*- coding: utf-8 -*-
"""
Employee Hooks — Auto-create Canteen Employee Wallet

When an Employee is saved with "Enable Canteen Wallet" checked:
  1. Creates a Canteen Employee Wallet if one doesn't exist
     - Initial balance is set from the Employee's wallet_credit_limit field
     - Credit limit is kept separate (set to 0 for new wallets)
  2. For existing wallets: syncs the credit_limit field only (doesn't touch balance)
  3. Links the wallet back to the Employee's read-only canteen_wallet field
  4. Creates a Canteen Wallet Transaction (Credit) for the initial balance

When "Enable Canteen Wallet" is unchecked:
  1. Deactivates the wallet (is_active = 0)

Usage:
    Registered via hooks.py doc_events -> "Employee" on_update
"""

import frappe
from frappe.utils import flt


def sync_wallet_on_save(doc, method):
    """Auto-create or update the Canteen Employee Wallet when an Employee is saved.
    
    Uses on_update (not validate) so the Employee record is already committed
    before any wallet operations begin — prevents orphaned wallet records
    if the Employee save fails.
    """
    if not doc.enable_canteen_wallet:
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
        # Wallet exists — sync credit limit only (don't modify balance)
        wallet = frappe.get_doc("Canteen Employee Wallet", existing.name)
        new_credit_limit = flt(doc.wallet_credit_limit)

        if flt(wallet.credit_limit) != new_credit_limit:
            wallet.credit_limit = new_credit_limit

        wallet.is_active = 1
        wallet.save(ignore_permissions=True)
    else:
        # Create new wallet with initial balance from wallet_credit_limit
        initial_balance = flt(doc.wallet_credit_limit)

        wallet = frappe.new_doc("Canteen Employee Wallet")
        wallet.employee = doc.name
        wallet.employee_name = doc.employee_name
        wallet.department = doc.department
        wallet.balance = initial_balance
        wallet.credit_limit = 0  # credit limit is a separate concept
        wallet.is_active = 1
        wallet.insert(ignore_permissions=True)

        # Create Credit transaction for audit trail
        if initial_balance > 0:
            txn = frappe.new_doc("Canteen Wallet Transaction")
            txn.wallet = wallet.name
            txn.employee = doc.name
            txn.transaction_type = "Credit"
            txn.amount = initial_balance
            txn.balance_after = initial_balance
            txn.remarks = "Initial wallet credit from Employee setup"
            txn.insert(ignore_permissions=True)

        # Update total_credited on the wallet
        if initial_balance > 0:
            frappe.db.set_value("Canteen Employee Wallet", wallet.name,
                "total_credited", initial_balance)

    # Update the read-only link on Employee to point to the wallet
    if doc.canteen_wallet != wallet.name:
        frappe.db.set_value("Employee", doc.name, "canteen_wallet", wallet.name)


def auto_create_customer(doc, method):
    """Auto-create a Customer and Canteen Wallet when a new Employee is created.

    Runs on after_insert so it only fires once per Employee.

    - Creates a Customer (Individual, All Territories) from employee_name
    - Creates a Canteen Employee Wallet with zero balance
    - Enables the wallet (set enable_canteen_wallet = 1)
    - Updates doc in-memory so the subsequent on_update handler
      (sync_wallet_on_save) sees the enabled state and doesn't
      accidentally deactivate the wallet.
    """
    customer_name = doc.employee_name or doc.name

    # ── Customer ──────────────────────────────────────────────────────────
    if not doc.customer:
        existing = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
        if existing:
            doc.customer = existing
            frappe.db.set_value("Employee", doc.name, "customer", existing)
            frappe.msgprint(
                f"Linked Employee '{customer_name}' to existing Customer '{existing}'.",
                alert=True,
            )
        else:
            customer = frappe.new_doc("Customer")
            customer.customer_name = customer_name
            customer.customer_type = "Individual"
            customer.customer_group = "Individual"
            customer.territory = "All Territories"
            customer.insert(ignore_permissions=True)
            doc.customer = customer.name
            frappe.db.set_value("Employee", doc.name, "customer", customer.name)
            frappe.msgprint(
                f"Auto-created Customer '{customer.name}' for Employee '{customer_name}'.",
                alert=True,
            )

    # ── Wallet ────────────────────────────────────────────────────────────
    existing_wallet = frappe.db.get_value(
        "Canteen Employee Wallet",
        {"employee": doc.name},
        ["name", "balance"],
        as_dict=True,
    )

    if not existing_wallet:
        wallet = frappe.new_doc("Canteen Employee Wallet")
        wallet.employee = doc.name
        wallet.employee_name = customer_name
        wallet.department = doc.department
        wallet.balance = 0
        wallet.credit_limit = 0
        wallet.is_active = 1
        wallet.insert(ignore_permissions=True)

        # Update Employee fields in DB
        frappe.db.set_value("Employee", doc.name, {
            "enable_canteen_wallet": 1,
            "canteen_wallet": wallet.name,
        })

        # Also update in-memory doc so the subsequent on_update
        # (sync_wallet_on_save) sees enable_canteen_wallet = 1
        # and doesn't deactivate the wallet
        doc.enable_canteen_wallet = 1
        doc.canteen_wallet = wallet.name

        frappe.msgprint(
            f"Auto-created wallet '{wallet.name}' for Employee '{customer_name}'.",
            alert=True,
        )


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
