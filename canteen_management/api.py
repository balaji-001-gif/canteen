# -*- coding: utf-8 -*-
"""
Canteen Management REST API

Comprehensive REST API endpoints for the Canteen POS system.
All endpoints are callable via frappe.call() from the client side
or via /api/method/canteen_management.api.*
"""

import frappe
from frappe.utils import flt, today, nowtime, now


# =============================================================================
# POS Data  single endpoint to hydrate the POS interface
# =============================================================================

@frappe.whitelist()
def pos_data():
    """Return all data needed to bootstrap the POS in one call."""
    settings = _get_settings_dict()
    return {
        "settings": settings,
        "categories": _get_categories(),
        "items": get_items(),
        "tables": _get_tables() if settings.get("enable_table_management") else [],
        "active_shift": _get_active_shift(),
        "payment_modes": _get_payment_modes(),
        "dashboard_stats": _get_dashboard_stats(),
    }


# =============================================================================
# Items
# =============================================================================

@frappe.whitelist()
def get_items(search_term=None, category=None, include_inactive=False):
    """Get menu items for POS with optional search and category filter."""
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
    """Get full details of a single item including stock."""
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
    return _get_categories()


def _get_categories():
    return frappe.get_all(
        "Canteen Category",
        filters={"is_active": 1},
        fields=["name", "category_name", "parent_category", "image", "sort_order"],
        order_by="sort_order asc, category_name asc",
    )


# =============================================================================
# Orders
# =============================================================================

@frappe.whitelist()
def create_order(items, order_type="Dine In", payment_mode="Cash",
                 paid_amount=None, employee=None, customer_name=None,
                 table_no=None, shift=None, discount_amount=0,
                 special_instructions=None):
    """Create and submit a new canteen order via POS.

    Args:
        items: List of dicts [{item, qty, rate, tax_rate?}]
        order_type: Dine In / Take Away / Delivery / Bulk Order
        payment_mode: Cash / Card / UPI / Wallet / Credit
        paid_amount: Amount paid by customer
        employee: Employee link (for wallet payments)
        customer_name: Customer name
        table_no: Table link (for dine-in)
        shift: Shift link
        discount_amount: Discount on total
        special_instructions: Notes for kitchen
    """
    doc = frappe.new_doc("Canteen Order")
    doc.order_type = order_type
    doc.payment_mode = payment_mode
    doc.discount_amount = flt(discount_amount)

    if customer_name:
        doc.customer_name = customer_name
    if employee:
        doc.employee = employee
        doc.employee_name = frappe.db.get_value("Employee", employee, "employee_name")
    if table_no:
        doc.table_no = table_no
    if shift:
        doc.shift = shift
    if special_instructions:
        doc.special_instructions = special_instructions

    for item_data in items:
        row = doc.append("items", {})
        row.item = item_data.get("item")
        row.item_name = item_data.get("item_name") or frappe.db.get_value(
            "Canteen Item", item_data["item"], "item_name"
        )
        row.quantity = flt(item_data.get("qty", 1))
        row.rate = flt(item_data.get("rate", 0))
        row.tax_rate = flt(item_data.get("tax_rate", 0))

    doc.insert(ignore_permissions=True)

    if paid_amount:
        doc.paid_amount = flt(paid_amount)
    doc.submit()

    # Update table status to Occupied if dine-in
    if table_no and order_type == "Dine In":
        table_doc = frappe.get_doc("Canteen Table", table_no)
        table_doc.status = "Occupied"
        table_doc.save(ignore_permissions=True)

    return {
        "name": doc.name,
        "status": doc.status,
        "total_amount": doc.total_amount,
        "subtotal": doc.subtotal,
        "tax_amount": doc.tax_amount,
        "change_amount": doc.change_amount,
        "invoice": frappe.db.get_value("Canteen Invoice", {"order": doc.name}, "name"),
    }


@frappe.whitelist()
def get_order(order_name):
    """Get full order details."""
    doc = frappe.get_doc("Canteen Order", order_name)
    return _serialize_order(doc)


def _serialize_order(doc):
    items = []
    for row in doc.items:
        items.append({
            "item": row.item,
            "item_name": row.item_name,
            "quantity": row.quantity,
            "rate": row.rate,
            "tax_rate": row.tax_rate,
            "amount": row.amount,
            "tax_amount": row.tax_amount,
            "total_amount": row.total_amount,
            "special_note": row.special_note,
        })
    return {
        "name": doc.name,
        "order_date": str(doc.order_date) if doc.order_date else None,
        "order_time": str(doc.order_time) if doc.order_time else None,
        "status": doc.status,
        "order_type": doc.order_type,
        "employee": doc.employee,
        "employee_name": doc.employee_name,
        "customer_name": doc.customer_name,
        "table_no": doc.table_no,
        "cashier": doc.cashier,
        "shift": doc.shift,
        "items": items,
        "subtotal": doc.subtotal,
        "tax_amount": doc.tax_amount,
        "discount_amount": doc.discount_amount,
        "total_amount": doc.total_amount,
        "payment_mode": doc.payment_mode,
        "paid_amount": doc.paid_amount,
        "change_amount": doc.change_amount,
        "special_instructions": doc.special_instructions,
        "docstatus": doc.docstatus,
        "amended_from": doc.amended_from,
    }


@frappe.whitelist()
def list_orders(filters=None, limit=50, offset=0):
    """List orders with optional filters.

    Filters can include: order_date, status, order_type, cashier, employee, shift.
    """
    f = {"docstatus": ["!=", 2]}
    if filters:
        if filters.get("order_date"):
            f["order_date"] = filters["order_date"]
        if filters.get("status"):
            f["status"] = filters["status"]
        if filters.get("order_type"):
            f["order_type"] = filters["order_type"]
        if filters.get("cashier"):
            f["cashier"] = filters["cashier"]
        if filters.get("employee"):
            f["employee"] = filters["employee"]
        if filters.get("shift"):
            f["shift"] = filters["shift"]

    orders = frappe.get_all(
        "Canteen Order",
        filters=f,
        fields=[
            "name", "order_date", "order_time", "status", "order_type",
            "customer_name", "table_no", "cashier", "employee_name",
            "total_amount", "payment_mode", "shift", "docstatus",
        ],
        order_by="creation desc",
        limit=limit,
        start=offset,
    )
    return orders


@frappe.whitelist()
def update_order_status(order_name, status):
    """Update order status (e.g. Pending -> Preparing -> Ready -> Served)."""
    valid_statuses = ["Pending", "Preparing", "Ready", "Served", "Completed", "Cancelled"]
    if status not in valid_statuses:
        frappe.throw(f"Invalid status: {status}. Must be one of {', '.join(valid_statuses)}")

    doc = frappe.get_doc("Canteen Order", order_name)
    doc.status = status
    doc.save(ignore_permissions=True)
    return {"status": "success", "order": order_name, "new_status": status}


@frappe.whitelist()
def cancel_order(order_name):
    """Cancel an order. Will also cancel the linked invoice."""
    doc = frappe.get_doc("Canteen Order", order_name)
    if doc.docstatus != 1:
        frappe.throw("Only submitted orders can be cancelled")
    doc.cancel()
    return {"status": "success", "order": order_name, "message": "Order cancelled"}


@frappe.whitelist()
def get_today_orders():
    """Get all orders for today (quick POS list)."""
    orders = frappe.get_all(
        "Canteen Order",
        filters={"order_date": today(), "docstatus": ["!=", 2]},
        fields=[
            "name", "order_time", "status", "order_type", "customer_name",
            "table_no", "total_amount", "payment_mode", "employee_name",
        ],
        order_by="creation desc",
        limit=100,
    )
    return orders


# =============================================================================
# Invoices
# =============================================================================

@frappe.whitelist()
def get_invoice(invoice_name):
    """Get full invoice details."""
    doc = frappe.get_doc("Canteen Invoice", invoice_name)
    items = []
    for row in doc.items:
        items.append({
            "item": row.item,
            "item_name": row.item_name,
            "quantity": row.quantity,
            "rate": row.rate,
            "amount": row.amount,
            "tax_amount": row.tax_amount,
            "total_amount": row.total_amount,
        })
    return {
        "name": doc.name,
        "order": doc.order,
        "invoice_date": str(doc.invoice_date) if doc.invoice_date else None,
        "status": doc.status,
        "employee": doc.employee,
        "employee_name": doc.employee_name,
        "customer_name": doc.customer_name,
        "cashier": doc.cashier,
        "shift": doc.shift,
        "items": items,
        "subtotal": doc.subtotal,
        "tax_amount": doc.tax_amount,
        "discount_amount": doc.discount_amount,
        "total_amount": doc.total_amount,
        "payment_mode": doc.payment_mode,
        "paid_amount": doc.paid_amount,
        "change_amount": doc.change_amount,
        "docstatus": doc.docstatus,
    }


@frappe.whitelist()
def get_invoice_print_html(invoice_name):
    """Generate printable invoice HTML for thermal receipt printer."""
    invoice = frappe.get_doc("Canteen Invoice", invoice_name)
    settings = frappe.get_single("Canteen Settings")
    html = frappe.render_template(
        "canteen_management/templates/invoice.html",
        {"invoice": invoice, "settings": settings},
    )
    return {"html": html, "name": invoice_name}


@frappe.whitelist()
def list_invoices(filters=None, limit=50, offset=0):
    """List invoices with optional filters."""
    f = {"docstatus": ["!=", 2]}
    if filters:
        if filters.get("invoice_date"):
            f["invoice_date"] = filters["invoice_date"]
        if filters.get("status"):
            f["status"] = filters["status"]
        if filters.get("cashier"):
            f["cashier"] = filters["cashier"]
        if filters.get("employee"):
            f["employee"] = filters["employee"]

    invoices = frappe.get_all(
        "Canteen Invoice",
        filters=f,
        fields=[
            "name", "order", "invoice_date", "status", "customer_name",
            "total_amount", "payment_mode", "cashier", "docstatus",
        ],
        order_by="creation desc",
        limit=limit,
        start=offset,
    )
    return invoices


# =============================================================================
# Inventory / Stock
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


@frappe.whitelist()
def create_stock_entry(stock_type, items, company=None, remarks=None):
    """Create and submit a stock entry.

    Args:
        stock_type: Inward / Outward / Adjustment / Wastage
        items: List of dicts [{item, qty, rate}]
        company: Company link
        remarks: Notes
    """
    doc = frappe.new_doc("Canteen Stock Entry")
    doc.stock_type = stock_type
    if company:
        doc.company = company
    if remarks:
        doc.remarks = remarks

    for item_data in items:
        row = doc.append("items", {})
        row.item = item_data["item"]
        row.item_name = item_data.get("item_name") or frappe.db.get_value(
            "Canteen Item", item_data["item"], "item_name"
        )
        row.quantity = flt(item_data.get("qty", 1))
        row.rate = flt(item_data.get("rate", 0))

    doc.insert(ignore_permissions=True)
    doc.submit()

    return {
        "name": doc.name,
        "status": "Submitted",
        "stock_type": stock_type,
        "total_quantity": doc.total_quantity,
        "total_amount": doc.total_amount,
    }


@frappe.whitelist()
def list_stock_entries(filters=None, limit=50, offset=0):
    """List stock entries."""
    f = {}
    if filters:
        if filters.get("stock_type"):
            f["stock_type"] = filters["stock_type"]
        if filters.get("posting_date"):
            f["posting_date"] = filters["posting_date"]
        if filters.get("status"):
            f["status"] = filters["status"]

    entries = frappe.get_all(
        "Canteen Stock Entry",
        filters=f,
        fields=["name", "posting_date", "posting_time", "stock_type", "company",
                "status", "total_quantity", "total_amount", "docstatus"],
        order_by="creation desc",
        limit=limit,
        start=offset,
    )
    return entries


# =============================================================================
# Employee Wallet
# =============================================================================

@frappe.whitelist()
def get_wallet_balance(employee=None):
    """Get wallet balance for an employee.
    If employee is omitted, gets wallet for the current user.
    """
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
# Shifts
# =============================================================================

@frappe.whitelist()
def open_shift(shift_name=None, opening_amount=0, cashier=None):
    """Open a new shift for the cashier."""
    if not cashier:
        cashier = frappe.session.user

    active = frappe.db.exists("Canteen Shift", {"status": "Active", "cashier": cashier})
    if active:
        frappe.throw(f"Cashier already has an active shift: {active}")

    doc = frappe.new_doc("Canteen Shift")
    doc.shift_name = shift_name or f"Shift-{today()}-{cashier}"
    doc.cashier = cashier
    doc.opening_amount = flt(opening_amount)
    doc.start_time = nowtime()
    doc.status = "Active"
    doc.insert(ignore_permissions=True)

    return {"status": "success", "shift": doc.name, "shift_name": doc.shift_name}


@frappe.whitelist()
def close_shift(shift_name, closing_amount=0):
    """Close an active shift and calculate totals."""
    doc = frappe.get_doc("Canteen Shift", shift_name)
    if doc.status != "Active":
        frappe.throw("Shift is not active")

    doc.status = "Closed"
    doc.closed_at = now()
    doc.closing_amount = flt(closing_amount)
    doc.calculate_totals()
    doc.save(ignore_permissions=True)

    return {
        "status": "success",
        "shift": doc.name,
        "total_sales": doc.total_sales,
        "total_orders": doc.total_orders,
        "closing_amount": doc.closing_amount,
    }


@frappe.whitelist()
def get_active_shift(cashier=None):
    """Get the active shift for a cashier."""
    return _get_active_shift(cashier)


def _get_active_shift(cashier=None):
    if not cashier:
        cashier = frappe.session.user
    shift = frappe.db.get_value(
        "Canteen Shift",
        {"status": "Active", "cashier": cashier},
        ["name", "shift_name", "start_time", "opening_amount", "opened_at", "cashier"],
        as_dict=True,
    )
    if shift:
        shift["order_count"] = frappe.db.count("Canteen Order",
            {"shift": shift.name, "docstatus": 1}
        )
    return shift


@frappe.whitelist()
def list_shifts(filters=None, limit=50, offset=0):
    """List shifts."""
    f = {}
    if filters:
        if filters.get("status"):
            f["status"] = filters["status"]
        if filters.get("cashier"):
            f["cashier"] = filters["cashier"]

    shifts = frappe.get_all(
        "Canteen Shift",
        filters=f,
        fields=["name", "shift_name", "status", "cashier", "start_time", "end_time",
                "opening_amount", "closing_amount", "total_sales", "total_orders",
                "opened_at", "closed_at"],
        order_by="creation desc",
        limit=limit,
        start=offset,
    )
    return shifts


# =============================================================================
# Tables
# =============================================================================

@frappe.whitelist()
def get_tables():
    """Get all tables."""
    return _get_tables()


def _get_tables():
    return frappe.get_all(
        "Canteen Table",
        fields=["name", "table_name", "table_no", "capacity", "status", "location"],
        order_by="table_no asc",
    )


@frappe.whitelist()
def get_available_tables():
    """Get only available tables."""
    tables = frappe.get_all(
        "Canteen Table",
        filters={"status": "Available"},
        fields=["name", "table_name", "table_no", "capacity", "location"],
        order_by="table_no asc",
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


def _get_payment_modes():
    settings = frappe.get_single("Canteen Settings")
    modes = []
    for mode in settings.accepted_payment_modes:
        if mode.is_active:
            modes.append({
                "mode": mode.payment_mode,
                "label": mode.mode_label or mode.payment_mode,
                "is_default": mode.is_default,
            })
    return modes


# =============================================================================
# Dashboard
# =============================================================================

@frappe.whitelist()
def get_dashboard_stats():
    """Get dashboard statistics."""
    return _get_dashboard_stats()


def _get_dashboard_stats():
    today_str = today()

    today_orders = frappe.db.count("Canteen Order", {
        "order_date": today_str, "docstatus": 1
    })

    today_sales_data = frappe.db.get_all(
        "Canteen Order",
        filters={"order_date": today_str, "docstatus": 1},
        fields=["total_amount"],
    )
    today_sales = sum(flt(o.total_amount) for o in today_sales_data)

    active_shifts = frappe.db.count("Canteen Shift", {"status": "Active"})

    low_stock_count = frappe.db.count("Canteen Inventory",
        filters=[["current_quantity", "<=", "minimum_quantity"]]
    )

    return {
        "today_orders": today_orders,
        "today_sales": today_sales,
        "active_shifts": active_shifts,
        "low_stock_items": low_stock_count,
        "currency": frappe.db.get_single_value("Canteen Settings", "currency") or "INR",
    }


@frappe.whitelist()
def get_sales_overview(days=7):
    """Get sales overview for the last N days."""
    from frappe.utils import add_days
    end_date = today()
    start_date = add_days(end_date, -days)

    orders = frappe.db.sql("""
        SELECT
            DATE(order_date) as date,
            COUNT(*) as order_count,
            SUM(total_amount) as total_sales,
            AVG(total_amount) as avg_order
        FROM `tabCanteen Order`
        WHERE order_date BETWEEN %(start)s AND %(end)s
            AND docstatus = 1
        GROUP BY DATE(order_date)
        ORDER BY date ASC
    """, {"start": start_date, "end": end_date}, as_dict=True)

    payment_breakdown = frappe.db.sql("""
        SELECT
            payment_mode,
            COUNT(*) as count,
            SUM(total_amount) as total
        FROM `tabCanteen Order`
        WHERE order_date BETWEEN %(start)s AND %(end)s
            AND docstatus = 1
        GROUP BY payment_mode
    """, {"start": start_date, "end": end_date}, as_dict=True)

    type_breakdown = frappe.db.sql("""
        SELECT
            order_type,
            COUNT(*) as count,
            SUM(total_amount) as total
        FROM `tabCanteen Order`
        WHERE order_date BETWEEN %(start)s AND %(end)s
            AND docstatus = 1
        GROUP BY order_type
    """, {"start": start_date, "end": end_date}, as_dict=True)

    return {
        "period": {"start": start_date, "end": end_date, "days": days},
        "daily_breakdown": orders,
        "by_payment_mode": payment_breakdown,
        "by_order_type": type_breakdown,
    }


@frappe.whitelist()
def get_top_items(days=7, limit=10):
    """Get top-selling items."""
    from frappe.utils import add_days
    start_date = add_days(today(), -days)

    items = frappe.db.sql("""
        SELECT
            oi.item,
            oi.item_name,
            SUM(oi.quantity) as total_qty,
            SUM(oi.total_amount) as total_amount
        FROM `tabCanteen Order Item` oi
        JOIN `tabCanteen Order` o ON o.name = oi.parent
        WHERE o.order_date >= %(start)s
            AND o.docstatus = 1
        GROUP BY oi.item, oi.item_name
        ORDER BY total_qty DESC
        LIMIT %(limit)s
    """, {"start": start_date, "limit": limit}, as_dict=True)
    return items
