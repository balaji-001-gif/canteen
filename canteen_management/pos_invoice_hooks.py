# -*- coding: utf-8 -*-
"""
POS Invoice Hooks — Employee Wallet Integration

Hooks into ERPNext's standard POS Invoice (on_submit / on_cancel) to:

1. When a POS Invoice is submitted with "Wallet" payment mode:
   - Finds the employee's wallet via the custom canteen_employee field
   - Validates sufficient balance (balance + credit_limit >= invoice total)
   - Deducts the wallet amount
   - Creates a Canteen Wallet Transaction record (Debit)

2. When a POS Invoice is cancelled with "Wallet" payment:
   - Refunds the wallet balance
   - Creates a Canteen Wallet Transaction record (Credit)

Usage:
    Registered via hooks.py doc_events -> "POS Invoice"
"""

import frappe
from frappe.utils import flt

WALLET_MODE = "Wallet"


# =============================================================================
# POS Invoice on_submit
# =============================================================================

def wallet_payment_on_submit(doc, method):
    """Handle wallet deduction when a POS Invoice is submitted."""
    wallet_amount = _get_wallet_payment_amount(doc)
    if not wallet_amount or wallet_amount <= 0:
        return  # No wallet payment on this invoice

    employee = _get_employee_from_invoice(doc)
    if not employee:
        frappe.throw(
            "Wallet payment selected but no employee is linked. "
            "Please set the 'Canteen Employee' field on the invoice."
        )

    wallet = _get_wallet(employee)
    if not wallet:
        frappe.throw(
            f"Employee {employee} does not have an active canteen wallet. "
            "Please create a wallet first via Canteen Employee Wallet."
        )

    _validate_wallet_balance(wallet, wallet_amount)
    _deduct_wallet(wallet, wallet_amount, doc)


# =============================================================================
# POS Invoice on_cancel
# =============================================================================

def wallet_payment_on_cancel(doc, method):
    """Refund wallet when a POS Invoice is cancelled."""
    wallet_amount = _get_wallet_payment_amount(doc)
    if not wallet_amount or wallet_amount <= 0:
        return

    employee = _get_employee_from_invoice(doc)
    if not employee:
        return  # Can't refund if no employee — skip silently

    wallet = _get_wallet(employee)
    if not wallet:
        return  # Wallet might have been deleted — skip

    _refund_wallet(wallet, wallet_amount, doc)


# =============================================================================
# Internal helpers
# =============================================================================

def _get_wallet_payment_amount(doc):
    """Check if invoice has Wallet payment and return the amount."""
    if not hasattr(doc, "payments") or not doc.payments:
        return 0

    for payment in doc.payments:
        mode = payment.mode_of_payment
        if mode == WALLET_MODE:
            return flt(payment.amount)

    return 0


def _get_employee_from_invoice(doc):
    """Get the employee from the custom canteen_employee field.
    Falls back to looking up employee via the Customer doctype link.
    """
    # Check custom field first
    if hasattr(doc, "canteen_employee") and doc.canteen_employee:
        return doc.canteen_employee

    # Fallback: try to find employee via the Customer
    if doc.customer:
        employee = frappe.db.get_value("Employee", {"customer": doc.customer}, "name")
        if employee:
            return employee

        # Try by customer name match
        employee = frappe.db.get_value(
            "Employee",
            {"employee_name": doc.customer},
            "name",
        )
        if employee:
            return employee

    return None


def _get_wallet(employee):
    """Get the active wallet for an employee."""
    wallet = frappe.db.get_value(
        "Canteen Employee Wallet",
        {"employee": employee, "is_active": 1},
        ["name", "balance", "credit_limit"],
        as_dict=True,
    )
    return wallet


def _validate_wallet_balance(wallet, amount):
    """Check if wallet has sufficient available balance."""
    available = flt(wallet.balance) + flt(wallet.credit_limit)
    if available < amount:
        frappe.throw(
            f"Insufficient wallet balance.\n"
            f"Available: ₹{available:,.2f} "
            f"(Balance: ₹{flt(wallet.balance):,.2f}, "
            f"Credit Limit: ₹{flt(wallet.credit_limit):,.2f})\n"
            f"Required: ₹{amount:,.2f}"
        )


def _deduct_wallet(wallet, amount, doc):
    """Deduct amount from employee wallet and create a Debit transaction."""
    wallet_doc = frappe.get_doc("Canteen Employee Wallet", wallet.name)
    new_balance = flt(wallet_doc.balance) - amount
    wallet_doc.balance = new_balance
    wallet_doc.save(ignore_permissions=True)

    txn = frappe.new_doc("Canteen Wallet Transaction")
    txn.wallet = wallet.name
    txn.employee = wallet_doc.employee
    txn.transaction_type = "Debit"
    txn.amount = amount
    txn.reference_document = doc.doctype
    txn.reference_name = doc.name
    txn.remarks = f"POS Invoice payment - {doc.name}"
    txn.insert(ignore_permissions=True)

    frappe.msgprint(
        f"₹{amount:,.2f} deducted from {wallet_doc.employee_name}'s wallet. "
        f"New balance: ₹{new_balance:,.2f}",
        indicator="green",
        alert=True,
    )


def _refund_wallet(wallet, amount, doc):
    """Refund amount back to employee wallet and create a Credit transaction."""
    wallet_doc = frappe.get_doc("Canteen Employee Wallet", wallet.name)
    new_balance = flt(wallet_doc.balance) + amount
    wallet_doc.balance = new_balance
    wallet_doc.save(ignore_permissions=True)

    txn = frappe.new_doc("Canteen Wallet Transaction")
    txn.wallet = wallet.name
    txn.employee = wallet_doc.employee
    txn.transaction_type = "Credit"
    txn.amount = amount
    txn.reference_document = doc.doctype
    txn.reference_name = doc.name
    txn.remarks = f"POS Invoice cancelled - refund - {doc.name}"
    txn.insert(ignore_permissions=True)

    frappe.msgprint(
        f"₹{amount:,.2f} refunded to {wallet_doc.employee_name}'s wallet. "
        f"New balance: ₹{new_balance:,.2f}",
        indicator="blue",
        alert=True,
    )
