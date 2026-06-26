app_name = "canteen_management"
app_title = "Canteen Management"
app_publisher = "Your Company"
app_description = "Canteen Management System - Employee Wallet, Menu, Reports for ERPNext POS"
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

# Document Events - hooks into ERPNext standard doctypes
doc_events = {
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
    "hourly": []
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
