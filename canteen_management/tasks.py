import frappe
from frappe.utils import today, add_days


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


def weekly_report():
    """Placeholder for weekly report task"""
    pass
