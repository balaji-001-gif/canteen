import frappe
from frappe.utils import flt


@frappe.whitelist(allow_guest=True)
def get_canteen_settings():
    """Get canteen settings as dictionary"""
    settings = frappe.cache().get_value("canteen_settings")
    if not settings:
        settings_doc = frappe.get_single("Canteen Settings")
        settings = {
            "canteen_name": settings_doc.canteen_name,
            "company": settings_doc.company,
            "currency": settings_doc.currency or "INR",
            "gst_number": settings_doc.gst_number,
            "default_tax_rate": settings_doc.tax_rate or 5,
            "enable_wallet": settings_doc.enable_wallet or 0,
            "enable_table_management": settings_doc.enable_table_management or 0,
            "low_stock_threshold": settings_doc.low_stock_threshold or 10,
            "auto_close_shift": settings_doc.auto_close_shift or 0,
            "enable_credit_sales": settings_doc.enable_credit_sales or 0,
            "max_credit_limit": settings_doc.max_credit_limit or 0,
            "low_stock_email": settings_doc.low_stock_email or "",
            "daily_report_email": settings_doc.daily_report_email or "",
            "receipt_header": settings_doc.receipt_header or "",
            "receipt_footer": settings_doc.receipt_footer or "",
        }
        frappe.cache().set_value("canteen_settings", settings, expires_in_sec=3600)
    return settings


@frappe.whitelist(allow_guest=True)
def format_currency(amount, currency=None):
    """Format amount with currency symbol"""
    if currency is None:
        settings = get_canteen_settings()
        currency = settings.get("currency", "INR")
    return frappe.format_value(flt(amount), {"fieldtype": "Currency", "options": currency})


def get_payment_modes():
    """Get active payment modes from settings"""
    settings = frappe.get_single("Canteen Settings")
    modes = []
    for mode in settings.accepted_payment_modes:
        if mode.is_active:
            modes.append({
                "mode": mode.payment_mode,
                "label": mode.mode_label or mode.payment_mode,
                "is_default": mode.is_default
            })
    return modes


def get_dashboard_stats():
    """Get dashboard statistics"""
    today_orders = frappe.db.count("Canteen Order", {
        "order_date": frappe.utils.today(),
        "docstatus": 1
    })
    
    today_sales = frappe.db.get_all(
        "Canteen Order",
        filters={"order_date": frappe.utils.today(), "docstatus": 1},
        fields=["total_amount"]
    )
    total_sales = sum(o.total_amount for o in today_sales if o.total_amount)
    
    active_shifts = frappe.db.count("Canteen Shift", {"status": "Active"})
    
    low_stock_items = frappe.db.count("Canteen Inventory",
        filters=[["current_quantity", "<=", "minimum_quantity"]]
    )
    
    return {
        "today_orders": today_orders,
        "today_sales": total_sales,
        "active_shifts": active_shifts,
        "low_stock_items": low_stock_items
    }
