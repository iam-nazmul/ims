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

## Project layout

```
db_schema.sql        PostgreSQL schema + seed data (re-runnable)
ims/
  __main__.py        entry point (python -m ims), --initdb helper
  qt.py              PySide6/PyQt6 compatibility imports
  db.py              connection, query helpers, transactions
  widgets.py         shared UI: list dialogs, lookup pickers, print preview
  login.py           LogIn dialog
  main_window.py     dashboard, menus, colored shortcut buttons
  basic.py           system info, companies, categories, banks, products
  people.py          employees, customers, suppliers
  inventory.py       purchase orders, sales orders, returns, credit sales
  accounts.py        cash collection/delivery, bank, income, expense, investments
  reports.py         All Report window and every report
```


```
git remote add origin git@github.com:iam-nazmul/ims.git
git branch -M main
git push -u origin main
```


sudo -u postgres psql -c "ALTER USER nazmul WITH PASSWORD '123456';"