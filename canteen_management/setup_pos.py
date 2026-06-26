# -*- coding: utf-8 -*-
"""
ERPNext Standard POS Setup for Canteen Management

Run this script once after deploying the app to configure ERPNext's
built-in POS system for use in the canteen.

Usage:
    bench --site your-site execute canteen_management.setup_pos.run

What it does:
    1. Creates standard ERPNext Modes of Payment (Cash, Card, UPI)
    2. Creates a canteen Warehouse (if it doesn't exist)
    3. Creates an "Canteen" Item Group (if it doesn't exist)
    4. Creates standard Items from all active Canteen Items
    5. Creates Item Prices for each item
    6. Creates a POS Profile configured for the canteen
"""

import frappe
from frappe.utils import flt


def run():
    """Main entry point — run all setup steps."""
    print("=" * 60)
    print("Canteen Management — ERPNext Standard POS Setup")
    print("=" * 60)

    company = _get_company()
    if not company:
        return

    warehouse = _create_warehouse(company)
    item_group = _create_item_group()
    payment_modes = _create_payment_modes(company)
    _create_items(item_group)
    _create_pos_profile(company, warehouse, payment_modes)

    frappe.db.commit()
    print("\n✅ Setup complete! Now go to:")
    print("   Point of Sale > POS > New Opening Entry")
    print("   to start your first shift, then open the POS interface.")
    print("=" * 60)


def _get_company():
    """Get the company from Canteen Settings, or prompt the user."""
    try:
        settings = frappe.get_single("Canteen Settings")
        if settings.company:
            print(f"  ✓ Using company: {settings.company}")
            return settings.company
    except Exception:
        pass

    # Fall back to first available company
    companies = frappe.get_all("Company", limit=1)
    if companies:
        print(f"  ✓ Using company: {companies[0].name}")
        return companies[0].name

    print("  ❌ No company found. Please create a Company first in ERPNext.")
    return None


def _create_warehouse(company):
    """Create a canteen warehouse if it doesn't exist."""
    wh_name = "Canteen - " + frappe.db.get_value("Company", company, "abbr")

    existing = frappe.db.exists("Warehouse", wh_name)
    if existing:
        print(f"  ✓ Warehouse already exists: {wh_name}")
        return existing

    doc = frappe.get_doc({
        "doctype": "Warehouse",
        "warehouse_name": "Canteen",
        "company": company,
        "is_group": 0,
    })
    doc.insert(ignore_permissions=True)
    print(f"  ✓ Created warehouse: {wh_name}")
    return doc.name


def _create_item_group():
    """Create a Canteen item group for organization."""
    ig_name = "Canteen"

    existing = frappe.db.exists("Item Group", ig_name)
    if existing:
        print(f"  ✓ Item group already exists: {ig_name}")
        return existing

    doc = frappe.get_doc({
        "doctype": "Item Group",
        "item_group_name": ig_name,
        "parent_item_group": "All Item Groups",
        "is_group": 0,
    })
    doc.insert(ignore_permissions=True)
    print(f"  ✓ Created item group: {ig_name}")
    return doc.name


def _create_payment_modes(company):
    """Create standard payment modes for the canteen.
    Returns list of (mode_name, has_account) tuples.
    """
    abbr = frappe.db.get_value("Company", company, "abbr")
    modes_to_create = [
        {
            "mode_of_payment": "Cash",
            "type": "Cash",
            "account_hint": f"Cash - {abbr}",
        },
        {
            "mode_of_payment": "Card",
            "type": "Bank",
            "account_hint": None,  # will try to find automatically
        },
        {
            "mode_of_payment": "UPI",
            "type": "Bank",
            "account_hint": None,
        },
        {
            "mode_of_payment": "Wallet",
            "type": "Cash",
            "account_hint": None,
        },
    ]

    results = []  # [(mode_name, has_account), ...]
    for mode_data in modes_to_create:
        name = mode_data["mode_of_payment"]
        existing = frappe.db.exists("Mode of Payment", name)

        # Try to find a suitable account
        account = _find_payment_account(mode_data, company, abbr)
        accounts = []
        if account:
            accounts.append({
                "company": company,
                "default_account": account,
            })

        if existing:
            # Update existing mode with account if missing
            mode_doc = frappe.get_doc("Mode of Payment", name)
            has_account = any(
                row.company == company for row in mode_doc.accounts
            )
            if not has_account and account:
                mode_doc.append("accounts", {
                    "company": company,
                    "default_account": account,
                })
                mode_doc.save(ignore_permissions=True)
                print(f"  ✓ Updated Mode of Payment: {name} → {account}")
            else:
                status = f" (account: {account})" if account else " (no account — manual setup needed)"
                print(f"  ✓ Mode of Payment already exists: {name}{status}")
            results.append((name, bool(account or has_account)))
            continue

        doc = frappe.get_doc({
            "doctype": "Mode of Payment",
            "mode_of_payment": name,
            "type": mode_data["type"],
            "accounts": accounts,
        })
        doc.insert(ignore_permissions=True)

        status = f" (account: {account})" if account else " (no account — manual setup needed)"
        print(f"  ✓ Created Mode of Payment: {name}{status}")
        results.append((name, bool(account)))

    return results


def _find_payment_account(mode_data, company, abbr):
    """Find a suitable default account for a payment mode."""
    name = mode_data["mode_of_payment"]
    mode_type = mode_data["type"]

    # 1. Try the explicit account hint first
    hint = mode_data.get("account_hint")
    if hint and frappe.db.exists("Account", hint):
        return hint

    # 2. For Bank-type (Card, UPI): find any active Bank account
    if mode_type == "Bank":
        bank_account = frappe.db.get_value(
            "Account",
            {"company": company, "account_type": "Bank", "is_group": 0, "disabled": 0},
            "name",
        )
        if bank_account:
            return bank_account

        # Try by naming pattern for common setups
        for try_name in [f"Bank - {abbr}", "Bank"]:
            if frappe.db.exists("Account", try_name):
                return try_name

    # 3. For Cash-type (Wallet): find any Cash account
    if mode_type == "Cash":
        cash_account = frappe.db.get_value(
            "Account",
            {"company": company, "account_type": "Cash", "is_group": 0, "disabled": 0},
            "name",
        )
        if cash_account:
            return cash_account

        # Try specific names
        for try_name in [f"Cash - {abbr}", f"Cash in Hand - {abbr}"]:
            if frappe.db.exists("Account", try_name):
                return try_name

    return None


def _create_items(item_group):
    """Create standard Items from active Canteen Items."""
    canteen_items = frappe.get_all(
        "Canteen Item",
        filters={"is_active": 1},
        fields=["name", "item_code", "item_name", "selling_price", "tax_rate",
                "cost_price", "unit_of_measure", "description"],
    )

    if not canteen_items:
        print("  ℹ No active Canteen Items found to sync.")
        return

    count = 0
    for ci in canteen_items:
        # Check if item already exists
        if frappe.db.exists("Item", ci.item_code):
            print(f"  ℹ Item already exists (skipped): {ci.item_code}")
            continue

        doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": ci.item_code,
            "item_name": ci.item_name,
            "item_group": item_group,
            "stock_uom": ci.unit_of_measure or "Nos",
            "is_stock_item": 1,
            "is_purchase_item": 0,
            "is_sales_item": 1,
            "description": ci.description or ci.item_name,
            "include_item_in_manufacturing": 0,
        })
        doc.insert(ignore_permissions=True)

        # Create Item Price
        if flt(ci.selling_price) > 0:
            if not frappe.db.exists("Item Price", {
                "item_code": ci.item_code,
                "price_list": "Standard Selling",
            }):
                price_doc = frappe.get_doc({
                    "doctype": "Item Price",
                    "item_code": ci.item_code,
                    "price_list": "Standard Selling",
                    "price_list_rate": flt(ci.selling_price),
                })
                price_doc.insert(ignore_permissions=True)

        count += 1
        print(f"  ✓ Created Item + Price: {ci.item_code} ({ci.item_name}) — ₹{ci.selling_price}")

    print(f"  → Synced {count} items to standard ERPNext Items")


def _create_pos_profile(company, warehouse, payment_modes):
    """Create a POS Profile configured for the canteen.

    payment_modes: list of (mode_name, has_account) tuples
    """
    profile_name = "Canteen POS"

    existing = frappe.db.exists("POS Profile", profile_name)
    if existing:
        print(f"  ✓ POS Profile already exists: {profile_name}")
        return

    abbr = frappe.db.get_value("Company", company, "abbr")

    # Find default income account
    income_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Income", "is_group": 0},
        "name",
    )
    if not income_account:
        income_account = frappe.db.get_value(
            "Account",
            {"company": company, "account_name": "Sales"},
            "name",
        )
    if not income_account:
        print("  ⚠ No income account found — POS Profile created but may need account setup")

    # Find expense account
    expense_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": "Cost of Goods Sold"},
        "name",
    ) or frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Expense Account", "is_group": 0},
        "name",
    )

    # Find write-off account
    write_off_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": "Write Off"},
        "name",
    )

    # Build payments table — only include modes with accounts configured
    payments = []
    modes_without_accounts = []
    for mode_name, has_account in payment_modes:
        if has_account:
            payments.append({
                "mode_of_payment": mode_name,
                "default": 1 if not payments else 0,
            })
        else:
            modes_without_accounts.append(mode_name)

    if modes_without_accounts:
        print(f"  ⚠ Skipped modes in POS Profile (no default account):")
        for m in modes_without_accounts:
            print(f"     - {m}")
        print(f"     → After creating accounts, edit the POS Profile and add them manually.")
        print(f"       Go to: Point of Sale > Settings > POS Profile > Canteen POS")

    if not payments:
        print("  ❌ No payment modes with accounts available. POS Profile not created.")
        print("     Please set up at least one Mode of Payment with a default account,")
        print("     then re-run this script.")
        return

    doc = frappe.get_doc({
        "doctype": "POS Profile",
        "name": profile_name,
        "company": company,
        "warehouse": warehouse,
        "currency": frappe.db.get_single_value("Canteen Settings", "currency") or "INR",
        "income_account": income_account,
        "expense_account": expense_account,
        "write_off_account": write_off_account,
        "payments": payments,
    })
    doc.insert(ignore_permissions=True)
    print(f"  ✓ Created POS Profile: {profile_name} (with {len(payments)} payment mode(s))")
