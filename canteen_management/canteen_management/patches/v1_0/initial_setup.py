import frappe

def execute():
    """Initial setup patch for Canteen Management v1.0"""
    
    # Create default roles
    roles = ["Canteen Admin", "Canteen Manager", "Canteen Cashier", "Canteen Staff", "Canteen User"]
    for role_name in roles:
        if not frappe.db.exists("Role", role_name):
            role = frappe.new_doc("Role")
            role.role_name = role_name
            role.desk_access = 1
            role.insert(ignore_permissions=True)
    
    # Create default settings
    if not frappe.db.exists("Canteen Settings", "Canteen Settings"):
        settings = frappe.new_doc("Canteen Settings")
        settings.canteen_name = "Default Canteen"
        settings.company = frappe.db.get_single_value("Global Defaults", "default_company") or ""
        settings.save(ignore_permissions=True)
    
    # Create sample categories
    categories = ["Beverages", "Snacks", "Main Course", "Desserts", "Special" ]
    for cat in categories:
        if not frappe.db.exists("Canteen Category", cat):
            category = frappe.new_doc("Canteen Category")
            category.category_name = cat
            category.is_active = 1
            category.insert(ignore_permissions=True)
    
    frappe.db.commit()
