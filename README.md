# Canteen Management System for ERPNext v15+

A complete **Canteen Management** Frappe/ERPNext application with POS billing, inventory tracking, employee wallets, shift management, and detailed reporting.

---

## 📋 Features

- 🍽️ **POS Billing** — Fast and intuitive Point-of-Sale interface
- 📦 **Inventory Management** — Real-time stock tracking with low-stock alerts
- 👛 **Employee Wallet** — Pre-loaded digital wallets for employees
- ⏱️ **Shift Management** — Cashier shift opening and closing with summaries
- 🪑 **Table Management** — Dine-in table status tracking
- 📊 **Reports** — Sales, Inventory, Employee Consumption, P&L
- 🔔 **Notifications** — Low stock and daily sales email alerts
- 🔐 **Role-Based Access** — Granular permissions for Admin, Manager, Cashier, Staff, User

---

## 🏗️ Application Structure

```
canteen_management/
├── canteen_management/
│   ├── doctype/
│   │   ├── canteen_settings/          # Global app configuration
│   │   ├── canteen_category/          # Food categories
│   │   ├── canteen_item/              # Menu items
│   │   ├── canteen_order/             # Customer orders
│   │   ├── canteen_order_item/        # Order line items (child)
│   │   ├── canteen_invoice/           # Invoices
│   │   ├── canteen_invoice_item/      # Invoice line items (child)
│   │   ├── canteen_inventory/         # Stock levels
│   │   ├── canteen_stock_entry/       # Stock purchases & adjustments
│   │   ├── canteen_stock_entry_item/  # Stock entry items (child)
│   │   ├── canteen_employee_wallet/   # Employee pre-paid wallets
│   │   ├── canteen_wallet_transaction/# Wallet credit/debit records
│   │   ├── canteen_shift/             # Cashier shift records
│   │   ├── canteen_table/             # Dine-in tables
│   │   ├── canteen_supplier/          # Inventory suppliers
│   │   └── canteen_payment_mode/      # Payment mode child table
│   ├── page/
│   │   └── canteen_pos/               # POS Billing Page
│   ├── report/
│   │   ├── canteen_sales_report/
│   │   ├── canteen_inventory_report/
│   │   ├── canteen_employee_consumption/
│   │   ├── daily_sales_summary/
│   │   └── canteen_profit_loss/
│   └── workspace/
│       └── canteen_management/        # Workspace shortcuts
├── config/
│   ├── desktop.py
│   └── docs.py
├── templates/
│   └── invoice.html                   # Printable invoice template
├── public/
│   ├── css/canteen.css
│   └── js/canteen.js
├── hooks.py
├── setup.py                           # App install hooks
├── tasks.py                           # Scheduled tasks
├── utils.py                           # Shared utilities
└── patches/
    └── v1_0/initial_setup.py
```

---

## 🚀 Installation

### Prerequisites
- ERPNext v15+ installed
- Frappe Framework v15+

### Steps

```bash
# 1. Get the app
bench get-app https://github.com/balaji-001-gif/canteen.git

# 2. Install on your site
bench --site your-site-name install-app canteen_management

# 3. Run migrations
bench --site your-site-name migrate

# 4. Restart bench
bench restart
```

---

## ⚙️ Configuration

1. Go to **Canteen Management > Canteen Settings**
2. Set your **Canteen Name** and **Company**
3. Configure **Tax Rate**, **Payment Modes**, **Email Alerts**
4. Enable **Employee Wallet** and **Table Management** as needed

---

## 👥 Roles

| Role             | Permissions                              |
|------------------|------------------------------------------|
| Canteen Admin    | Full access to all features              |
| Canteen Manager  | Manage orders, reports, inventory        |
| Canteen Cashier  | Create orders, manage shifts             |
| Canteen Staff    | View items and inventory                 |
| Canteen User     | View own orders and wallet balance       |

---

## 📊 Reports

| Report                      | Description                              |
|-----------------------------|------------------------------------------|
| Canteen Sales Report        | Order-level sales with filters           |
| Canteen Inventory Report    | Current stock levels and status          |
| Canteen Employee Consumption| Per-employee order summary               |
| Daily Sales Summary         | Day-wise sales breakdown by payment mode |
| Canteen Profit & Loss       | Item-wise revenue, cost, and margin      |

---

## 📄 License

MIT License — Free to use and modify.

---

## 🙋 Support

For issues or feature requests, raise an issue on [GitHub](https://github.com/balaji-001-gif/canteen/issues).
