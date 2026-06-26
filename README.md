# Canteen Management

> **Menu management, inventory tracking, and employee wallet system for ERPNext.**
> Sales and orders are handled through **ERPNext's standard POS Invoice** — no custom POS page or duplicate doctypes.

---

## Table of Contents

1. [Who This App Is For](#who-this-app-is-for)
2. [Installation](#installation)
3. [Architecture Overview](#architecture-overview)
4. [Setting Up ERPNext POS with Canteen](#setting-up-erpnext-pos-with-canteen)
5. [Employee Wallet Integration](#employee-wallet-integration)
6. [Stock Sync with Canteen Inventory](#stock-sync-with-canteen-inventory)
7. [Pre-Go-Live Checklist](#pre-go-live-checklist)
8. [Daily Operations](#daily-operations)
9. [Reports](#reports)
10. [API Endpoints](#api-endpoints)
11. [Scheduled Tasks](#scheduled-tasks)
12. [Troubleshooting](#troubleshooting)
13. [Development Guide](#development-guide)
14. [Known Gaps](#known-gaps)
15. [License](#license)

---

## Who This App Is For

| Role | What They Do |
|---|---|
| **Canteen Admin** | Full access — configuration, all transactions, all reports |
| **Canteen Manager** | Manage menu items, inventory, stock entries, reports |
| **Canteen Cashier** | Run ERPNext POS — create invoices, process wallet payments |
| **Canteen Staff** | View items and inventory only |
| **Canteen User** | View their own wallet balance and transactions only |
| **IT / Super User** | Install the app, assign roles, configure settings |

---

## Installation

```bash
bench get-app https://github.com/balaji-001-gif/canteen.git
bench --site your-site install-app canteen_management
bench --site your-site migrate
bench restart
```

### Verify installation

```bash
bench --site your-site console
```

```python
frappe.db.exists("Role", "Canteen Cashier")              # → True
frappe.db.exists("DocType", "Canteen Item")              # → True
frappe.db.exists("Canteen Category", "Beverages")        # → True (seeded by after_install)
frappe.db.exists("Canteen Table", "T01")                 # → True (seeded by after_install)
```

`after_install` runs automatically and creates five Canteen roles, five default categories (Beverages, Breakfast, Lunch, Snacks, Desserts), and ten default tables (T01–T10).

### Assign roles to users

| User Type | Role(s) to Assign |
|---|---|
| Cashier | **Canteen Cashier** |
| Manager | **Canteen Manager** |
| Employee with wallet | **Canteen User** |
| Admin | **Canteen Admin** |

---

## Architecture Overview

### What this app provides

| Component | Purpose |
|---|---|
| **Canteen Item** | Menu management — items, pricing, dietary flags. Synced to ERPNext Item via `setup_pos.py` |
| **Canteen Category** | Food categories (Beverages, Breakfast, Lunch, etc.) |
| **Canteen Settings** | Global config — tax, payment modes, wallet settings, alerts |
| **Canteen Payment Mode** | Payment mode options visible in the canteen context |
| **Canteen Inventory** | Custom stock tracking per item (current qty, min/max levels) |
| **Canteen Employee Wallet** | Prepaid wallet per employee (balance + credit limit) |
| **Canteen Wallet Transaction** | Audit trail for all wallet credits and debits |
| **Canteen Table** | Dine-in table management (Available/Occupied/Reserved) |

### What ERPNext provides

| Standard | Used For |
|---|---|
| **POS Invoice** | All sales transactions — replaces the old Canteen Order + Canteen Invoice |
| **POS Invoice Item** | Line items in each sale |
| **Item** | Standard ERPNext items synced from Canteen Items |
| **Stock Entry** | All stock movements — replaces old Canteen Stock Entry |
| **Supplier** | Supplier records — replaces old Canteen Supplier |
| **POS Profile** | POS configuration (warehouse, payment modes, accounts) |
| **Mode of Payment** | Payment methods (Cash, Card, UPI, Wallet) |

### Integration flow

```
  ERPNext POS Invoice (submit)
       │ on_submit (pos_invoice_hooks.py)
       ├──► Wallet Payment? ──► Deduct wallet balance
       │                       └──► Create Canteen Wallet Transaction (Debit)
       │
       └──► Deduct Canteen Inventory quantities
            └──► Low stock check → alert email

  POS Invoice (cancel)
       │ on_cancel (pos_invoice_hooks.py)
       ├──► Wallet Payment? ──► Refund wallet balance
       │                       └──► Create Canteen Wallet Transaction (Credit)
       │
       └──► Restore Canteen Inventory quantities
```

### Doctypes reference

| Table | Type | Stores |
|---|---|---|
| **Canteen Settings** | Single | Global config |
| **Canteen Category** | Master | Menu categories |
| **Canteen Item** | Master | Menu items, pricing, flags |
| **Canteen Inventory** | Balance | Running stock per item |
| **Canteen Employee Wallet** | Balance | Per-employee prepaid balance |
| **Canteen Wallet Transaction** | Ledger | Credit/debit audit trail |
| **Canteen Table** | Master | Dine-in tables |
| **Canteen Payment Mode** | Master | Enabled payment modes |

---

## Setting Up ERPNext POS with Canteen

### Automated setup

After installing the app and running `bench migrate`, sync your Canteen Items to ERPNext:

```bash
bench --site your-site execute canteen_management.setup_pos.run
```

This creates:
1. Modes of Payment: **Cash**, **Card**, **UPI**, **Wallet**
2. A **Canteen** Warehouse
3. A **Canteen** Item Group
4. Standard ERPNext **Items** with **Item Prices** from your Canteen Items
5. A **Canteen POS** POS Profile

### Manual setup

#### 1. Configure Canteen Settings

Go to **Canteen Management > Canteen Settings** and configure:
- Canteen Name, Company, Currency, GST Number
- Default Tax Rate
- Enable Wallet (turns on wallet payment integration)
- Enable Table Management
- Accepted Payment Modes
- Email addresses for low stock and daily report alerts

#### 2. Create Menu Items

1. Go to **Canteen Item > + Add New**
2. Set Item Code, Item Name, Category, Selling Price, Cost Price
3. Set dietary flags (vegetarian/vegan), barcode, preparation time
4. Save

Then run `bench --site your-site execute canteen_management.setup_pos.run` to sync to ERPNext Items.

#### 3. Set Up Inventory

For each item, create a **Canteen Inventory** record:
- Link to the Canteen Item
- Set Current Quantity, Minimum Quantity, Maximum Quantity
- This is the stock level the app tracks for low-stock alerts

#### 4. Create Modes of Payment

Go to **Accounting > Settings > Mode of Payment**:
- Cash, Card, UPI, Wallet

#### 5. Create a POS Profile

Go to **Point of Sale > Settings > POS Profile > New**:
- Name: `Canteen POS`
- Company: Your company
- Warehouse: `Canteen`
- Payments: Add Cash, Card, UPI, Wallet
- Set Income/Expense accounts

#### 6. Create an Opening Entry

Go to **Point of Sale > POS > New Opening Entry**:
- Select the Canteen POS profile
- Enter opening cash amount
- Submit

Then open **Point of Sale > POS** to start billing.

---

## Employee Wallet Integration

### Setup

1. Create **Canteen Employee Wallet** records for each employee
2. Top up wallets via the Canteen Employee Wallet form or `topup_wallet()` API

### In the POS

When creating a POS Invoice for an employee with a wallet:

1. Add items to cart as usual
2. Add **Wallet** as a payment mode in the Payments table
3. Set the **Canteen Employee** field on the invoice (appears under Customer info)
4. Submit

### On submit (automatic)

| Step | Action |
|---|---|
| 1 | Checks if any payment mode is "Wallet" |
| 2 | Looks up the employee's wallet via the `canteen_employee` field |
| 3 | Validates available balance (balance + credit limit) ≥ invoice total |
| 4 | Deducts the amount from the wallet |
| 5 | Creates a **Canteen Wallet Transaction** (Debit) |

### On cancel (automatic)

When a POS Invoice paid via Wallet is cancelled:
- Wallet balance is **refunded** automatically
- A **Canteen Wallet Transaction** (Credit) is created

### Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| "Wallet payment selected but no employee is linked" | Cashier didn't select employee | Set **Canteen Employee** on the invoice |
| "Employee does not have an active canteen wallet" | No wallet exists | Create wallet via **Canteen Employee Wallet** |
| "Insufficient wallet balance" | Not enough funds | Top up via `topup_wallet()` API |

---

## Stock Sync with Canteen Inventory

When a POS Invoice is submitted, the app automatically deducts from **Canteen Inventory** for each item sold. If no inventory record exists for an item, one is auto-created with zero starting quantity.

When a POS Invoice is cancelled, quantities are restored.

Low stock alerts are sent to the email configured in **Canteen Settings**.

---

## Pre-Go-Live Checklist

- [ ] **Configure Canteen Settings** — tax, payment modes, wallet, alerts
- [ ] **Create Canteen Categories** — edit defaults or add your own
- [ ] **Create Canteen Items** — all menu items with pricing
- [ ] **Create Canteen Inventory** — opening stock quantities
- [ ] **Sync to ERPNext** — run `setup_pos.run` to create Items and POS Profile
- [ ] **Set up Modes of Payment** — Cash, Card, UPI, Wallet
- [ ] **Create Employee Wallets** — for wallet-using employees
- [ ] **Assign roles** — Cashier, Manager, Admin to users
- [ ] **Create POS Opening Entry** — before first shift

### Loading opening stock

Set `current_quantity` on each **Canteen Inventory** record. Then create an ERPNext **Stock Entry** (type: Material Receipt) to load physical stock into the Canteen warehouse.

### Loading opening wallet balances

Either:
- Use `topup_wallet(wallet_name, amount, remarks)` per employee, or
- Set `balance` directly on each **Canteen Employee Wallet** record

---

## Daily Operations

### At the POS

1. Cashier opens **Point of Sale > POS**
2. Selects the **Canteen POS** profile
3. Rings up orders — items, quantities, customer, payment
4. For wallet payments: selects **Wallet** mode and sets **Canteen Employee**
5. Submits — wallet deducted + inventory updated automatically

### Stock management

Use ERPNext's **Stock Entry** for:
- **Material Receipt** — receiving new stock from suppliers
- **Material Issue** — waste, internal consumption
- **Stock Transfer** — moving between warehouses

Canteen Inventory is updated independently for low-stock alerts. For physical stock tracking, use ERPNext's **Stock Ledger** and **Bin** reports.

### Table management

Use the API (`get_tables()`, `update_table_status()`) to manage table status from a custom interface.

---

## Reports

All reports now query **ERPNext POS Invoice** instead of the old custom doctypes.

| Report | Source | What You See |
|---|---|---|
| **Daily Sales Summary** | POS Invoice + Payments child table | Day-wise sales, tax, discount, payment mode breakdown |
| **Canteen Sales Report** | POS Invoice | Item-level sales with employee, item count |
| **Canteen Profit & Loss** | POS Invoice Item + Item | Revenue, cost (valuation_rate), margin per item |
| **Canteen Employee Consumption** | POS Invoice + canteen_employee | Per-employee spending by payment method |
| **Canteen Inventory Report** | Canteen Inventory | Current stock levels, low/out of stock status |

---

## API Endpoints

| Endpoint | What It Does |
|---|---|
| `get_items` | Menu items with search/category filter |
| `get_item_detail` | Full item details including inventory |
| `get_categories` | Active categories |
| `get_stock_summary` | Inventory health (total, low, out-of-stock counts) |
| `get_low_stock_items` | Items below minimum stock |
| `get_all_inventory` | All inventory records |
| `get_stock_balance` | Single item stock |
| `get_wallet_balance` | Employee wallet balance |
| `topup_wallet` | Credit wallet (Admin/Manager) |
| `get_wallet_transactions` | Wallet transaction history |
| `create_wallet_for_employee` | Create a new wallet |
| `list_wallets` | All wallets with optional filters |
| `get_tables` | All tables with status |
| `get_available_tables` | Only available tables |
| `update_table_status` | Change table status |
| `get_settings` | Canteen configuration |
| `get_dashboard_stats` | Today's sales, orders, low stock |
| `get_sales_overview` | Daily sales breakdown for N days |
| `get_top_items` | Top-selling items |
| `get_invoice_print_html` | Printable receipt for a POS Invoice |

All endpoints use `@frappe.whitelist()` and standard Frappe session auth.

---

## Scheduled Tasks

| Task | Schedule | What It Does |
|---|---|---|
| `check_low_stock()` | Daily | Emails low-stock alert to configured email |
| `send_daily_sales_summary()` | Daily | Emails yesterday's sales summary |
| `check_shift_alerts()` | Hourly | Notifies cashiers of shifts open > 12 hours |

---

## Troubleshooting

| Error | Likely Cause | Fix |
|---|---|---|
| "Wallet payment selected but no employee is linked" | Cashier didn't set Canteen Employee field | Set the employee on the POS Invoice |
| "Insufficient wallet balance" | Employee balance + credit limit < invoice total | Top up wallet |
| "Insufficient stock for X" | Canteen Inventory quantity too low | Restock via ERPNext Stock Entry |
| "No inventory record found" | Canteen Inventory missing for item | Create one or let auto-create on first sale |

---

## Development Guide

### Project structure

```
canteen_management/
├── canteen_management/
│   ├── doctype/              # Custom doctypes (Item, Wallet, Settings, etc.)
│   ├── report/               # Script reports (querying POS Invoice)
│   ├── workspace/            # Workspace shortcuts
├── public/css|js/            # Static assets
├── templates/invoice.html    # Printable receipt template
├── fixtures/custom_field.json
├── patches/v1_0/             # Migration patches
├── hooks.py                  # App config, doc_events (POS Invoice hooks)
├── pos_invoice_hooks.py      # Wallet + stock sync hooks on POS Invoice
├── api.py                    # Whitelisted endpoints
├── setup.py                  # after_install (roles, defaults)
├── tasks.py                  # Scheduled jobs
├── utils.py                  # Helpers
└── README.md
```

### Key files

| File | Purpose |
|---|---|
| `hooks.py` | App config, doc_events for POS Invoice, scheduler |
| `pos_invoice_hooks.py` | Wallet deduction/refund + stock sync on POS Invoice submit/cancel |
| `api.py` | REST endpoints for items, inventory, wallets, tables, dashboard |
| `setup.py` | `after_install` — creates roles, categories, tables |
| `tasks.py` | Daily sales summary email, low stock alerts |
| `templates/invoice.html` | Printable invoice template using POS Invoice fields |

### Adding a new doctype

```bash
bench new-doctype DoctypeName --module "Canteen Management"
```

### Running migrations

```bash
bench --site your-site migrate
```

---

## Known Gaps

| Gap | Current State |
|---|---|
| No customer self-ordering | Every order entered by cashier in ERPNext POS |
| No self-service wallet top-up | Requires API/Desk access |
| No customer-facing notifications | Only manager alerts via email |
| Wallet payment mode name is hardcoded | `pos_invoice_hooks.py` checks for `"Wallet"` exactly — rename requires code change |
| "Delivery" order type not supported | ERPNext POS can handle this but no canteen-specific delivery tracking |

---

## License

MIT
