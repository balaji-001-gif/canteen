# Canteen Management

> **POS billing, inventory, and employee wallet tracking for ERPNext.**
> This app provides the backend data and reports (items, inventory, wallets, shifts) that feed into **ERPNext's built-in POS system** — no custom POS page needed.

---

## Table of Contents

1. [Who This App Is For](#who-this-app-is-for)
2. [Start Here: Installation for IT Team](#start-here-installation-for-it-team)
3. [Configure ERPNext Standard POS (Recommended)](#configure-erpnext-standard-pos-recommended)
4. [Pre-Go-Live Checklist (Canteen Manager)](#pre-go-live-checklist-canteen-manager)
5. [Go-Live Day: Opening Stock & Wallets](#go-live-day-opening-stock--wallets)
6. [Transaction: Take an Order (POS)](#transaction-take-an-order-pos)
7. [Transaction: Receive Stock](#transaction-receive-stock)
8. [Transaction: Cashier Shift](#transaction-cashier-shift)
9. [Reports & Monitoring](#reports--monitoring)
10. [Notifications & Alerts](#notifications--alerts)
11. [Troubleshooting Guide](#troubleshooting-guide)
12. [Role & Permission Matrix](#role--permission-matrix)
13. [Technical Architecture (For IT Reference)](#technical-architecture-for-it-reference)
14. [Development Guide (For IT)](#development-guide-for-it)
15. [Known Gaps](#known-gaps)

---

## Who This App Is For

| Role | What They Do in This App |
|---|---|
| **Canteen Admin** | Full access — configuration, all transactions, all reports |
| **Canteen Manager** | Manage orders, inventory, stock entries, reports |
| **Canteen Cashier** | Run the POS — create orders, open/close their own shift |
| **Canteen Staff** | View items and inventory only |
| **Canteen User** | View their own orders and wallet balance only |
| **IT / Super User** | Install the app, assign roles, configure settings, troubleshoot |

> There is no customer-facing role. Every transaction in this app is entered by a Cashier on behalf of a walk-in customer or wallet-linked employee — see [Known Gaps](#known-gaps).

---

## Start Here: Installation for IT Team

### Step 1 — Install the app on your bench

```bash
bench get-app https://github.com/balaji-001-gif/canteen.git
bench --site your-site install-app canteen_management
bench --site your-site migrate
bench restart
```

### Step 2 — Verify installation

```bash
bench --site your-site console
```

```python
frappe.db.exists("Role", "Canteen Cashier")              # → True
frappe.db.exists("DocType", "Canteen Order")              # → True
frappe.db.exists("Canteen Category", "Beverages")          # → True (created by after_install)
frappe.db.exists("Canteen Table", "T01")                   # → True (created by after_install)
```

`after_install` runs automatically on install and creates the five Canteen roles, five default categories (Beverages, Breakfast, Lunch, Snacks, Desserts), and ten default tables (T01–T10).

### Step 3 — Assign roles to users

| Go to | Do this |
|---|---|
| **Frappe Desk > User > [Cashier's User]** | Add role **Canteen Cashier**, save |
| **Frappe Desk > User > [Manager's User]** | Add role **Canteen Manager**, save |
| **Frappe Desk > User > [Employee with wallet]** | Add role **Canteen User**, save |

> Cashiers need normal Desk access. They'll use ERPNext's built-in POS interface at **Point of Sale > POS**, not a custom page.

---

## Configure ERPNext Standard POS (Recommended)

This app works best when paired with **ERPNext's built-in POS system** — no custom POS page needed. Run the setup script to automatically create standard Items, Payment Modes, and a POS Profile from your existing Canteen Items.

### Automated setup

After installing the app and running `bench migrate`, run:

```bash
bench --site your-site execute canteen_management.setup_pos.run
```

This will:
1. Create Modes of Payment: **Cash**, **Card**, **UPI**
2. Create a **Canteen** Warehouse
3. Create a **Canteen** Item Group
4. Sync all active **Canteen Items** → standard ERPNext **Items** with **Item Prices**
5. Create a **Canteen POS** POS Profile with all payment modes

### Manual configuration (if you prefer to do it step-by-step)

#### 1. Create Modes of Payment

Go to **Accounting > Settings > Mode of Payment** and create:

| Mode of Payment | Type | Default Account |
|---|---|---|
| Cash | Cash | Cash - [Company Abbr] |
| Card | Bank | (leave blank, set later) |
| UPI | Bank | (leave blank, set later) |

#### 2. Create a Warehouse

Go to **Stock > Settings > Warehouse** and create:
- Warehouse Name: `Canteen`
- Company: your company
- Parent Warehouse: `Stores`

#### 3. Create Items from Canteen Items

For each item in **Canteen Item**, create a matching **Item** (`Stock > Items > Item`):
- Item Code, Item Name → from Canteen Item
- Item Group → `Canteen` (create it if it doesn't exist)
- Stock UOM → Nos (or as appropriate)
- Enable `Maintain Stock`

Then set Item Price for each item under **Selling > Standard Selling**.

#### 4. Create a POS Profile

Go to **Point of Sale > Settings > POS Profile > New**:

| Field | Value |
|---|---|
| Name | Canteen POS |
| Company | Your company |
| Warehouse | Canteen |
| Currency | INR |
| **Payments** | Add Cash, Card, UPI |

Set the Income Account and Expense Account under the **Accounting** section.

### Using the POS

1. **Create an Opening Entry**: `Point of Sale > POS > New Opening Entry`
2. Select **Canteen POS** profile, enter opening cash amount, submit
3. Open the POS: `Point of Sale > POS`
4. Start ringing up orders

### Employee Wallet Payments in Standard POS

The app integrates **Employee Wallet** as a payment mode in ERPNext's standard POS. When setting up (via the script or manually), a **Wallet** Mode of Payment is created.

#### How it works

1. Create **Canteen Employee Wallet** records for each employee who'll pay via wallet
2. Top up wallets via `topup_wallet()` or the Canteen Employee Wallet form
3. In the POS, the cashier:
   - Adds items to the cart as usual
   - Adds **Wallet** as a payment mode in the Payments table
   - Sets the **Canteen Employee** field (appears under Customer on the POS Invoice form)
   - Submits the invoice

#### What happens on submit

| Step | Action |
|---|---|
| 1 | Checks if any payment mode is "Wallet" |
| 2 | Looks up the employee's wallet via the `canteen_employee` field |
| 3 | Validates available balance (balance + credit limit) >= invoice total |
| 4 | Deducts the amount from the wallet |
| 5 | Creates a **Canteen Wallet Transaction** (Debit) for audit trail |

#### What happens on cancel

When a POS Invoice paid via Wallet is cancelled:
- The wallet balance is **refunded** automatically
- A **Canteen Wallet Transaction** (Credit) is created

#### Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| "Wallet payment selected but no employee is linked" | Cashier didn't select an employee | Set the **Canteen Employee** field on the invoice |
| "Employee X does not have an active canteen wallet" | No wallet exists for that employee | Create a wallet via **Canteen Employee Wallet** |
| "Insufficient wallet balance" | Employee doesn't have enough funds | Top up the wallet via `topup_wallet()` |

> The custom fields `canteen_employee` and `wallet_balance` on POS Invoice are installed automatically via `bench migrate` (from `fixtures/custom_field.json`). They only show when "Wallet" payment mode is selected.

---

## Pre-Go-Live Checklist (Canteen Manager)

Complete these steps BEFORE the first order is taken.

### □ 1. Configure Canteen Settings

Go to **Canteen Management > Canteen Settings** (single doctype) and set:

| Field | Purpose |
|---|---|
| Canteen Name, Company, Currency, GST Number | Identity used on invoices |
| Tax Rate | Default tax % applied to items |
| Enable Wallet | Turns on employee wallet payment mode |
| Enable Table Management | Turns on dine-in table tracking |
| Accepted Payment Modes | Which of Cash/Card/UPI/Wallet/Credit show in POS |
| Enable Credit Sales, Max Credit Limit | Controls "Credit" payment mode |
| Low Stock Email, Daily Report Email | Where alerts get sent — see [Notifications](#notifications--alerts) |
| Notify on Large Order | Threshold flag (field exists; confirm wiring before relying on it — see [Known Gaps](#known-gaps)) |

### □ 2. Set up Categories

Five defaults are seeded on install. Go to **Canteen Category** to add/reorder via `sort_order`, or mark inactive ones you don't need.

### □ 3. Create Menu Items

For each item, go to **Canteen Item > + Add New** and set:
- Item Code, Item Name, Category
- Selling Price, Cost Price, Tax Rate
- Is Vegetarian / Is Vegan, Allergen Info, Preparation Time
- Barcode (used for POS search/scan-by-code)

> Saving an item does **not** automatically create its `Canteen Inventory` record — confirm this manually before go-live, because `Canteen Stock Entry` will hard-throw ("No inventory record found...") if the item has no inventory row yet.

Then run `bench --site your-site execute canteen_management.setup_pos.run` to sync them to standard ERPNext Items for use in the POS.

### □ 4. Set Minimum Stock Levels

On each **Canteen Inventory** record (or the item's `min_stock_level`), set the threshold that triggers low-stock alerts and blocks orders that would oversell.

### □ 5. Configure Payment Modes

Go to **Canteen Payment Mode** and create rows for each mode you accept (Cash, Card, UPI, Wallet, Credit), marking one `is_default`.

Also configure the corresponding **Mode of Payment** in ERPNext (see [Configure ERPNext Standard POS](#configure-erpnext-standard-pos-recommended)).

### □ 6. Set up Tables (if dine-in)

Ten tables (T01–T10, capacity 4) are seeded on install. Edit capacity/location per table, or add more under **Canteen Table**.

### □ 7. Create Employee Wallets (if using Wallet payments)

For each employee who'll pay by wallet:
1. Go to **Canteen Employee Wallet > + Add New**, or call `create_wallet_for_employee(employee)`
2. Top up the initial balance via `topup_wallet()` — there is no self-service top-up; only an Admin/Manager/Cashier with API access can credit a wallet

---

## Go-Live Day: Opening Stock & Wallets

### Why this is needed

`Canteen Inventory.current_quantity` starts at zero (or whatever you set manually). There is no backfill/migration patch in this app — `patches/v1_0/initial_setup.py` exists but only handles app-level setup, not stock import.

### Loading opening stock

For each item, create a **Canteen Stock Entry** with **Stock Type = Opening Stock**:

1. Go to **Canteen Stock Entry > + Add New**
2. Stock Type: `Opening Stock`
3. Add item rows with quantity and rate
4. Submit

On submit, `update_inventory()` adds the quantity to `Canteen Inventory.current_quantity` for each item. If an item has no inventory record yet, submission throws — create the inventory record first.

### Loading opening wallet balances

There's no bulk wallet-import tool. Either:
- Use `topup_wallet(wallet_name, amount, remarks)` per employee, or
- Set `balance` directly on each **Canteen Employee Wallet** record (bypasses the `Canteen Wallet Transaction` audit trail — only do this for true opening balances, with a note in `remarks`)

---

## Transaction: Take an Order (POS)

### Where

**Frappe Desk > Canteen Management > Canteen POS** (or the `/canteen-pos` route, which maps to the same Desk page — it is not a public website page).

### Step-by-step: Cashier

1. Open the POS page. `pos_data()` loads settings, categories, items, tables (if enabled), the cashier's active shift, payment modes, and dashboard stats in one call.
2. Search or browse items (`get_items`), add to cart.
3. Select **Order Type**: Dine In / Take Away / Delivery / Bulk Order.
   - If Dine In and table management is on, assign a table — its status flips to **Occupied** on order submit.
4. Select **Payment Mode**: Cash / Card / UPI / Wallet / Credit (only those marked active in Canteen Payment Mode).
   - If Wallet: enter the Employee. The order will be rejected at submit if the wallet balance is insufficient.
5. Enter Paid Amount (cash) — change is calculated automatically; submission throws if paid amount is less than the total.
6. Submit.

### What happens on submit (`Canteen Order.on_submit`)

```
Order submitted
  → validate_items(): re-checks stock availability per line, throws if insufficient
  → update_inventory(): deducts current_quantity per item
       → if resulting quantity <= minimum_quantity: low-stock alert email sent immediately
  → update_wallet_if_applicable(): if payment_mode == Wallet
       → debits employee wallet balance (throws if insufficient)
       → creates a Canteen Wallet Transaction (Debit) for audit
  → create_invoice(): generates and submits a Canteen Invoice, copying all line items
  → order.status set to "Completed"
```

> **Status flow is not staged in practice.** The `status` field schema allows `Pending → Preparing → Ready → Served → Completed`, but `on_submit` sets status straight to `Completed` the moment the order is submitted — there's no kitchen-display step that holds an order at "Preparing." If you need that workflow, the order must stay in **Draft** and someone has to call `update_order_status()` manually before submission, which isn't how `create_order()` in the API is wired today.

### Cancelling an order

`cancel_order()` only works on submitted (`docstatus == 1`) orders. Cancelling restores inventory and cancels the linked invoice — it does **not** automatically reverse a wallet debit; check the wallet transaction manually if the original payment was Wallet.

---

## Transaction: Receive Stock

### Who does what

| Team | Action |
|---|---|
| **Canteen Manager** | Creates **Canteen Stock Entry** for Purchase, Return, Adjustment, Opening Stock, or Waste |
| **Canteen Supplier** record | Optional link on Purchase-type entries for traceability |

### Step-by-step

1. Go to **Canteen Stock Entry > + Add New**
2. Choose **Stock Type**:

   | Stock Type | Effect on inventory |
   |---|---|
   | Purchase | `current_quantity += qty` |
   | Opening Stock | `current_quantity += qty` |
   | Return | `current_quantity += qty` |
   | Adjustment | `current_quantity -= qty` (throws if it would go negative) |
   | Waste | `current_quantity -= qty` (throws if it would go negative) |

3. Add item rows with quantity and rate
4. Submit

On submit, `update_inventory()` applies the change per the table above and stamps `last_stock_entry` on the inventory record. Cancelling the entry reverses the same logic (`reverse_inventory()`).

---

## Transaction: Cashier Shift

### Step-by-step

1. **Open shift:** `open_shift(opening_amount, cashier)` — a cashier can only have **one Active shift at a time**; opening a second throws.
2. Take orders as normal during the shift — each submitted order auto-links to the cashier's active shift via `set_active_shift()`.
3. **Close shift:** `close_shift(shift_name, closing_amount)`. On save, `calculate_totals()` sums every submitted order on that shift and splits totals into `cash_sales`, `card_sales`, `upi_sales`, `wallet_sales`, `credit_sales`.
4. An hourly scheduled job (`check_shift_alerts`) flags any shift that's been **Active for over 12 hours** via a realtime event to that cashier — there's no email/SMS for this, only an in-session push.

---

## Reports & Monitoring

### Built-in reports via the Desk

| Report | What you see |
|---|---|
| **Canteen Sales Report** | Order-level sales with filters |
| **Canteen Inventory Report** | Current stock levels and status |
| **Canteen Employee Consumption** | Per-employee order summary |
| **Daily Sales Summary** | Day-wise sales breakdown by payment mode |
| **Canteen Profit & Loss** | Item-wise revenue, cost, and margin |

### Dashboard stats (POS page)

`get_dashboard_stats()`, `get_sales_overview(days)`, and `get_top_items(days, limit)` power the at-a-glance numbers on the POS screen and dashboard — these are read-only summaries, not exportable reports.

### Stock health

`get_stock_summary()` returns total items, low-stock count, out-of-stock count, and healthy-stock count for a quick inventory health check.

---

## Notifications & Alerts

This app sends a **small, fixed set of emails** — there is no customer-facing notification of any kind (no order confirmation, no "ready for pickup," no receipt emailed to the customer).

| Trigger | Alert | Recipient | Mechanism |
|---|---|---|---|
| Item hits minimum quantity during an order | "Low Stock Alert - {item}" email | `Canteen Settings.low_stock_email` | Sent inline from `Canteen Order.on_submit` |
| Daily scheduled job | Same low-stock check across all inventory | `Canteen Settings.low_stock_email` | `check_low_stock()`, runs daily |
| Daily scheduled job | "Canteen Sales Summary - {date}" email with totals | `Canteen Settings.daily_report_email` | `send_daily_sales_summary()`, runs daily |
| Shift open > 12 hours | Realtime browser event to that cashier | The cashier's own session | `check_shift_alerts()`, runs hourly — **no email, only a live push while logged in** |
| Inventory record saved below minimum | Realtime browser event `canteen_low_stock` | Whoever's listening on that page | `Canteen Inventory.after_save` |

> `Canteen Settings.notify_on_large_order` exists as a field but no code path was found that reads it — treat it as unwired until confirmed otherwise.

---

## Troubleshooting Guide

| Error message | Likely cause | What to do |
|---|---|---|
| `"No inventory record found for item X"` | Stock Entry submitted for an item with no `Canteen Inventory` row | Create the inventory record for that item first |
| `"Insufficient stock for X"` | Order line quantity exceeds `current_quantity` | Check inventory, restock, or reduce order quantity |
| `"Insufficient wallet balance"` | Wallet payment exceeds employee's `balance` | Top up the wallet via `topup_wallet()` before retrying |
| `"Paid amount is less than total amount"` | Cash tendered < order total | Re-enter correct paid amount |
| `"Stock for X cannot go below zero"` | Adjustment/Waste entry exceeds current stock | Verify quantity, check for an earlier unrecorded entry |
| `"Cashier already has an active shift"` | Trying to open a second shift before closing the first | Close the existing shift, then open a new one |
| `"Only submitted orders can be cancelled"` | Trying to cancel a Draft order | Delete the draft instead of cancelling |
| POS page shows no tables | `Enable Table Management` is off in Canteen Settings | Turn it on, or this is expected for take-away-only canteens |

---

## Role & Permission Matrix

| Capability | Canteen Admin | Canteen Manager | Canteen Cashier | Canteen Staff | Canteen User |
|---|---|---|---|---|---|
| **Configure Canteen Settings** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Create/edit Items, Categories** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Take orders on POS** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **View own orders/wallet only** | — | — | — | — | ✅ |
| **View items & inventory (read-only)** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Create Stock Entries** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Open/close own shift** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **View all reports** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Read any Canteen Order / Invoice** | ✅ | ✅ | — | — | own-only |

> This table is built from the doctype-level `has_permission` hooks on **Canteen Order** and **Canteen Invoice** plus the role descriptions in `README.md`/`setup.py`. The other doctypes rely on standard Frappe role permissions configured separately — verify the actual Role Permission Manager matches this before go-live, since the code doesn't enforce all of these rows directly.

---

## Technical Architecture (For IT Reference)

### Data flow diagram

```
     Canteen Order (submit)
          │ on_submit
          ▼
     ┌──────────────────────┐
     │ validate_items()      │  ← stock availability check
     └──────────┬────────────┘
                ▼
     ┌──────────────────────┐      ┌───────────────────────────┐
     │ update_inventory()    │ ───▶ │ Canteen Inventory (− qty) │
     └──────────┬────────────┘      └───────────────────────────┘
                ▼
     ┌──────────────────────────────┐
     │ update_wallet_if_applicable()│ ───▶ Canteen Employee Wallet (− balance)
     │                               │ ───▶ Canteen Wallet Transaction (audit)
     └──────────┬────────────────────┘
                ▼
     ┌──────────────────────┐
     │ create_invoice()      │ ───▶ Canteen Invoice (auto-submitted, status=Paid)
     └──────────────────────┘


     Canteen Stock Entry (submit)
          │ on_submit
          ▼
     ┌──────────────────────┐
     │ update_inventory()    │ ───▶ Canteen Inventory (± qty, by Stock Type)
     └──────────────────────┘
```

### Doctypes (database tables)

| Table | Type | Stores |
|---|---|---|
| **Canteen Settings** | Single | Global config — tax, payment modes, alerts |
| **Canteen Category** | Master | Menu categories |
| **Canteen Item** | Master | Menu items, pricing, dietary flags |
| **Canteen Order** | Document | Customer orders (submittable) |
| **Canteen Order Item** | Child | Order line items |
| **Canteen Invoice** | Document | Auto-generated, auto-submitted on order completion |
| **Canteen Invoice Item** | Child | Invoice line items |
| **Canteen Inventory** | Balance | Running stock quantity per item |
| **Canteen Stock Entry** | Document | Purchase / Return / Adjustment / Opening Stock / Waste |
| **Canteen Stock Entry Item** | Child | Stock entry line items |
| **Canteen Employee Wallet** | Balance | Per-employee prepaid balance |
| **Canteen Wallet Transaction** | Ledger | Credit/debit audit trail |
| **Canteen Shift** | Document | Cashier shift open/close + sales split |
| **Canteen Table** | Master | Dine-in tables and status |
| **Canteen Supplier** | Master | Stock suppliers |
| **Canteen Payment Mode** | Master | Enabled payment modes |

### Key files

| File | Purpose |
|---|---|
| `hooks.py` | App config, role fixtures, doc_events, scheduler_events, after_install |
| `api.py` | ~40 whitelisted endpoints — POS data, orders, invoices, inventory, wallets, shifts, tables, dashboard stats |
| `setup.py` | `after_install` — creates roles, default categories, default tables |
| `tasks.py` | Scheduled jobs — daily sales summary email, weekly report (placeholder, unimplemented), hourly shift alerts |
| `utils.py` | Shared helpers (settings lookup, currency formatting) |
| `templates/invoice.html` | Printable invoice template |
| `canteen_management/doctype/canteen_order/canteen_order.py` | Order validation, totals, inventory/wallet/invoice side effects |
| `canteen_management/doctype/canteen_stock_entry/canteen_stock_entry.py` | Stock entry inventory updates by type |
| `canteen_management/doctype/canteen_inventory/canteen_inventory.py` | Stock validation, low-stock realtime flag, `check_low_stock`, `get_stock_summary` |
| `canteen_management/page/canteen_pos/` | The POS Desk page (HTML/JS/Python) |

### API endpoints (selected)

| Endpoint | What it does |
|---|---|
| `pos_data` | Single-call bootstrap for the POS page |
| `create_order` | Create + submit an order (cascades inventory/wallet/invoice) |
| `cancel_order` | Cancel a submitted order, restore inventory |
| `create_stock_entry` | Create a stock movement |
| `get_wallet_balance` / `topup_wallet` | Wallet read/credit |
| `open_shift` / `close_shift` | Shift lifecycle |
| `get_dashboard_stats` / `get_sales_overview` / `get_top_items` | Dashboard summaries |

All endpoints use `@frappe.whitelist()` — they rely on standard Frappe session auth and the doctype-level `has_permission` hooks on Order/Invoice; most other endpoints have no extra role check beyond a valid login, so don't assume every endpoint is locked to Cashier/Manager roles without checking the function body.

---

## Development Guide (For IT)

### Project structure

```
canteen_management/
├── canteen_management/
│   ├── doctype/                # All custom doctypes
│   ├── page/canteen_pos/       # POS Desk page
│   ├── report/                 # Script reports
│   ├── workspace/              # Workspace shortcuts
├── config/
├── templates/invoice.html
├── public/css|js/
├── fixtures/custom_field.json
├── patches/v1_0/initial_setup.py
├── hooks.py
├── api.py
├── setup.py
├── tasks.py
├── utils.py
├── pyproject.toml
└── README.md
```

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

This section exists because the original README documented features as if a customer-facing flow existed. It doesn't. If you're scoping work, these are the real gaps:

| Gap | Current state |
|---|---|
| No customer self-ordering | Every order is entered by a Cashier; no kiosk, QR, or web ordering page |
| No `Customer` doctype | `customer_name` is free text on the order, not a master record — no order history per customer |
| No order status visibility for the customer | `status` jumps straight to `Completed` on submit; intermediate states aren't surfaced anywhere a customer could see them |
| No customer notifications | Zero emails/SMS go to the customer or employee — only manager-facing alerts exist |
| No self-service wallet top-up | `topup_wallet()` requires API/Desk access; an employee can't reload their own balance |
| "Delivery" order type has no support | Selectable on the order, but no address field, delivery tracking, or rider assignment anywhere in the schema |
| No feedback/rating mechanism | No way to capture customer satisfaction per order |
| Status workflow is mostly unused | `Pending/Preparing/Ready/Served` exist in the schema but `on_submit` skips straight to `Completed` |

---

## License

MIT
