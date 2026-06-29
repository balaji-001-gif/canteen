import frappe
from frappe.utils import flt, today, add_days, now_datetime


def _get_topup_amount():
    """Read the monthly wallet top-up amount from Canteen Settings."""
    return flt(frappe.db.get_single_value("Canteen Settings", "monthly_wallet_topup")) or 0


def send_daily_sales_summary():
    """Send daily sales summary email"""
    settings = frappe.get_single("Canteen Settings")
    if not settings.daily_report_email:
        return

    yesterday = add_days(today(), -1)

    result = frappe.db.sql("""
        SELECT
            COUNT(*) AS total_orders,
            IFNULL(SUM(grand_total), 0) AS total_sales,
            IFNULL(SUM(total_taxes_and_charges), 0) AS total_tax,
            IFNULL(SUM(discount_amount), 0) AS total_discount
        FROM `tabPOS Invoice`
        WHERE posting_date = %s AND docstatus = 1 AND is_return = 0
    """, yesterday, as_dict=True)[0]

    message = f"""
    <h3>Daily Sales Summary - {yesterday}</h3>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><td>Total Orders</td><td><b>{result.total_orders}</b></td></tr>
        <tr><td>Total Sales</td><td><b>{result.total_sales}</b></td></tr>
        <tr><td>Total Tax</td><td>{result.total_tax}</td></tr>
        <tr><td>Total Discount</td><td>{result.total_discount}</td></tr>
    </table>
    """

    frappe.sendmail(
        recipients=[settings.daily_report_email],
        subject=f"Canteen Sales Summary - {yesterday}",
        message=message
    )


def monthly_wallet_topup():
    """Credit the configured top-up amount to every active employee wallet each month.

    The amount is read from Canteen Settings > Monthly Wallet Top-up Amount.
    Called by the Frappe scheduler on the 1st of each month.
    Idempotent: checks for an existing "Monthly wallet top-up" transaction
    in the current month before adding a new one.
    """
    now = now_datetime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    wallets = frappe.get_all(
        "Canteen Employee Wallet",
        filters={"is_active": 1},
        fields=["name", "employee", "employee_name", "balance"],
    )

    topup_amount = _get_topup_amount()
    if topup_amount <= 0 or not wallets:
        return

    topup_count = 0

    for wallet_data in wallets:
        # Check if already topped up this month
        already_done = frappe.db.exists("Canteen Wallet Transaction", {
            "wallet": wallet_data.name,
            "transaction_type": "Credit",
            "remarks": "Monthly wallet top-up",
            "date": [">=", month_start.strftime("%Y-%m-%d")],
        })

        if already_done:
            continue

        try:
            wallet_doc = frappe.get_doc("Canteen Employee Wallet", wallet_data.name)
            new_balance = flt(wallet_doc.balance) + topup_amount
            wallet_doc.balance = new_balance
            wallet_doc.total_credited = flt(wallet_doc.total_credited) + topup_amount
            wallet_doc.last_transaction_date = now
            wallet_doc.save(ignore_permissions=True)

            txn = frappe.new_doc("Canteen Wallet Transaction")
            txn.wallet = wallet_data.name
            txn.employee = wallet_data.employee
            txn.transaction_type = "Credit"
            txn.amount = topup_amount
            txn.balance_after = new_balance
            txn.remarks = "Monthly wallet top-up"
            txn.insert(ignore_permissions=True)

            topup_count += 1
        except Exception:
            frappe.log_error(
                f"Failed to top-up wallet {wallet_data.name} ({wallet_data.employee_name})",
                "Monthly Wallet Top-up",
            )

    if topup_count:
        frappe.log_error(
            f"Monthly wallet top-up: ₹{topup_amount:,.0f} credited to {topup_count} wallet(s).",
            "Monthly Wallet Top-up",
        )


def weekly_report():
    """Placeholder for weekly report task"""
    pass
