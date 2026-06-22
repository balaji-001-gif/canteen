app_name = "canteen_management"
app_title = "Canteen Management"
app_publisher = "Your Company"
app_description = "Canteen Management System with integrated POS Billing"
app_email = "admin@yourcompany.com"
app_license = "MIT"

# NOTE: app_version is not a recognized hooks.py key — Frappe reads the
# version from `__version__` in canteen_management/__init__.py instead.
# Set it there, not here. (Removed from this file.)

# Includes in <head>
app_include_css = [
    "/assets/canteen_management/css/canteen.css"
]
app_include_js = [
    "/assets/canteen_management/js/canteen.js"
]

# Website include
web_include_css = []
web_include_js = []

# Fixtures
# - "Custom Field" exports all Custom Field records — standard practice for
#   field-level customizations you want versioned with the app.
# - "Workspace" is deliberately NOT included here. The workspace JSON built
#   earlier has is_standard=1, which means Frappe syncs it automatically on
#   migrate from:
#     canteen_management/canteen_management/workspace/canteen_management/canteen_management.json
#   Fixture-exporting "Workspace" on top of that gives you two competing
#   sources of truth for the same doc. If you'd rather manage the workspace
#   via fixtures instead, set is_standard=0 on the doc and add "Workspace"
#   back to this list — don't do both.
fixtures = [
    "Custom Field",
    {
        "doctype": "Role",
        "filters": [["name", "in", [
            "Canteen Admin",
            "Canteen Cashier",
            "Canteen Manager",
            "Canteen Staff",
            "Canteen User"
        ]]]
    }
]

# Document Events
# NOTE: these dotted paths assume the module name is "canteen_management"
# (i.e. module_name == app_name). If your module folder is named anything
# else, every path below resolves to nothing and the hook silently never
# fires — no error, it just won't run. Verify against
# canteen_management/modules.txt before relying on this.
doc_events = {
    "Canteen Order": {
        "on_submit": "canteen_management.canteen_management.doctype.canteen_order.canteen_order.on_submit",
        "on_cancel": "canteen_management.canteen_management.doctype.canteen_order.canteen_order.on_cancel",
    },
    "Canteen Invoice": {
        "on_submit": "canteen_management.canteen_management.doctype.canteen_invoice.canteen_invoice.on_submit",
        "on_cancel": "canteen_management.canteen_management.doctype.canteen_invoice.canteen_invoice.on_cancel",
    },
    "Canteen Stock Entry": {
        "on_submit": "canteen_management.canteen_management.doctype.canteen_stock_entry.canteen_stock_entry.on_submit",
    }
}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "canteen_management.canteen_management.doctype.canteen_inventory.canteen_inventory.check_low_stock",
        "canteen_management.tasks.send_daily_sales_summary",
    ],
    "weekly": [
        "canteen_management.tasks.weekly_report",
    ],
    "hourly": [
        "canteen_management.tasks.check_shift_alerts",
    ]
}

# Permissions
has_permission = {
    "Canteen Order": "canteen_management.canteen_management.doctype.canteen_order.canteen_order.has_permission",
    "Canteen Invoice": "canteen_management.canteen_management.doctype.canteen_invoice.canteen_invoice.has_permission",
}

# After install / migrate
after_install = "canteen_management.setup.after_install"
after_migrate = "canteen_management.setup.after_migrate"

# Jinja
jinja = {
    "methods": [
        "canteen_management.utils.get_canteen_settings",
        "canteen_management.utils.format_currency",
    ]
}

# Website Route Rules
website_route_rules = [
    {"from_route": "/canteen-pos", "to_route": "canteen_pos"},
]
