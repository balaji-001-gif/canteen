import frappe


def after_install():
    """Setup default data after app install"""
    create_roles()
    create_default_categories()
    create_default_tables()


def after_migrate():
    """Run after every bench migrate"""
    pass


def create_roles():
    """Create default canteen roles"""
    roles = [
        "Canteen Admin",
        "Canteen Manager",
        "Canteen Cashier",
        "Canteen Staff",
        "Canteen User"
    ]
    for role in roles:
        if not frappe.db.exists("Role", role):
            doc = frappe.new_doc("Role")
            doc.role_name = role
            doc.insert(ignore_permissions=True)


def create_default_categories():
    """Create default food categories"""
    categories = [
        {"category_name": "Beverages", "sort_order": 1},
        {"category_name": "Breakfast", "sort_order": 2},
        {"category_name": "Lunch", "sort_order": 3},
        {"category_name": "Snacks", "sort_order": 4},
        {"category_name": "Desserts", "sort_order": 5},
    ]
    for cat in categories:
        if not frappe.db.exists("Canteen Category", cat["category_name"]):
            doc = frappe.new_doc("Canteen Category")
            doc.category_name = cat["category_name"]
            doc.sort_order = cat["sort_order"]
            doc.is_active = 1
            doc.insert(ignore_permissions=True)


def create_default_tables():
    """Create default canteen tables T1 to T10"""
    for i in range(1, 11):
        table_no = f"T{i:02d}"
        if not frappe.db.exists("Canteen Table", table_no):
            doc = frappe.new_doc("Canteen Table")
            doc.table_number = table_no
            doc.table_name = f"Table {i}"
            doc.capacity = 4
            doc.status = "Available"
            doc.is_active = 1
            doc.insert(ignore_permissions=True)
