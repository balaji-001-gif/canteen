# Canteen Management System

A comprehensive **Canteen Management System** with integrated **POS Billing** for **ERPNext v15+**. This Frappe app enables you to manage canteen/cafeteria operations — from menu items and inventory to order processing, billing, shift management, and employee wallet payments.

---

## Features

### Menu & Item Management
- **Canteen Items** — Full item catalog with item codes, names, categories, pricing (selling/cost), tax rates, dietary labels (vegetarian/vegan), allergen info, barcode support, and preparation times
- **Canteen Categories** — Hierarchical categories with parent-child relationships, images, sorting, and active/inactive toggling

### Order Processing
- **Canteen Orders** — POS-style order creation with multiple order types:
  - Dine In / Take Away / Delivery / Bulk Order
- Status workflow: Draft → Pending → Preparing → Ready → Served → Cancelled → Completed
- Table management support (via **Canteen Table** DocType)
- Shift tracking (via **Canteen Shift** DocType)

### Billing & Invoicing
- **Canteen Invoices** — Auto-generated invoices upon order submission
- Payment modes: Cash, Card, UPI, Wallet, Credit
- Tax calculations with configurable rates
- Receipt printing with customizable header/footer
- Invoice HTML template for printing

### Inventory Management
- **Canteen Inventory** — Per-item stock tracking with min/max levels
- **Canteen Stock Entry** — Inward/Outward/Adjustment/Wastage stock movements
- Low stock alerts (realtime + email notifications)
- Automatic stock updates on order placement/cancellation
- Stock level dashboard

### Employee Wallet System
- **Canteen Employee Wallet** — Per-employee wallet balances with credit limits
- **Canteen Wallet Transaction** — Credit/Debit transaction history
- Wallet payments for orders
- Top-up functionality

### Settings & Configuration
- **Canteen Settings** — Single DocType for global configuration:
  - Canteen name, company, currency, GST number
  - Default tax rate, payment modes
  - Table management toggle, auto-close shift
  - Low stock threshold and notification emails

### Reporting & Scheduling
- Daily sales summary emails
- Weekly sales reports
- Shift auto-closure alerts
- Low stock email notifications

### Roles & Permissions
- **Canteen Admin** — Full access
- **Canteen Manager** — Create/Read/Write access
- **Canteen Cashier** — POS operations
- **Canteen Staff** — Read access
- **Canteen User** — Read own orders

---

## DocTypes Reference

| DocType | Type | Description |
|---------|------|-------------|
| Canteen Item | Master | Menu items with pricing, dietary info, barcode |
| Canteen Category | Master | Item categories (hierarchical) |
| Canteen Order | Transaction (Submittable) | POS orders with items, payment, status workflow |
| Canteen Order Item | Child Table | Order line items |
| Canteen Invoice | Transaction (Submittable) | Auto-generated invoices on order submission |
| Canteen Invoice Item | Child Table | Invoice line items |
| Canteen Inventory | Master | Per-item stock tracking |
| Canteen Stock Entry | Transaction (Submittable) | Stock movements (Inward/Outward/Adjustment/Wastage) |
| Canteen Stock Entry Item | Child Table | Stock entry line items |
| Canteen Shift | Master | Cashier shift management |
| Canteen Table | Master | Table management for dine-in |
| Canteen Employee Wallet | Master | Employee wallet balances |
| Canteen Wallet Transaction | Transaction | Wallet credit/debit history |
| Canteen Settings | Single | Global configuration |
| Canteen Payment Mode | Child Table | Payment modes configuration |

---

## Installation

### Prerequisites
- ERPNext v15+ (Frappe v15+)
- Bench CLI

### Steps

1. **Download the app**
   ```bash
   cd /path/to/bench
   bench get-app https://github.com/balaji-001-gif/canteen
   ```

2. **Install on your site**
   ```bash
   bench --site yoursite.com install-app canteen_management
   ```

3. **Build assets**
   ```bash
   bench build
   ```

4. **Migrate**
   ```bash
   bench --site yoursite.com migrate
   ```

---

## Usage

1. **Setup**
   - Go to **Canteen Settings** → Configure your canteen name, company, currency, tax rate, payment modes
   - Add menu items under **Canteen Item**
   - Organize items into **Canteen Category**

2. **Inventory Setup**
   - Stock entries under **Canteen Stock Entry** to add initial inventory
   - Monitor stock levels via the **Canteen Inventory** list

3. **Operations**
   - Create shifts under **Canteen Shift** for cashiers
   - Set up tables under **Canteen Table** (if dine-in enabled)
   - Process orders via the POS interface or directly creating **Canteen Order**

4. **Employee Wallets**
   - Create wallets for employees under **Canteen Employee Wallet**
   - Top-up wallets using the wallet view
   - Employees can pay using wallet balance

---

## Architecture

The app follows the standard Frappe nested app layout:
```
canteen_management/
├── __init__.py          # App version
├── canteen_management/  # Main package
│   ├── __init__.py
│   ├── hooks.py         # App hooks, events, scheduler
│   ├── modules.txt      # Module definition
│   ├── patches.txt      # Patch list
│   ├── patches/
│   │   └── v1_0/        # Version patches
│   ├── doctype/         # All DocTypes
│   ├── templates/
│   │   └── invoice.html # Invoice print template
│   ├── public/
│   │   ├── css/
│   │   │   └── canteen.css
│   │   └── js/
│   │       └── canteen.js
│   ├── setup.py         # After install/migrate setup
│   ├── tasks.py         # Scheduled tasks
│   └── utils.py         # Utility functions
├── setup.py             # Package setup
├── requirements.txt
├── MANIFEST.in
└── .gitignore
```

---

## License

MIT

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
