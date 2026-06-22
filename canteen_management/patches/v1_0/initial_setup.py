import frappe


def execute():
    """Initial setup patch - create roles and default settings"""
    # Create default roles
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

    frappe.db.commit()
