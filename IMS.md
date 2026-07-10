# IMS.md

Desktop inventory management app: PySide6/PyQt6 + PostgreSQL, single `ims/` package,
no test suite. User-facing docs live in [README.md](README.md); developer notes per
module live in [ims/README.md](ims/README.md).

## Architecture

```
                    python -m ims  (__main__.py)
                    │  --initdb → createdb + psql db_schema.sql
                    │  Fusion style, forced light palette
                    ▼
              login.py (LoginDialog, users table)
                    ▼
        main_window.py (menus, shortcut buttons, dashboard)
        role gating via users.MENU_KEYS / get_role_permissions
                    │ opens dialogs from feature modules
  ┌─────────┬──────────┬────────────┬────────────┬───────────┬─────────┐
  basic.py  people.py  inventory.py accounts.py  reports.py  users.py
  companies employees  purchase/    cash/bank/   All Report  accounts,
  products  customers  sales orders income/      grid +      roles,
  banks     suppliers  credit sales expense/     print       passwords
  categories           returns      investments
  ├── settings.py  backup/restore (pg_dump/psql)
  ├── history.py   audit-log viewer (admin only)
  └── about.py     about/help
                    │
        widgets.py — shared UI: ListDialog, LookupField, SearchBar,
                     DataTable, dedit/dspin/pydate, html_table,
                     preview_html (print preview), info/error/confirm
                    │
   qt.py (PySide6→PyQt6 shim)        db.py (one shared psycopg2 conn,
                                      dict rows, transaction(), money(),
                                      next_code()/next_serial(),
                                      company + user session vars)
                    │
   bootstrap.py — packaged builds only: starts the bundled PostgreSQL
   (initdb into per-user data dir), sets IMS_DATABASE_URL; no-op in dev.
   Installers built by packaging/ (see packaging/README.md).
                    │
        PostgreSQL ims_db — db_schema.sql (re-runnable, seed data)
        migrate_multicompany.sql (company_id + RLS)
        migrate_audit_log.sql (audit triggers → history.py)
```

## Rules for changes

- Import Qt classes only via `from .qt import *` — never import PySide6/PyQt6 directly.
- All DB access goes through `db()` from [ims/db.py](ims/db.py). Use `db().transaction()`
  for multi-statement writes; `execute()` commits a single statement.
- Document numbering must use `db().next_code()` / `next_serial()` — they scope per
  company via `COMPANY_SCOPED_TABLES`.
- A new table holding per-company data needs: a `company_id` column with RLS policy
  (pattern in `migrate_multicompany.sql`), membership in `COMPANY_SCOPED_TABLES`
  in [ims/db.py](ims/db.py), and `WHERE company_id = app_company_id()` in its queries.
- Schema changes go into `db_schema.sql` (kept re-runnable) **and** a `migrate_*.sql`
  for existing databases.
- Reuse [ims/widgets.py](ims/widgets.py) building blocks (ListDialog, LookupField,
  DataTable, SearchBar, html_table/preview_html) before writing new UI; apply
  `DIALOG_QSS` to new dialogs.
- A new menu entry needs a permission key in `MENU_KEYS` ([ims/users.py](ims/users.py))
  so role gating keeps working.
- Format money for display with `db.money()`, never manual f-strings.
- Audit logging is automatic via DB triggers — do not add app-side logging.
- Comments: match the codebase — one-line module docstring, docstrings only on
  non-obvious helpers. Where a subclass overrides behavior, refer to the parent
  class's method docs instead of restating them.
- Verify by running `venv/bin/python -m ims` (login `sajad` / `1234`); there are no
  automated tests.
- Files the app writes at runtime (e.g. product images) must go under
  `bootstrap.media_root()` / `data_root()`, never under the install/bundle dir;
  read-only bundled files resolve via `bootstrap.resource_root()`.
