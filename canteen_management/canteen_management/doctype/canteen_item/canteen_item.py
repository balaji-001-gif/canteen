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

    def after_insert(self):
        """Create ERPNext Item + Price after inserting a new Canteen Item."""
        self._sync_to_erpnext()

    def after_save(self):
        self.update_inventory_record()

    def on_update(self):
        """Sync changes to the existing ERPNext Item + Price.
        on_update only fires for existing (saved) documents in Frappe, so this is safe."""
        self._sync_to_erpnext()

    # ------------------------------------------------------------------
    # ERPNext Standard Item sync
    # ------------------------------------------------------------------

    def _sync_to_erpnext(self):
        """Create or update the corresponding ERPNext standard Item and Item Price."""
        item_code = self.item_code
        item_group = self._get_canteen_item_group()

        existing_item = frappe.db.exists("Item", item_code)

        if existing_item:
            item_doc = frappe.get_doc("Item", item_code)
            item_doc.item_name = self.item_name
            item_doc.item_group = item_group
            item_doc.stock_uom = self.unit_of_measure or "Nos"
            item_doc.description = self.description or self.item_name
            item_doc.image = self.image
            item_doc.disabled = 0 if self.is_active else 1
            item_doc.flags.ignore_permissions = True
            item_doc.save()
        else:
            item_doc = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": self.item_name,
                "item_group": item_group,
                "stock_uom": self.unit_of_measure or "Nos",
                "is_stock_item": 1,
                "is_purchase_item": 0,
                "is_sales_item": 1,
                "description": self.description or self.item_name,
                "image": self.image,
                "disabled": 0 if self.is_active else 1,
                "include_item_in_manufacturing": 0,
            })
            item_doc.insert(ignore_permissions=True)

        # Create or update the Item Price
        self._sync_item_price(item_code)

    def _sync_item_price(self, item_code):
        """Create or update the Standard Selling price for this item."""
        if flt(self.selling_price) <= 0:
            return

        existing_price = frappe.db.get_value(
            "Item Price",
            {"item_code": item_code, "price_list": "Standard Selling"},
            "name",
        )

        if existing_price:
            price_doc = frappe.get_doc("Item Price", existing_price)
            price_doc.price_list_rate = flt(self.selling_price)
            price_doc.flags.ignore_permissions = True
            price_doc.save()
        else:
            price_doc = frappe.get_doc({
                "doctype": "Item Price",
                "item_code": item_code,
                "price_list": "Standard Selling",
                "price_list_rate": flt(self.selling_price),
            })
            price_doc.insert(ignore_permissions=True)

    def _get_canteen_item_group(self):
        """Return the 'Canteen' Item Group, creating it if needed."""
        ig_name = "Canteen"
        if not frappe.db.exists("Item Group", ig_name):
            doc = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": ig_name,
                "parent_item_group": "All Item Groups",
                "is_group": 0,
            })
            doc.insert(ignore_permissions=True)
        return ig_name

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
