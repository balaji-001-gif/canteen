app_name = "canteen_management"
app_title = "Canteen Management"
app_publisher = "Your Company"
app_description = "Canteen Management System with integrated POS Billing"
app_email = "admin@yourcompany.com"
app_license = "MIT"
app_version = "1.0.0"

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
fixtures = [
    "custom_field.json",
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
        "on_submit": [
            "canteen_management.canteen_management.doctype.canteen_stock_entry.canteen_stock_entry.on_submit",
            "canteen_management.canteen_stock_entry_hooks.stock_entry_on_submit",
        ],
        "on_cancel": [
            "canteen_management.canteen_stock_entry_hooks.stock_entry_on_cancel",
        ],
    },
    "POS Invoice": {
        "on_submit": [
            "canteen_management.pos_invoice_hooks.wallet_payment_on_submit",
            "canteen_management.pos_invoice_hooks.stock_on_submit",
        ],
        "on_cancel": [
            "canteen_management.pos_invoice_hooks.wallet_payment_on_cancel",
            "canteen_management.pos_invoice_hooks.stock_on_cancel",
        ],
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

# Roles
has_permission = {
    "Canteen Order": "canteen_management.canteen_management.doctype.canteen_order.canteen_order.has_permission",
    "Canteen Invoice": "canteen_management.canteen_management.doctype.canteen_invoice.canteen_invoice.has_permission",
}

# After install
after_install = "canteen_management.setup.after_install"
after_migrate = "canteen_management.setup.after_migrate"

# Jinja
jinja = {
    "methods": [
        "canteen_management.utils.get_canteen_settings",
        "canteen_management.utils.format_currency",
    ]
}

# Override Whitelisted Methods
override_whitelisted_methods = {}

# Website Route
website_route_rules = [
    {"from_route": "/canteen-pos", "to_route": "canteen_pos"},
]
