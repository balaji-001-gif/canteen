import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CanteenItem(Document):
    def validate(self):
        if flt(self.selling_price) < 0:
            frappe.throw("Selling price cannot be negative")
        
        if flt(self.cost_price) < 0:
            frappe.throw("Cost price cannot be negative")
        
        if flt(self.tax_rate) < 0 or flt(self.tax_rate) > 100:
            frappe.throw("Tax rate must be between 0 and 100")

    def after_save(self):
        self.update_inventory_record()

    def update_inventory_record(self):
        if not frappe.db.exists("Canteen Inventory", {"item": self.name}):
            inventory = frappe.new_doc("Canteen Inventory")
            inventory.item = self.name
            inventory.item_name = self.item_name
            inventory.current_quantity = 0
            inventory.minimum_quantity = self.min_stock_level
            inventory.unit = self.unit_of_measure
            inventory.insert(ignore_permissions=True)


@frappe.whitelist()
def get_item_details(item_code):
    """Get item details for POS"""
    item = frappe.get_doc("Canteen Item", item_code)
    if not item.is_active:
        frappe.throw(f"Item {item_code} is not active")
    
    inventory = frappe.db.get_value(
        "Canteen Inventory",
        {"item": item_code},
        ["current_quantity", "minimum_quantity"],
        as_dict=True
    )
    
    return {
        "item_code": item.item_code,
        "item_name": item.item_name,
        "selling_price": item.selling_price,
        "tax_rate": item.tax_rate,
        "is_vegetarian": item.is_vegetarian,
        "current_stock": inventory.get("current_quantity", 0) if inventory else 0,
        "image": item.image,
        "preparation_time": item.preparation_time
    }


@frappe.whitelist()
def search_items(search_term, category=None):
    """Search items for POS"""
    filters = {
        "is_active": 1,
        "is_available": 1
    }
    
    if category:
        filters["category"] = category
    
    items = frappe.get_all(
        "Canteen Item",
        filters=filters,
        fields=["item_code", "item_name", "selling_price", "tax_rate", 
                "image", "category", "is_vegetarian", "current_stock"],
        or_filters=[
            ["item_name", "like", f"%{search_term}%"],
            ["item_code", "like", f"%{search_term}%"],
            ["barcode", "=", search_term]
        ],
        order_by="item_name asc",
        limit=50
    )
    return items
