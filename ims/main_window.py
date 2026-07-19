"""Main IMS window: menu bar, colored shortcut buttons, dashboard grids, footer."""

from __future__ import annotations

from datetime import date

from .qt import *
from .db import db, money, current_company
from .widgets import SearchBar, DataTable, html_table, preview_html, info, error
from .basic import SystemInfoDialog, CompaniesDialog, SimpleNameDialog, ProductsDialog
from .people import EmployeesDialog, CustomersDialog, SuppliersDialog
from .users import UsersDialog, ChangePasswordDialog, RolesDialog, MENU_KEYS, get_role_permissions
from .settings import BackupDatabaseDialog, RestoreDatabaseDialog
from .about import AboutDialog, HelpDialog, ContactSupportDialog
from .inventory import (PurchaseOrdersDialog, SalesOrdersDialog, CreditSalesDialog,
                        ReturnsDialog, PurchaseReturnsDialog, DamageProductsDialog)
from .accounts import (CashCollectionsDialog, CashDeliveriesDialog, BankTransactionsDialog,
                       MoneyListDialog, InvestmentHeadsDialog, InvestmentsDialog)
from .reports import AllReportDialog, Reports
from .history import HistoryDialog

NAV_BUTTONS = [
    ("Product\nConfiguration", "#ffffff", "#1c3f92", "Inventory Management"),
    ("Purchase\nOrder", "#41d0c4", "#00332f", "Inventory Management"),
    ("Sales Order", "#fdf3f3", "#8b1a1a", "Inventory Management"),
    ("Credit Sales", "#f8d2f1", "#5c1049", "Inventory Management"),
    ("Cash\nCollection", "#eeb0f4", "#3c1050", "Cash Collection"),
    ("Cash\nDelivery", "#e9c4d9", "#4d1030", "Account Management"),
    ("Income", "#c7af78", "#3a2c00", "Account Management"),
    ("Expense", "#d1b399", "#3a2410", "Account Management"),
    ("MIS Report", "#f2a81a", "#4a3000", "MIS Report"),
]


class MainWindow(QMainWindow):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.logout_requested = False
        self.setWindowTitle("IMS")
        self.setMinimumSize(1200, 720)
        self.setStyleSheet("""
            QMainWindow { background-color: #1533a5; }
            QMenuBar { background: #f0f0f0; color: black; }
            QMenuBar::item:selected { background: #d2e0f0; }
            QMenu { background: #f8f8f8; color: black; }
            QMenu::item:selected { background: #316ac5; color: white; }
            QTableWidget { background: white; alternate-background-color: #eaf1fb;
                           color: black; gridline-color: #c0c0c0;
                           selection-background-color: #316ac5; selection-color: white; }
            QTableWidget::item { background-color: white; color: black; }
            QTableWidget::item:alternate { background-color: #eaf1fb; }
            QTableWidget::item:selected { background-color: #316ac5; color: white; }
            QHeaderView::section { background: #dbe5f1; color: #10243c; padding: 3px;
                                   border: 1px solid #aab8c9; }
            QLineEdit { background: white; color: black; border: 1px solid #7f9db9;
                        padding: 3px; }
            QPushButton { background: #e8eef7; color: #10243c;
                          border: 1px solid #7f9db9; padding: 4px 12px; }
            QStatusBar { background: #ece9d8; color: black; }
        """)
        self._build_menus()
        self._build_body()
        self.refresh()

    # -- UI -------------------------------------------------------------------
    def _build_menus(self):
        bar = self.menuBar()
        role = self.user.get("role", "Staff")
        self.is_admin = role == "Admin"
        self.permitted = set(MENU_KEYS) if self.is_admin else get_role_permissions(role)
        if "Account Management" in self.permitted:
            self.permitted.add("Cash Collection")

        basic_config = [
            ("System Information", lambda: SystemInfoDialog(self).exec()),
            ("Companies", lambda: CompaniesDialog(self).exec()),
            ("Brands", lambda: SimpleNameDialog("brands", "Brand", self).exec()),
            ("Category", lambda: SimpleNameDialog("categories", "Category", self).exec()),
            ("Product", self.open_products),
            ("Bank", lambda: SimpleNameDialog("banks", "Bank", self).exec()),
            ("Card Type Setups", lambda: SimpleNameDialog("card_types", "Card Type", self).exec()),
        ] if "Basic" in self.permitted else []
        basic_items = basic_config + ([None] if basic_config else []) + [
            ("LogOut", self.logout), ("Exit", self.close)]

        menus = {
            "Basic": basic_items,
            "Employee": [("Employee List", lambda: EmployeesDialog(self).exec())]
                        if "Employee" in self.permitted else [],
            "Customer and Supplier": [
                ("Customer Info", self.open_customers),
                ("Supplier Info", self.open_suppliers),
            ] if "Customer and Supplier" in self.permitted else [],
            "Inventory Management": [
                ("Product Configuration", self.open_products),
                ("Purchase Order", self.open_purchases),
                ("Sales Order", self.open_sales),
                ("Credit Sales", self.open_credit_sales),
                ("Sales Return", self.open_returns),
                ("Purchase Return", self.open_purchase_returns),
                ("Damage Product", self.open_damage_products),
            ] if "Inventory Management" in self.permitted else [],
            "Account Management": ([
                ("Cash Collection", self.open_collections),
            ] if "Cash Collection" in self.permitted else []) + ([
                ("Cash Delivery", self.open_deliveries),
                ("Bank Transaction", lambda: BankTransactionsDialog(self).exec()),
                ("Investment Heads", lambda: InvestmentHeadsDialog(self).exec()),
                ("Share Investments", lambda: InvestmentsDialog(self).exec()),
                ("Income", self.open_income),
                ("Expense", self.open_expense),
            ] if "Account Management" in self.permitted else []),
            "MIS Report": [
                ("Daily Sales Report", lambda: Reports(self).daily_sales()),
                ("Daily Purchase Report", lambda: Reports(self).daily_purchase()),
                ("Monthly Sales Report", lambda: Reports(self).monthly_sales()),
                ("Monthly Purchase Report", lambda: Reports(self).monthly_purchase()),
                ("Yearly Sales Report", lambda: Reports(self).yearly_sales()),
                ("Yearly Purchase Report", lambda: Reports(self).yearly_purchase()),
                ("Expenditure Report", lambda: Reports(self).expense_income()),
                ("Stock Report", lambda: Reports(self).stock_report()),
                ("Customer Wise Sales", lambda: Reports(self).customer_wise_sales()),
                ("Supplier Wise Purchase", lambda: Reports(self).supplier_wise_purchase()),
                None,
                ("Summary Report", self.open_reports),
            ] if "MIS Report" in self.permitted else [],
            "Settings": [
                ("Change Password", self.open_change_password),
                *([("User Management", self.open_user_management)] if self.is_admin else []),
                *([("Roles and Permissions", self.open_roles)] if self.is_admin else []),
                ("Backup Database", lambda: BackupDatabaseDialog(self).exec()),
                *([("Restore Database", self.open_restore_database)] if self.is_admin else []),
            ],
            "About": [
                ("About IMS", lambda: AboutDialog(self).exec()),
                ("Help", lambda: HelpDialog(self).exec()),
                ("Contact Support", lambda: ContactSupportDialog(self).exec())
            ],
            "History": [
                ("Account Ledger", self.open_account_ledger),
                ("Stock Ledger", self.open_stock_ledger),
                ("Transaction Log", lambda: Reports(self).transaction_log()),
                ("Stock Transaction Log", lambda: Reports(self).stock_transaction_log()),
                ("Log", self.open_history),
            ] if self.is_admin else []
        }
        for title, actions in menus.items():
            if not actions:
                continue
            menu = bar.addMenu(title)
            for entry in actions:
                if entry is None:
                    menu.addSeparator()
                    continue
                name, fn = entry
                action = QAction(name, self)
                action.triggered.connect(lambda checked=False, f=fn: (f(), self.refresh()))
                menu.addAction(action)

    def _build_body(self):
        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # top strip: nav buttons + company banner
        top = QWidget()
        top.setStyleSheet("background-color: #1533a5;")
        tlay = QHBoxLayout(top)
        tlay.setContentsMargins(8, 8, 8, 8)
        handlers = [self.open_products, self.open_purchases, self.open_sales,
                    self.open_credit_sales, self.open_collections, self.open_deliveries,
                    self.open_income, self.open_expense, self.open_reports]
        for (label, bg, fg, menu_key), fn in zip(NAV_BUTTONS, handlers):
            if menu_key not in self.permitted:
                continue
            b = QPushButton(label)
            b.setMinimumHeight(58)
            b.setMinimumWidth(96)
            b.setStyleSheet(
                f"QPushButton {{ background-color: {bg}; color: {fg}; font-weight: bold;"
                f" border: 2px solid #e07b00; border-radius: 3px; }}"
                f"QPushButton:hover {{ border: 2px solid #ffffff; }}")
            b.clicked.connect(lambda checked=False, f=fn: (f(), self.refresh()))
            tlay.addWidget(b)
        tlay.addStretch(1)
        self.banner = QLabel()
        self.banner.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._update_banner()
        tlay.addWidget(self.banner)
        lay.addWidget(top)

        # dashboard grids
        content = QWidget()
        content.setStyleSheet("background-color: #1533a5;")
        clay = QHBoxLayout(content)
        clay.setContentsMargins(8, 4, 8, 4)

        left = QVBoxLayout()
        self.cust_search = SearchBar()
        self.cust_search.searched.connect(lambda *_: self.refresh())
        left.addWidget(self.cust_search)
        self.cust_table = DataTable(["Code", "Customer Name", "Contact No", "Address",
                                     "Amount", "S.Type"])
        left.addWidget(self.cust_table, 1)
        cust_print = QPushButton("Print")
        cust_print.setObjectName("find")
        cust_print.clicked.connect(self.print_customers)
        left.addWidget(cust_print, 0, Qt.AlignmentFlag.AlignLeft)
        clay.addLayout(left, 3)

        clay.addSpacing(8)

        right = QVBoxLayout()
        self.prod_search = SearchBar()
        self.prod_search.searched.connect(lambda *_: self.refresh())
        right.addWidget(self.prod_search)
        self.prod_table = DataTable(["Product Name", "Brand Name", "Short", "Stock"])
        right.addWidget(self.prod_table, 1)
        prod_print = QPushButton("Print")
        prod_print.setObjectName("find")
        prod_print.clicked.connect(self.print_products)
        right.addWidget(prod_print, 0, Qt.AlignmentFlag.AlignRight)
        clay.addLayout(right, 2)
        lay.addWidget(content, 1)

        footer = QLabel("Developed By © SOFTIFE")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        footer.setStyleSheet("background-color: #0b1f8f; color: white; font-size: 14pt;"
                             "font-family: Georgia; font-weight: bold; padding: 8px;")
        lay.addWidget(footer)

    # -- dashboard data ---------------------------------------------------------
    def _update_banner(self):
        company = current_company() or {}
        name = company.get("name") or "IMS"
        self.banner.setText(
            "<div style='color:white'><span style='font-size:20pt;font-family:Georgia'>"
            f"{name}</span><br>"
            "<i style='font-size:11pt;color:#ffe97a'>Inventory Management Software (IMS)</i></div>")
        self.setWindowTitle(f"IMS — {name}")
        self.statusBar().showMessage(
            f"Logged in As : {self.user['username']}    |    Company : {name}"
            f"    |    {date.today():%d %b %Y}")

    def refresh(self):
        self._update_banner()
        s = f"%{self.cust_search.edit.text().strip()}%"
        rows = db().fetch_all(
            """SELECT c.id, c.code, c.name, c.contact_no, c.address, d.total_due,
                      c.customer_type
               FROM customers c JOIN customer_dues d ON d.id = c.id
               WHERE c.company_id = app_company_id()
                     AND (c.name ILIKE %s OR c.code ILIKE %s OR c.contact_no ILIKE %s)
               ORDER BY c.name""", (s, s, s))
        self.cust_table.set_rows(
            [(r["id"], r["code"], r["name"], r["contact_no"], r["address"],
              money(r["total_due"]), "Credit") for r in rows])

        s = f"%{self.prod_search.edit.text().strip()}%"
        rows = db().fetch_all(
            """SELECT p.id, p.model_name, b.name AS brand,
                      GREATEST(p.warning_qty - p.stock_qty, 0) AS short, p.stock_qty
               FROM products p LEFT JOIN brands b ON b.id = p.brand_id
               WHERE p.company_id = app_company_id()
                     AND (p.model_name ILIKE %s OR b.name ILIKE %s)
               ORDER BY b.name, p.model_name""", (s, s))
        self.prod_table.set_rows(
            [(r["id"], r["model_name"], r["brand"], money(r["short"]),
              money(r["stock_qty"])) for r in rows])

    def print_customers(self):
        rows = db().fetch_all(
            """SELECT c.code, c.name, c.contact_no, c.address, d.total_due
               FROM customers c JOIN customer_dues d ON d.id = c.id
               WHERE c.company_id = app_company_id() ORDER BY c.name""")
        preview_html(self, "Customer List", html_table(
            ["Code", "Customer Name", "Contact No", "Address", "Amount"],
            [[r["code"], r["name"], r["contact_no"], r["address"], float(r["total_due"])]
             for r in rows]))

    def print_products(self):
        rows = db().fetch_all(
            """SELECT p.model_name, b.name AS brand,
                      GREATEST(p.warning_qty - p.stock_qty, 0) AS short, p.stock_qty
               FROM products p LEFT JOIN brands b ON b.id = p.brand_id
               WHERE p.company_id = app_company_id()
               ORDER BY b.name, p.model_name""")
        preview_html(self, "Product Stock List", html_table(
            ["Product Name", "Brand Name", "Short", "Stock"],
            [[r["model_name"], r["brand"], float(r["short"]), float(r["stock_qty"])]
             for r in rows]))

    # -- window openers ---------------------------------------------------------
    def open_products(self):
        ProductsDialog(self).exec()

    def open_customers(self):
        CustomersDialog(self).exec()

    def open_suppliers(self):
        SuppliersDialog(self).exec()

    def open_purchases(self):
        PurchaseOrdersDialog(self).exec()

    def open_sales(self):
        SalesOrdersDialog(self.user["username"], self).exec()

    def open_credit_sales(self):
        CreditSalesDialog(self.user["username"], self).exec()

    def open_returns(self):
        ReturnsDialog(self).exec()

    def open_purchase_returns(self):
        PurchaseReturnsDialog(self).exec()

    def open_damage_products(self):
        DamageProductsDialog(self).exec()

    def open_collections(self):
        CashCollectionsDialog(self).exec()

    def open_deliveries(self):
        CashDeliveriesDialog(self).exec()

    def open_income(self):
        MoneyListDialog("incomes", "income_date", "Income", self).exec()

    def open_expense(self):
        MoneyListDialog("expenses", "expense_date", "Expense", self).exec()

    def open_reports(self):
        AllReportDialog(self).exec()
        self.refresh()

    def open_change_password(self):
        ChangePasswordDialog(self.user, self).exec()

    def open_user_management(self):
        if self.user.get("role") != "Admin":
            error(self, "Only Admin users can access User Management.")
            return
        UsersDialog(self.user, self).exec()

    def open_roles(self):
        if self.user.get("role") != "Admin":
            error(self, "Only Admin users can view Roles and Permissions.")
            return
        RolesDialog(self).exec()

    def open_account_ledger(self):
        if self.user.get("role") != "Admin":
            error(self, "Only Admin users can view the account ledger.")
            return
        Reports(self).account_ledger()

    def open_stock_ledger(self):
        if self.user.get("role") != "Admin":
            error(self, "Only Admin users can view the stock ledger.")
            return
        Reports(self).stock_ledger()

    def open_history(self):
        if self.user.get("role") != "Admin":
            error(self, "Only Admin users can view the activity log.")
            return
        HistoryDialog(self).exec()

    def open_restore_database(self):
        if self.user.get("role") != "Admin":
            error(self, "Only Admin users can restore the database.")
            return
        if RestoreDatabaseDialog(self).exec():
            self.logout()

    def logout(self):
        self.logout_requested = True
        self.close()
