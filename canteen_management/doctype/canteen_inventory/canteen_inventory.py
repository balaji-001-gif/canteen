import frappe
from frappe.model.document import Document
from frappe.utils import flt, now


class CanteenInventory(Document):
    def validate(self):
        if flt(self.current_quantity) < 0:
            frappe.throw("Current quantity cannot be negative")
        
        if flt(self.minimum_quantity) < 0:
            frappe.throw("Minimum quantity cannot be negative")

    def before_save(self):
        self.last_updated = now()

    def after_save(self):
        self.update_item_stock()
        
        if flt(self.current_quantity) <= flt(self.minimum_quantity):
            self.flag_low_stock()

    def update_item_stock(self):
        frappe.db.set_value(
            "Canteen Item",
            self.item,
            "current_stock",
            self.current_quantity
        )

    def flag_low_stock(self):
        frappe.publish_realtime(
            event="canteen_low_stock",
            message={
                "item": self.item,
                "item_name": self.item_name,
                "current_quantity": self.current_quantity,
                "minimum_quantity": self.minimum_quantity
            }
        )


@frappe.whitelist()
def check_low_stock():
    """Check for low stock items and send alerts"""
    settings = frappe.get_single("Canteen Settings")
    
    low_stock_items = frappe.get_all(
        "Canteen Inventory",
        filters=[["current_quantity", "<=", "minimum_quantity"]],
        fields=["item", "item_name", "current_quantity", "minimum_quantity"]
    )
    
    if low_stock_items and settings.low_stock_email:
        items_text = "\n".join([
            f"- {item.item_name}: {item.current_quantity} (min: {item.minimum_quantity})"
            for item in low_stock_items
        ])
        
        frappe.sendmail(
            recipients=[settings.low_stock_email],
            subject="Canteen Low Stock Alert",
            message=f"""
            The following items are running low on stock:
            
            {items_text}
            
            Please replenish the stock as soon as possible.
            """
        )
    
    return low_stock_items


@frappe.whitelist()
def get_stock_summary():
    """Get inventory summary for dashboard"""
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
        "healthy_stock": total_items - low_stock - out_of_stock
    }
