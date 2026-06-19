import frappe
from frappe.utils import now


def after_install():
    """Run after app installation"""
    create_default_roles()
    create_default_settings()
    create_canteen_workspace()
    frappe.db.commit()


def after_migrate():
    """Run after app migration"""
    create_default_roles()
    create_canteen_workspace()
    frappe.db.commit()


def create_default_roles():
    """Create default roles if they don't exist"""
    roles = ["Canteen Admin", "Canteen Manager", "Canteen Cashier", "Canteen Staff", "Canteen User"]
    for role_name in roles:
        if not frappe.db.exists("Role", role_name):
            role = frappe.new_doc("Role")
            role.role_name = role_name
            role.desk_access = 1
            role.insert(ignore_permissions=True)


def create_default_settings():
    """Create default canteen settings if they don't exist"""
    if not frappe.db.exists("Canteen Settings", "Canteen Settings"):
        settings = frappe.new_doc("Canteen Settings")
        settings.canteen_name = "Default Canteen"
        settings.company = frappe.db.get_single_value("Global Defaults", "default_company") or ""
        settings.save(ignore_permissions=True)


def create_canteen_workspace():
    """Create Canteen Management workspace if not exists"""
    if not frappe.db.exists("Workspace", "Canteen Management"):
        workspace = frappe.new_doc("Workspace")
        workspace.title = "Canteen Management"
        workspace.module = "Canteen Management"
        workspace.icon = "utensils"
        workspace.is_standard = 1
        workspace.public = 1
        workspace.append("links", {
            "type": "DocType",
            "label": "Canteen Items",
            "link_to": "Canteen Item",
            "group": "Items"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Canteen Categories",
            "link_to": "Canteen Category",
            "group": "Items"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Canteen Orders",
            "link_to": "Canteen Order",
            "group": "Orders"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Canteen Invoices",
            "link_to": "Canteen Invoice",
            "group": "Orders"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Canteen Inventory",
            "link_to": "Canteen Inventory",
            "group": "Inventory"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Stock Entries",
            "link_to": "Canteen Stock Entry",
            "group": "Inventory"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Shifts",
            "link_to": "Canteen Shift",
            "group": "Operations"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Tables",
            "link_to": "Canteen Table",
            "group": "Operations"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Employee Wallets",
            "link_to": "Canteen Employee Wallet",
            "group": "Finance"
        })
        workspace.append("links", {
            "type": "DocType",
            "label": "Canteen Settings",
            "link_to": "Canteen Settings",
            "group": "Settings"
        })
        workspace.insert(ignore_permissions=True)
