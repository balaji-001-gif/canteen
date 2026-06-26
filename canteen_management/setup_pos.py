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
    """Create standard payment modes for the canteen."""
    abbr = frappe.db.get_value("Company", company, "abbr")
    modes_to_create = [
        {
            "mode_of_payment": "Cash",
            "type": "Cash",
            "account": f"Cash - {abbr}",
        },
        {
            "mode_of_payment": "Card",
            "type": "Bank",
            "account": None,  # user must set manually
        },
        {
            "mode_of_payment": "UPI",
            "type": "Bank",
            "account": None,  # user must set manually
        },
        {
            "mode_of_payment": "Wallet",
            "type": "Cash",
            "account": None,  # user must set manually
        },
    ]

    created_modes = []
    for mode_data in modes_to_create:
        name = mode_data["mode_of_payment"]
        existing = frappe.db.exists("Mode of Payment", name)
        if existing:
            print(f"  ✓ Mode of Payment already exists: {name}")
            created_modes.append(name)
            continue

        accounts = []
        if mode_data["account"]:
            if frappe.db.exists("Account", mode_data["account"]):
                accounts.append({
                    "company": company,
                    "default_account": mode_data["account"],
                })
            else:
                print(f"  ⚠ Account '{mode_data['account']}' not found — will need manual setup")

        doc = frappe.get_doc({
            "doctype": "Mode of Payment",
            "mode_of_payment": name,
            "type": mode_data["type"],
            "accounts": accounts,
        })
        doc.insert(ignore_permissions=True)
        print(f"  ✓ Created Mode of Payment: {name}")
        created_modes.append(name)

    return created_modes


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
    """Create a POS Profile configured for the canteen."""
    profile_name = "Canteen POS"

    existing = frappe.db.exists("POS Profile", profile_name)
    if existing:
        print(f"  ✓ POS Profile already exists: {profile_name}")
        return

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

    # Find default cash account
    abbr = frappe.db.get_value("Company", company, "abbr")
    cash_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": "Cash"},
        "name",
    )

    # Build payments table
    payments = []
    for i, mode in enumerate(payment_modes):
        payments.append({
            "mode_of_payment": mode,
            "default": 1 if i == 0 else 0,
        })

    doc = frappe.get_doc({
        "doctype": "POS Profile",
        "name": profile_name,
        "company": company,
        "warehouse": warehouse,
        "currency": frappe.db.get_single_value("Canteen Settings", "currency") or "INR",
        "income_account": income_account,
        "expense_account": frappe.db.get_value(
            "Account", {"company": company, "account_name": "Cost of Goods Sold"}, "name"
        ),
        "write_off_account": frappe.db.get_value(
            "Account", {"company": company, "account_name": "Write Off"}, "name"
        ),
        "payments": payments,
    })
    doc.insert(ignore_permissions=True)
    print(f"  ✓ Created POS Profile: {profile_name}")
