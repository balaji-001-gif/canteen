# -*- coding: utf-8 -*-
"""
Canteen Stock Entry Hooks — ERPNext Stock Ledger Sync

Hooks into the custom Canteen Stock Entry (on_submit / on_cancel) to
create corresponding ERPNext Stock Entries, keeping the ERPNext Stock
Ledger in sync whenever stock moves in/out of the canteen.

Mapping:
    Canteen Stock Type      → ERPNext Purpose
    ─────────────────────────────────────────────
    Purchase                → Material Receipt   (stock enters Canteen Warehouse)
    Opening Stock           → Material Receipt   (stock enters Canteen Warehouse)
    Return                  → Material Receipt   (stock enters Canteen Warehouse)
    Waste                   → Material Issue     (stock leaves Canteen Warehouse)
    Adjustment              → Material Issue     (stock leaves Canteen Warehouse)

Usage:
    Registered via hooks.py doc_events -> "Canteen Stock Entry"
"""

import frappe
from frappe.utils import flt, nowdate


# Stock types that INCREASE stock (stock enters the warehouse)
STOCK_IN_TYPES = ("Purchase", "Opening Stock", "Return")

# Stock types that DECREASE stock (stock leaves the warehouse)
STOCK_OUT_TYPES = ("Waste", "Adjustment")


# =============================================================================
# Canteen Stock Entry on_submit
# =============================================================================

def stock_entry_on_submit(doc, method):
    """Create an ERPNext Stock Entry when a Canteen Stock Entry is submitted."""
    company = _get_company()
    if not company:
        return

    warehouse = _get_canteen_warehouse(company)
    if not warehouse:
        frappe.throw(
            "Canteen Warehouse not found. Please run the POS setup script first:\n"
            "  bench --site your-site execute canteen_management.setup_pos.run"
        )

    purpose = _get_erpnext_purpose(doc.stock_type)
    if not purpose:
        return  # Unknown stock type — skip

    erpnext_doc = frappe.get_doc({
        "doctype": "Stock Entry",
        "purpose": purpose,
        "company": company,
        "posting_date": doc.posting_date or nowdate(),
        "posting_time": doc.posting_time,
        "canteen_stock_entry_ref": doc.name,
        "remarks": doc.remarks or f"Canteen Stock Entry - {doc.name} ({doc.stock_type})",
        "items": _build_items(doc, purpose, warehouse),
    })

    erpnext_doc.insert(ignore_permissions=True)
    erpnext_doc.submit()

    # Store the ERPNext Stock Entry name on the Canteen Stock Entry for reference
    frappe.db.set_value(
        doc.doctype,
        doc.name,
        "remarks",
        (doc.remarks or "") + f"\n[ERPNext Stock Entry: {erpnext_doc.name}]",
    )


# =============================================================================
# Canteen Stock Entry on_cancel
# =============================================================================

def stock_entry_on_cancel(doc, method):
    """Cancel the corresponding ERPNext Stock Entry when a Canteen Stock Entry is cancelled."""
    # Find the ERPNext Stock Entry by the custom reference field
    erpnext_entry_name = frappe.db.get_value(
        "Stock Entry",
        {"custom_canteen_stock_entry_ref": doc.name, "docstatus": 1},
        "name",
    )

    if not erpnext_entry_name:
        return  # No matching ERPNext Stock Entry found — nothing to cancel

    erpnext_doc = frappe.get_doc("Stock Entry", erpnext_entry_name)
    erpnext_doc.cancel()

    frappe.msgprint(
        f"Cancelled ERPNext Stock Entry: {erpnext_entry_name}",
        indicator="blue",
        alert=True,
    )


# =============================================================================
# Internal helpers
# =============================================================================

def _get_company():
    """Get the company from Canteen Settings."""
    try:
        settings = frappe.get_single("Canteen Settings")
        if settings.company:
            return settings.company
    except Exception:
        pass

    # Fallback: first available company
    companies = frappe.get_all("Company", limit=1)
    if companies:
        return companies[0].name

    frappe.throw("No company found. Please configure Canteen Settings first.")
    return None


def _get_canteen_warehouse(company):
    """Get the Canteen Warehouse name for the given company."""
    abbr = frappe.db.get_value("Company", company, "abbr")
    warehouse_name = f"Canteen - {abbr}"
    if frappe.db.exists("Warehouse", warehouse_name):
        return warehouse_name
    return None


def _get_erpnext_purpose(stock_type):
    """Map Canteen Stock Entry types to ERPNext Stock Entry purposes."""
    if stock_type in STOCK_IN_TYPES:
        return "Material Receipt"
    elif stock_type in STOCK_OUT_TYPES:
        return "Material Issue"

    frappe.msgprint(
        f"Unknown Canteen Stock Entry type: {stock_type}. "
        f"No ERPNext Stock Entry created.",
        indicator="orange",
        alert=True,
    )
    return None


def _build_items(doc, purpose, warehouse):
    """Build the items child table for the ERPNext Stock Entry.

    - Material Receipt: t_warehouse = Canteen Warehouse (stock goes in)
    - Material Issue:   s_warehouse = Canteen Warehouse (stock goes out)
    """
    items = []
    for row in doc.items:
        item_entry = {
            "item_code": row.item,          # item = Canteen Item name = item_code
            "item_name": row.item_name,
            "qty": flt(row.quantity),
            "basic_rate": flt(row.rate),
            "conversion_factor": 1,
        }

        if purpose == "Material Receipt":
            item_entry["t_warehouse"] = warehouse
        else:
            item_entry["s_warehouse"] = warehouse

        items.append(item_entry)

    return items
