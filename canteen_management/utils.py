import frappe
from frappe.utils import flt


def get_canteen_settings():
    """Get Canteen Settings - cached"""
    try:
        return frappe.get_cached_doc("Canteen Settings")
    except Exception:
        return frappe._dict()


def format_currency(amount, currency=None):
    """Format amount as currency string"""
    if not currency:
        try:
            settings = get_canteen_settings()
            currency = settings.currency or "INR"
        except Exception:
            currency = "INR"
    return frappe.utils.fmt_money(flt(amount), currency=currency)


@frappe.whitelist()
def get_dashboard_data():
    """Fetch summary data for the Canteen dashboard"""
    from frappe.utils import today

    today_date = today()

    today_sales = frappe.db.sql("""
        SELECT IFNULL(SUM(total_amount), 0) AS total,
               COUNT(*) AS orders
        FROM `tabCanteen Order`
        WHERE order_date = %s AND docstatus = 1
    """, today_date, as_dict=True)[0]

    low_stock = frappe.db.sql("""
        SELECT COUNT(*) AS cnt
        FROM `tabCanteen Inventory`
        WHERE current_quantity <= minimum_quantity
    """, as_dict=True)[0].cnt

    active_shift = frappe.db.get_value(
        "Canteen Shift",
        {"status": "Active", "cashier": frappe.session.user},
        "name"
    )

    return {
        "today_sales": today_sales.total,
        "today_orders": today_sales.orders,
        "low_stock_items": low_stock,
        "active_shift": active_shift
    }
