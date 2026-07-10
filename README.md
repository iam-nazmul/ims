# IMS — Inventory Management Software

A desktop inventory management application (PySide6/PyQt6 + PostgreSQL) recreated
from the `ims.wmv` demo video of the original "Shahajahan Enterprise" WinForms app.

## Features

- **Login** — user/password (seeded: `sajad` / `1234`, `admin` / `admin`)
- **Dashboard** — customer dues grid + product stock/short grid, search and print
- **Basic** — System Information, Companies, Categories, Products (warranty,
  warning qty, rates), Banks, Card Types
- **Employee / Customer / Supplier** management with running dues
- **Purchase Order** — multi-item entry, stock & rate updates, supplier due, stock tab, invoice
- **Sales Order** — multi-item entry with stock check, discount/VAT, card payment,
  printable Invoice/Bill, product returns (restock + refund)
- **Credit Sales** — down payment, interest, auto-generated monthly installment
  schedule, installment collection
- **Accounts** — Cash Collection, Cash Delivery, Bank Transactions, Income,
  Expense, Investment Heads, Share Investments (fixed/current/liability tabs)
- **MIS Reports** — the "All Report" grid: product/employee info, customer &
  supplier dues, stock, expense & income, daily/monthly/yearly sales and purchase,
  customer/supplier/bank ledgers, benefit reports, installment reports,
  cash-in-hand, profit & loss — all with print preview.
- **Multi-shop** — data is kept per company/shop; manage shops under Basic → Companies
- **User Management** — accounts, roles (Admin/Manager/Supervisor/Staff) with
  per-menu permissions, password change
- **History** — admin-only log of every create/edit/delete
- **Settings** — one-click database Backup / Restore

## Setup

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt

# create database and load schema + sample data
venv/bin/python -m ims --initdb        # runs createdb ims_db + psql -f db_schema.sql

# run
venv/bin/python -m ims
```

Log in with `sajad` / `1234`.

## Database connection

By default the app connects with `dbname=ims_db` as the current OS user.
Override with:

```bash
export IMS_DATABASE_URL="dbname=ims_db user=postgres password=... host=localhost"
```

If your PostgreSQL user requires a password, set one and include it in
`IMS_DATABASE_URL`:

```bash
sudo -u postgres psql -c "ALTER USER <your-user> WITH PASSWORD '<password>';"
```

## Backup & Restore

Use **Settings → Backup Database / Restore Database** inside the app to save or
load a full database dump.

## For developers

See [CLAUDE.md](CLAUDE.md) for the architecture overview and
[ims/README.md](ims/README.md) for the module-by-module developer guide.