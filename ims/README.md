# ims/ — developer guide

Single flat package; every feature is one module that exposes Qt dialogs opened
from `main_window.py`. Read [../CLAUDE.md](../CLAUDE.md) first for the
architecture diagram and change rules.

## Modules

| Module | Contents |
|---|---|
| `__main__.py` | Entry point; `--initdb` shells out to `createdb` + `psql -f db_schema.sql`; login → MainWindow loop with logout support |
| `bootstrap.py` | Embedded PostgreSQL for packaged builds: initdb/start the bundled server, per-user data dirs (`data_root()`, `media_root()`), sets `IMS_DATABASE_URL`. No-op on a dev checkout — see [../packaging/README.md](../packaging/README.md) |
| `qt.py` | The only place Qt is imported. Tries PySide6, falls back to PyQt6 (`Signal` aliased). Import everything with `from .qt import *` |
| `db.py` | `Database` wrapper around one shared psycopg2 connection (dict rows). `db()` singleton, `transaction()`, `next_code()`/`next_serial()` (company-scoped), `money()`. Publishes `app.company_id` / `app.username` as session vars for RLS and audit triggers |
| `widgets.py` | Shared UI: `ListDialog` (list + form CRUD base), `LookupField` (magnifier picker), `SearchBar`, `DataTable`, `dedit`/`dspin`/`pydate` field helpers, `html_table` + `preview_html` (print preview), `info`/`error`/`confirm`, `DIALOG_QSS` |
| `login.py` | `LoginDialog`; sha-hashed password check against `users`, calls `set_current_user()` |
| `main_window.py` | Menu bar, colored shortcut buttons, dashboard grids (customer dues, stock/short), footer. Hides menus the role lacks (`users.get_role_permissions`) |
| `basic.py` | Basic menu: System Information, Companies (shops), Brands, Categories, Products, Banks, Card Types. `ProductDetailDialog` is reused by inventory |
| `people.py` | Employee / Customer / Supplier list dialogs and forms with running dues |
| `inventory.py` | Largest module: Purchase Order, Sales Order (discount/VAT/card), Credit Sales (installment schedule), Returns. Exports `CUSTOMER_PICK_SQL` / `SUPPLIER_PICK_SQL` reused by accounts |
| `accounts.py` | Cash Collection/Delivery, Bank Transactions, Income, Expense, Investment Heads, Share Investments |
| `reports.py` | All Report button grid; every report renders through `html_table` → `preview_html` |
| `users.py` | User accounts, roles (`ROLES`), `MENU_KEYS` permission matrix, password change |
| `settings.py` | Backup (`pg_dump`) / Restore (`psql`) with `reset_connection()` after restore |
| `history.py` | Admin-only audit-log viewer; data comes from DB triggers (`migrate_audit_log.sql`) |
| `about.py` | About/help dialogs |

## Patterns

- **CRUD screens** subclass or instantiate `ListDialog`; look at `people.py` for the
  smallest complete example before writing a new one.
- **Forms** are plain `QDialog`s with `DIALOG_QSS`, field helpers from `widgets.py`,
  and save/update via `db().execute()` or `db().transaction()`.
- **Printing** is HTML-based: build with `html_table()`, show with `preview_html()`.
- **Company scoping** is invisible at call sites: session var + RLS + column defaults;
  just keep `WHERE company_id = app_company_id()` in explicit filters.
- When overriding a method, keep the docstring to a pointer at the parent class's
  method unless the override changes the contract.
