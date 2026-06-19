import frappe
from frappe.utils import today, now_datetime, add_days, flt


def send_daily_sales_summary():
    """Send daily sales summary to configured email"""
    settings = frappe.get_single("Canteen Settings")
    if not settings.daily_report_email:
        return
    
    today_str = today()
    
    orders = frappe.get_all(
        "Canteen Order",
        filters={"order_date": today_str, "docstatus": 1},
        fields=["total_amount", "order_type", "payment_mode"]
    )
    
    total_sales = sum(flt(o.total_amount) for o in orders)
    order_count = len(orders)
    
    by_type = {}
    by_payment = {}
    for order in orders:
        ot = order.order_type or "Unknown"
        by_type[ot] = by_type.get(ot, 0) + 1
        pm = order.payment_mode or "Unknown"
        by_payment[pm] = by_payment.get(pm, 0) + flt(order.total_amount)
    
    type_summary = "\n".join(f"- {k}: {v} orders" for k, v in sorted(by_type.items()))
    payment_summary = "\n".join(f"- {k}: {v:.2f}" for k, v in sorted(by_payment.items()))
    
    message = f"""
    <h2>Canteen Daily Sales Summary</h2>
    <p><strong>Date:</strong> {today_str}</p>
    
    <h3>Overview</h3>
    <ul>
        <li><strong>Total Sales:</strong> {total_sales:.2f}</li>
        <li><strong>Total Orders:</strong> {order_count}</li>
    </ul>
    
    <h3>Orders by Type</h3>
    <pre>{type_summary}</pre>
    
    <h3>Sales by Payment Mode</h3>
    <pre>{payment_summary}</pre>
    """
    
    frappe.sendmail(
        recipients=[settings.daily_report_email],
        subject=f"Canteen Daily Sales Summary - {today_str}",
        message=message
    )


def weekly_report():
    """Send weekly canteen report"""
    settings = frappe.get_single("Canteen Settings")
    if not settings.daily_report_email:
        return
    
    end_date = today()
    start_date = add_days(end_date, -7)
    
    orders = frappe.get_all(
        "Canteen Order",
        filters=[["order_date", ">=", start_date], ["order_date", "<=", end_date], ["docstatus", "=", 1]],
        fields=["total_amount", "order_date"]
    )
    
    total_sales = sum(flt(o.total_amount) for o in orders)
    order_count = len(orders)
    avg_sale = total_sales / order_count if order_count else 0
    
    # Group by day
    daily_sales = {}
    for order in orders:
        day = order.order_date.strftime("%A") if hasattr(order.order_date, "strftime") else str(order.order_date)
        daily_sales[day] = daily_sales.get(day, 0) + flt(order.total_amount)
    
    daily_summary = "\n".join(f"- {day}: {amount:.2f}" for day, amount in sorted(daily_sales.items()))
    
    message = f"""
    <h2>Canteen Weekly Report</h2>
    <p><strong>Period:</strong> {start_date} to {end_date}</p>
    
    <h3>Summary</h3>
    <ul>
        <li><strong>Total Sales:</strong> {total_sales:.2f}</li>
        <li><strong>Total Orders:</strong> {order_count}</li>
        <li><strong>Average Order Value:</strong> {avg_sale:.2f}</li>
    </ul>
    
    <h3>Daily Breakdown</h3>
    <pre>{daily_summary}</pre>
    """
    
    frappe.sendmail(
        recipients=[settings.daily_report_email],
        subject=f"Canteen Weekly Report - {start_date} to {end_date}",
        message=message
    )


def check_shift_alerts():
    """Check for shifts that should be auto-closed"""
    settings = frappe.get_single("Canteen Settings")
    if not settings.auto_close_shift:
        return
    
    active_shifts = frappe.get_all(
        "Canteen Shift",
        filters={"status": "Active"},
        fields=["name", "shift_name", "end_time", "cashier"]
    )
    
    now_time = now_datetime().time()
    
    for shift in active_shifts:
        if shift.end_time and shift.end_time <= now_time:
            doc = frappe.get_doc("Canteen Shift", shift.name)
            doc.status = "Closed"
            doc.calculate_totals()
            doc.save(ignore_permissions=True)
            
            frappe.sendmail(
                recipients=[frappe.db.get_value("User", shift.cashier, "email")],
                subject=f"Shift Auto-Closed: {shift.shift_name}",
                message=f"Your shift '{shift.shift_name}' has been auto-closed as it has reached its end time."
            )
