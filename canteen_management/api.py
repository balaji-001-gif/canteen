# -*- coding: utf-8 -*-
"""
Canteen Management REST API

Endpoints for wallet, inventory, tables, settings, and dashboard.
All sales/order data comes from ERPNext POS Invoice.
"""

import frappe
from frappe.utils import flt, today


# =============================================================================
# Items (Canteen Item — menu management)
# =============================================================================

@frappe.whitelist()
def get_items(search_term=None, category=None, include_inactive=False):
    """Get canteen menu items with optional search and category filter."""
    filters = {}
    if not include_inactive:
        filters["is_active"] = 1
        filters["is_available"] = 1
    if category:
        filters["category"] = category

    or_filters = None
    if search_term:
        or_filters = [
            ["item_name", "like", f"%{search_term}%"],
            ["item_code", "like", f"%{search_term}%"],
            ["barcode", "=", search_term],
        ]

    items = frappe.get_all(
        "Canteen Item",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name", "item_code", "item_name", "category", "selling_price",
            "cost_price", "tax_rate", "image", "is_vegetarian", "is_vegan",
            "is_active", "is_available", "current_stock", "min_stock_level",
            "preparation_time", "barcode", "unit_of_measure",
        ],
        order_by="item_name asc",
        limit=200,
    )
    return items


@frappe.whitelist()
def get_item_detail(item_code):
    """Get full details of a single canteen item including stock."""
    item = frappe.get_doc("Canteen Item", item_code)
    inventory = frappe.db.get_value(
        "Canteen Inventory",
        {"item": item.name},
        ["current_quantity", "minimum_quantity", "maximum_quantity"],
        as_dict=True,
    )
    return {
        "name": item.name,
        "item_code": item.item_code,
        "item_name": item.item_name,
        "category": item.category,
        "selling_price": item.selling_price,
        "cost_price": item.cost_price,
        "tax_rate": item.tax_rate,
        "description": item.description,
        "image": item.image,
        "is_vegetarian": item.is_vegetarian,
        "is_vegan": item.is_vegan,
        "allergen_info": item.allergen_info,
        "preparation_time": item.preparation_time,
        "barcode": item.barcode,
        "unit_of_measure": item.unit_of_measure,
        "current_stock": inventory.current_quantity if inventory else 0,
        "min_stock_level": item.min_stock_level,
        "inventory_name": inventory.name if inventory else None,
    }


@frappe.whitelist()
def get_categories():
    """Get all active categories."""
    return frappe.get_all(
        "Canteen Category",
        filters={"is_active": 1},
        fields=["name", "category_name", "parent_category", "image", "sort_order"],
        order_by="sort_order asc, category_name asc",
    )


# =============================================================================
# Inventory / Stock (Canteen Inventory — custom stock tracking)
# =============================================================================

@frappe.whitelist()
def get_stock_summary():
    """Get inventory health summary."""
    total_items = frappe.db.count("Canteen Inventory")
    low_stock = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabCanteen Inventory`
        WHERE current_quantity <= minimum_quantity
        AND current_quantity > 0
    """, as_dict=True)[0].count
    out_of_stock = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabCanteen Inventory`
        WHERE current_quantity = 0
    """, as_dict=True)[0].count

    return {
        "total_items": total_items,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "healthy_stock": total_items - low_stock - out_of_stock,
    }


@frappe.whitelist()
def get_low_stock_items():
    """Get all inventory items that are low on stock."""
    items = frappe.get_all(
        "Canteen Inventory",
        filters=[["current_quantity", "<=", "minimum_quantity"]],
        fields=["name", "item", "item_name", "current_quantity", "minimum_quantity", "unit"],
        order_by="current_quantity asc",
    )
    return items


@frappe.whitelist()
def get_all_inventory():
    """Get all inventory records."""
    records = frappe.get_all(
        "Canteen Inventory",
        fields=["name", "item", "item_name", "current_quantity", "minimum_quantity",
                "maximum_quantity", "unit", "last_updated", "last_stock_entry", "notes"],
        order_by="item_name asc",
    )
    return records


@frappe.whitelist()
def get_stock_balance(item_code):
    """Get current stock balance for a single item."""
    inv = frappe.db.get_value(
        "Canteen Inventory",
        {"item": item_code},
        ["name", "item_name", "current_quantity", "minimum_quantity", "unit"],
        as_dict=True,
    )
    return inv or {"current_quantity": 0, "minimum_quantity": 0}


# =============================================================================
# Employee Wallet
# =============================================================================

@frappe.whitelist()
def get_wallet_balance(employee=None):
    """Get wallet balance for an employee."""
    if not employee:
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return None

    wallet = frappe.db.get_value(
        "Canteen Employee Wallet",
        {"employee": employee, "is_active": 1},
        ["name", "employee", "employee_name", "balance", "credit_limit"],
        as_dict=True,
    )
    if wallet:
        wallet["available_balance"] = flt(wallet.balance) + flt(wallet.credit_limit)
    return wallet


@frappe.whitelist()
def topup_wallet(wallet_name, amount, remarks=None):
    """Add funds to an employee wallet. Creates a Credit transaction."""
    amount = flt(amount)
    if amount <= 0:
        frappe.throw("Amount must be greater than 0")

    wallet = frappe.get_doc("Canteen Employee Wallet", wallet_name)
    wallet.balance = flt(wallet.balance) + amount
    wallet.save(ignore_permissions=True)

    txn = frappe.new_doc("Canteen Wallet Transaction")
    txn.wallet = wallet.name
    txn.employee = wallet.employee
    txn.transaction_type = "Credit"
    txn.amount = amount
    txn.remarks = remarks or "Wallet top-up"
    txn.insert(ignore_permissions=True)

    return {"status": "success", "new_balance": wallet.balance, "transaction": txn.name}


@frappe.whitelist()
def get_wallet_transactions(wallet_name, limit=20, offset=0):
    """Get transaction history for a wallet."""
    txns = frappe.get_all(
        "Canteen Wallet Transaction",
        filters={"wallet": wallet_name},
        fields=["name", "transaction_type", "amount", "reference_document",
                "reference_name", "remarks", "date", "creation"],
        order_by="creation desc",
        limit=limit,
        start=offset,
    )
    return txns


@frappe.whitelist()
def create_wallet_for_employee(employee):
    """Create a wallet for an employee if they don't have one."""
    existing = frappe.db.exists("Canteen Employee Wallet", {"employee": employee})
    if existing:
        return {"status": "exists", "wallet": existing}

    emp = frappe.get_doc("Employee", employee)
    wallet = frappe.new_doc("Canteen Employee Wallet")
    wallet.employee = employee
    wallet.employee_name = emp.employee_name
    wallet.balance = 0
    wallet.is_active = 1
    wallet.insert(ignore_permissions=True)

    return {"status": "created", "wallet": wallet.name}


@frappe.whitelist()
def list_wallets(filters=None):
    """List all employee wallets."""
    f = {}
    if filters:
        if filters.get("is_active") is not None:
            f["is_active"] = 1 if filters["is_active"] else 0
        if filters.get("employee"):
            f["employee"] = filters["employee"]

    wallets = frappe.get_all(
        "Canteen Employee Wallet",
        filters=f,
        fields=["name", "employee", "employee_name", "department",
                "balance", "credit_limit", "is_active"],
        order_by="employee_name asc",
    )
    return wallets


# =============================================================================
# Tables
# =============================================================================

@frappe.whitelist()
def get_tables():
    """Get all active tables."""
    tables = frappe.get_all(
        "Canteen Table",
        filters={"is_active": 1},
        fields=["name", "table_name", "table_number", "capacity", "status", "location"],
        order_by="table_number asc",
    )
    return tables


@frappe.whitelist()
def get_available_tables():
    """Get only available tables."""
    tables = frappe.get_all(
        "Canteen Table",
        filters={"status": "Available", "is_active": 1},
        fields=["name", "table_name", "table_number", "capacity", "location"],
        order_by="table_number asc",
    )
    return tables


@frappe.whitelist()
def update_table_status(table_name, status):
    """Update table status (Available/Occupied/Reserved/Maintenance)."""
    valid = ["Available", "Occupied", "Reserved", "Maintenance"]
    if status not in valid:
        frappe.throw(f"Invalid status: {status}")

    doc = frappe.get_doc("Canteen Table", table_name)
    doc.status = status
    doc.save(ignore_permissions=True)
    return {"status": "success", "table": table_name, "new_status": status}


# =============================================================================
# Canteen Settings
# =============================================================================

@frappe.whitelist()
def get_settings():
    """Get canteen settings."""
    return _get_settings_dict()


def _get_settings_dict():
    settings = frappe.cache().get_value("canteen_settings_api")
    if settings:
        return settings

    doc = frappe.get_single("Canteen Settings")
    payment_modes = []
    for mode in doc.accepted_payment_modes:
        if mode.is_active:
            payment_modes.append({
                "mode": mode.payment_mode,
                "label": mode.mode_label or mode.payment_mode,
                "is_default": mode.is_default,
            })

    settings = {
        "canteen_name": doc.canteen_name,
        "company": doc.company,
        "currency": doc.currency or "INR",
        "gst_number": doc.gst_number,
        "default_tax_rate": doc.tax_rate or 5,
        "enable_wallet": doc.enable_wallet or 0,
        "enable_table_management": doc.enable_table_management or 0,
        "enable_credit_sales": doc.enable_credit_sales or 0,
        "max_credit_limit": doc.max_credit_limit or 0,
        "low_stock_threshold": doc.low_stock_threshold or 10,
        "auto_close_shift": doc.auto_close_shift or 0,
        "receipt_header": doc.receipt_header or "",
        "receipt_footer": doc.receipt_footer or "",
        "default_printer": doc.default_printer or "",
        "payment_modes": payment_modes,
    }
    frappe.cache().set_value("canteen_settings_api", settings, expires_in_sec=300)
    return settings


# =============================================================================
# Dashboard (powered by ERPNext POS Invoice)
# =============================================================================

@frappe.whitelist()
def get_dashboard_stats():
    """Get dashboard statistics from POS Invoice."""
    return _get_dashboard_stats()


def _get_dashboard_stats():
    today_str = today()

    today_orders = frappe.db.count("POS Invoice", {
        "posting_date": today_str, "docstatus": 1, "is_return": 0
    })

    today_sales_data = frappe.db.get_all(
        "POS Invoice",
        filters={"posting_date": today_str, "docstatus": 1, "is_return": 0},
        fields=["grand_total"],
    )
    today_sales = sum(flt(o.grand_total) for o in today_sales_data)

    low_stock_count = frappe.db.count("Canteen Inventory",
        filters=[["current_quantity", "<=", "minimum_quantity"]]
    )

    return {
        "today_orders": today_orders,
        "today_sales": today_sales,
        "low_stock_items": low_stock_count,
        "currency": frappe.db.get_single_value("Canteen Settings", "currency") or "INR",
    }


@frappe.whitelist()
def get_sales_overview(days=7):
    """Get sales overview for the last N days from POS Invoice."""
    from frappe.utils import add_days
    end_date = today()
    start_date = add_days(end_date, -days)

    orders = frappe.db.sql("""
        SELECT
            DATE(posting_date) as date,
            COUNT(*) as order_count,
            SUM(grand_total) as total_sales,
            AVG(grand_total) as avg_order
        FROM `tabPOS Invoice`
        WHERE posting_date BETWEEN %(start)s AND %(end)s
            AND docstatus = 1
            AND is_return = 0
        GROUP BY DATE(posting_date)
        ORDER BY date ASC
    """, {"start": start_date, "end": end_date}, as_dict=True)

    payment_breakdown = frappe.db.sql("""
        SELECT
            pm.mode_of_payment AS payment_mode,
            COUNT(*) as count,
            SUM(pm.amount) as total
        FROM `tabSales Invoice Payment` pm
        JOIN `tabPOS Invoice` pi ON pi.name = pm.parent
        WHERE pi.posting_date BETWEEN %(start)s AND %(end)s
            AND pi.docstatus = 1
            AND pi.is_return = 0
        GROUP BY pm.mode_of_payment
    """, {"start": start_date, "end": end_date}, as_dict=True)

    return {
        "period": {"start": start_date, "end": end_date, "days": days},
        "daily_breakdown": orders,
        "by_payment_mode": payment_breakdown,
    }


@frappe.whitelist()
def get_top_items(days=7, limit=10):
    """Get top-selling items from POS Invoice."""
    from frappe.utils import add_days
    start_date = add_days(today(), -days)

    items = frappe.db.sql("""
        SELECT
            pii.item_code AS item,
            pii.item_name,
            SUM(pii.qty) as total_qty,
            SUM(pii.amount) as total_amount
        FROM `tabPOS Invoice Item` pii
        JOIN `tabPOS Invoice` pi ON pi.name = pii.parent
        WHERE pi.posting_date >= %(start)s
            AND pi.docstatus = 1
            AND pi.is_return = 0
        GROUP BY pii.item_code, pii.item_name
        ORDER BY total_qty DESC
        LIMIT %(limit)s
    """, {"start": start_date, "limit": limit}, as_dict=True)
    return items


@frappe.whitelist()
def get_invoice_print_html(invoice_name):
    """Generate printable invoice HTML for a POS Invoice."""
    invoice = frappe.get_doc("POS Invoice", invoice_name)
    settings = frappe.get_single("Canteen Settings")
    html = frappe.render_template(
        "canteen_management/templates/invoice.html",
        {"invoice": invoice, "settings": settings},
    )
    return {"html": html, "name": invoice_name}
