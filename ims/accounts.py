"""Account Management: Cash Collection, Cash Delivery, Bank Transaction,
Income, Expense, Investment Heads and Share Investments."""

from __future__ import annotations

from .qt import *
from .db import db, money
from .widgets import (DIALOG_QSS, DataTable, ListDialog, LookupField, SearchBar,
                      dedit, pydate, dspin, info, error)
from .inventory import CUSTOMER_PICK_SQL, SUPPLIER_PICK_SQL
from .people import CustomerForm, SupplierForm


class CashCollectionForm(QDialog):
    """Receive money from a customer (matches the video's Cash Collection form)."""

    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("Cash Collection")
        self.setMinimumWidth(520)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.entry_date = dedit()
        self.receipt = QLineEdit(f"R-{db().next_serial('cash_collections'):05d}")
        self.receipt.setReadOnly(True)
        self.customer = LookupField("Customers", ["Code", "Name", "Contact", "Address", "Due"],
                                    CUSTOMER_PICK_SQL,
                                    new_form_factory=lambda p: CustomerForm(None, p))
        self.customer.selected.connect(
            lambda rec: self.total_due.setValue(float(rec.get("total_due") or 0)))
        self.pay_type = QComboBox()
        self.pay_type.addItems(["Cash", "Check", "Mobile Bank"])
        self.bank = QComboBox()
        self.bank.addItem("", None)
        for b in db().fetch_all("SELECT id, name FROM banks ORDER BY name"):
            self.bank.addItem(b["name"], b["id"])
        self.check_no = QLineEdit()
        self.issue_date = dedit()
        self.branch = QLineEdit()
        self.account_no = QLineEdit()
        self.mobile_bank = QLineEdit()
        self.mobile_no = QLineEdit()
        self.total_due = dspin(read_only=True)
        self.amount = dspin()
        self.adjustment = dspin()
        self.due_after = dspin(read_only=True)
        for w in (self.amount, self.adjustment):
            w.valueChanged.connect(self._recalc)
        form.addRow("Entry Date", self.entry_date)
        form.addRow("Receipt No", self.receipt)
        form.addRow("Customer", self.customer)
        form.addRow("Pay Type", self.pay_type)
        form.addRow("Bank Name", self.bank)
        form.addRow("Check No", self.check_no)
        form.addRow("C.Issue Date", self.issue_date)
        form.addRow("Branch Name", self.branch)
        form.addRow("Account No", self.account_no)
        form.addRow("Mobile Bank", self.mobile_bank)
        form.addRow("bKash No", self.mobile_no)
        form.addRow("Total Due", self.total_due)
        form.addRow("Amount", self.amount)
        form.addRow("Adjustment", self.adjustment)
        form.addRow("Due Amount", self.due_after)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)

        if rec_id:
            c = db().fetch_one("SELECT * FROM cash_collections WHERE id = %s", (rec_id,))
            d = c["entry_date"]; self.entry_date.setDate(QDate(d.year, d.month, d.day))
            self.receipt.setText(c["receipt_no"])
            self.customer.set_record(db().fetch_one(
                """SELECT c.id, c.code, c.name, d.total_due FROM customers c
                   JOIN customer_dues d ON d.id = c.id WHERE c.id = %s""", (c["customer_id"],)))
            self.pay_type.setCurrentText(c["pay_type"])
            if c["bank_id"]:
                self.bank.setCurrentIndex(max(self.bank.findData(c["bank_id"]), 0))
            self.check_no.setText(c["check_no"]); self.branch.setText(c["branch_name"])
            self.account_no.setText(c["account_no"]); self.mobile_bank.setText(c["mobile_bank"])
            self.mobile_no.setText(c["mobile_no"])
            self.amount.setValue(float(c["amount"]))
            self.adjustment.setValue(float(c["adjustment"]))

    def _recalc(self):
        self.due_after.setValue(self.total_due.value() - self.amount.value()
                                - self.adjustment.value())

    def save(self):
        if not self.customer.value():
            error(self, "Select a customer.")
            return
        params = (pydate(self.entry_date), self.customer.value(), self.pay_type.currentText(),
                  self.bank.currentData(), self.check_no.text(), pydate(self.issue_date),
                  self.branch.text(), self.account_no.text(), self.mobile_bank.text(),
                  self.mobile_no.text(), self.amount.value(), self.adjustment.value())
        if self.rec_id:
            db().execute(
                """UPDATE cash_collections SET entry_date=%s, customer_id=%s, pay_type=%s,
                       bank_id=%s, check_no=%s, check_issue_date=%s, branch_name=%s,
                       account_no=%s, mobile_bank=%s, mobile_no=%s, amount=%s, adjustment=%s
                   WHERE id=%s""", params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO cash_collections (entry_date, customer_id, pay_type, bank_id,
                       check_no, check_issue_date, branch_name, account_no, mobile_bank,
                       mobile_no, amount, adjustment, receipt_no)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                params + (self.receipt.text(),))
        self.accept()


class CashCollectionsDialog(ListDialog):
    title = "Cash Collections"
    headers = ["Entry Date", "Receipt No", "Customer", "Contact No", "Pay Type", "Amount",
               "Adjustment"]
    buttons = ("New", "Edit", "Delete", "Close")

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT cc.id, cc.entry_date, cc.receipt_no, c.name, c.contact_no,
                      cc.pay_type, cc.amount, cc.adjustment
               FROM cash_collections cc JOIN customers c ON c.id = cc.customer_id
               WHERE c.name ILIKE %s OR cc.receipt_no ILIKE %s
               ORDER BY cc.entry_date DESC, cc.id DESC""", (f"%{search}%",) * 2)
        return [(r["id"], r["entry_date"].strftime("%d %b %Y"), r["receipt_no"], r["name"],
                 r["contact_no"], r["pay_type"], money(r["amount"]), money(r["adjustment"]))
                for r in rows]

    def open_form(self, rec_id=None):
        return bool(CashCollectionForm(rec_id, self).exec())

    def delete_sql(self):
        return "DELETE FROM cash_collections WHERE id = %s"


class CashDeliveryForm(QDialog):
    """Pay money out to a supplier."""

    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("Cash Delivery")
        self.setMinimumWidth(500)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.entry_date = dedit()
        self.voucher = QLineEdit(f"V-{db().next_serial('cash_deliveries'):05d}")
        self.voucher.setReadOnly(True)
        self.supplier = LookupField("All Suppliers", ["Code", "Name", "Contact No", "Total Due"],
                                    SUPPLIER_PICK_SQL,
                                    new_form_factory=lambda p: SupplierForm(None, p))
        self.supplier.selected.connect(
            lambda rec: self.total_due.setValue(float(rec.get("total_due") or 0)))
        self.pay_type = QComboBox(); self.pay_type.addItems(["Cash", "Check", "Mobile Bank"])
        self.bank = QComboBox()
        self.bank.addItem("", None)
        for b in db().fetch_all("SELECT id, name FROM banks ORDER BY name"):
            self.bank.addItem(b["name"], b["id"])
        self.account_no = QLineEdit()
        self.total_due = dspin(read_only=True)
        self.amount = dspin()
        self.remarks = QTextEdit(); self.remarks.setMaximumHeight(60)
        form.addRow("Entry Date", self.entry_date)
        form.addRow("Voucher No", self.voucher)
        form.addRow("Supplier", self.supplier)
        form.addRow("Pay Type", self.pay_type)
        form.addRow("Bank Name", self.bank)
        form.addRow("Account No", self.account_no)
        form.addRow("Total Due", self.total_due)
        form.addRow("Amount", self.amount)
        form.addRow("Remarks", self.remarks)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)

        if rec_id:
            c = db().fetch_one("SELECT * FROM cash_deliveries WHERE id = %s", (rec_id,))
            d = c["entry_date"]; self.entry_date.setDate(QDate(d.year, d.month, d.day))
            self.voucher.setText(c["voucher_no"])
            self.supplier.set_record(db().fetch_one(
                """SELECT s.id, s.code, s.name, d.total_due FROM suppliers s
                   JOIN supplier_dues d ON d.id = s.id WHERE s.id = %s""", (c["supplier_id"],)))
            self.pay_type.setCurrentText(c["pay_type"])
            if c["bank_id"]:
                self.bank.setCurrentIndex(max(self.bank.findData(c["bank_id"]), 0))
            self.account_no.setText(c["account_no"])
            self.amount.setValue(float(c["amount"]))
            self.remarks.setPlainText(c["remarks"] or "")

    def save(self):
        if not self.supplier.value():
            error(self, "Select a supplier.")
            return
        params = (pydate(self.entry_date), self.supplier.value(), self.pay_type.currentText(),
                  self.bank.currentData(), self.account_no.text(), self.amount.value(),
                  self.remarks.toPlainText())
        if self.rec_id:
            db().execute(
                """UPDATE cash_deliveries SET entry_date=%s, supplier_id=%s, pay_type=%s,
                       bank_id=%s, account_no=%s, amount=%s, remarks=%s WHERE id=%s""",
                params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO cash_deliveries (entry_date, supplier_id, pay_type, bank_id,
                       account_no, amount, remarks, voucher_no)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", params + (self.voucher.text(),))
        self.accept()


class CashDeliveriesDialog(ListDialog):
    title = "Cash Delivery"
    headers = ["Entry Date", "Name", "Contact No", "Pay Type", "Amount", "Status"]
    buttons = ("New", "Edit", "Delete", "Close")

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT cd.id, cd.entry_date, s.name, s.contact_no, cd.pay_type, cd.amount
               FROM cash_deliveries cd JOIN suppliers s ON s.id = cd.supplier_id
               WHERE s.name ILIKE %s OR cd.voucher_no ILIKE %s
               ORDER BY cd.entry_date DESC, cd.id DESC""", (f"%{search}%",) * 2)
        return [(r["id"], r["entry_date"].strftime("%d %b %Y"), r["name"], r["contact_no"],
                 r["pay_type"], money(r["amount"]), "Cash Delivery") for r in rows]

    def open_form(self, rec_id=None):
        return bool(CashDeliveryForm(rec_id, self).exec())

    def delete_sql(self):
        return "DELETE FROM cash_deliveries WHERE id = %s"


class BankTransactionForm(QDialog):
    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("Bank Transaction")
        self.setMinimumWidth(460)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.entry_date = dedit()
        self.tran_no = QLineEdit(f"T-{db().next_serial('bank_transactions'):05d}")
        self.tran_no.setReadOnly(True)
        self.tran_type = QComboBox(); self.tran_type.addItems(["Deposit", "Withdraw"])
        self.bank = QComboBox()
        for b in db().fetch_all("SELECT id, name FROM banks ORDER BY name"):
            self.bank.addItem(b["name"], b["id"])
        self.amount = dspin()
        self.check_no = QLineEdit()
        self.remarks = QTextEdit(); self.remarks.setMaximumHeight(60)
        form.addRow("Entry Date", self.entry_date)
        form.addRow("Tran. No", self.tran_no)
        form.addRow("Tran. Type", self.tran_type)
        form.addRow("Bank Name", self.bank)
        form.addRow("Amount", self.amount)
        form.addRow("Check No", self.check_no)
        form.addRow("Remarks", self.remarks)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)

        if rec_id:
            t = db().fetch_one("SELECT * FROM bank_transactions WHERE id = %s", (rec_id,))
            d = t["entry_date"]; self.entry_date.setDate(QDate(d.year, d.month, d.day))
            self.tran_no.setText(t["tran_no"])
            self.tran_type.setCurrentText(t["tran_type"])
            if t["bank_id"]:
                self.bank.setCurrentIndex(max(self.bank.findData(t["bank_id"]), 0))
            self.amount.setValue(float(t["amount"]))
            self.check_no.setText(t["check_no"])
            self.remarks.setPlainText(t["remarks"] or "")

    def save(self):
        params = (pydate(self.entry_date), self.tran_type.currentText(),
                  self.bank.currentData(), self.amount.value(), self.check_no.text(),
                  self.remarks.toPlainText())
        if self.rec_id:
            db().execute(
                """UPDATE bank_transactions SET entry_date=%s, tran_type=%s, bank_id=%s,
                       amount=%s, check_no=%s, remarks=%s WHERE id=%s""",
                params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO bank_transactions (entry_date, tran_type, bank_id, amount,
                       check_no, remarks, tran_no) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                params + (self.tran_no.text(),))
        self.accept()


class BankTransactionsDialog(ListDialog):
    title = "Bank Transactions"
    headers = ["Trans. Date", "Tran No", "Type", "Bank", "Amount", "Check No", "Remarks"]

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT t.id, t.entry_date, t.tran_no, t.tran_type, b.name AS bank, t.amount,
                      t.check_no, t.remarks
               FROM bank_transactions t LEFT JOIN banks b ON b.id = t.bank_id
               WHERE t.tran_no ILIKE %s OR b.name ILIKE %s
               ORDER BY t.entry_date DESC, t.id DESC""", (f"%{search}%",) * 2)
        return [(r["id"], r["entry_date"].strftime("%d %b %Y"), r["tran_no"], r["tran_type"],
                 r["bank"], money(r["amount"]), r["check_no"], r["remarks"]) for r in rows]

    def open_form(self, rec_id=None):
        return bool(BankTransactionForm(rec_id, self).exec())

    def delete_sql(self):
        return "DELETE FROM bank_transactions WHERE id = %s"


class MoneyEntryForm(QDialog):
    """Date + description + amount, shared by Income and Expense."""

    def __init__(self, table: str, date_col: str, label: str, rec_id=None, parent=None):
        super().__init__(parent)
        self.table, self.date_col, self.rec_id = table, date_col, rec_id
        self.setWindowTitle(label)
        self.setMinimumWidth(420)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.entry_date = dedit()
        self.description = QTextEdit(); self.description.setMaximumHeight(70)
        self.amount = dspin()
        form.addRow("Date", self.entry_date)
        form.addRow("Description", self.description)
        form.addRow("Amount", self.amount)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)
        if rec_id:
            r = db().fetch_one(f"SELECT * FROM {table} WHERE id = %s", (rec_id,))
            d = r[date_col]; self.entry_date.setDate(QDate(d.year, d.month, d.day))
            self.description.setPlainText(r["description"] or "")
            self.amount.setValue(float(r["amount"]))

    def save(self):
        if self.amount.value() <= 0:
            error(self, "Amount must be positive.")
            return
        if self.rec_id:
            db().execute(
                f"UPDATE {self.table} SET {self.date_col}=%s, description=%s, amount=%s WHERE id=%s",
                (pydate(self.entry_date), self.description.toPlainText(),
                 self.amount.value(), self.rec_id))
        else:
            db().execute(
                f"INSERT INTO {self.table} ({self.date_col}, description, amount) VALUES (%s,%s,%s)",
                (pydate(self.entry_date), self.description.toPlainText(), self.amount.value()))
        self.accept()


class MoneyListDialog(ListDialog):
    headers = ["Date", "Description", "Amount"]

    def __init__(self, table: str, date_col: str, label: str, parent=None):
        self._table, self._date_col, self._label = table, date_col, label
        self.title = label
        super().__init__(parent)
        self.setWindowTitle(label)

    def load_rows(self, search):
        rows = db().fetch_all(
            f"""SELECT id, {self._date_col} AS d, description, amount FROM {self._table}
                WHERE description ILIKE %s ORDER BY d DESC, id DESC""", (f"%{search}%",))
        return [(r["id"], r["d"].strftime("%d %b %Y"), r["description"], money(r["amount"]))
                for r in rows]

    def open_form(self, rec_id=None):
        return bool(MoneyEntryForm(self._table, self._date_col, self._label, rec_id, self).exec())

    def delete_sql(self):
        return f"DELETE FROM {self._table} WHERE id = %s"


class InvestmentHeadForm(QDialog):
    def __init__(self, head_type: str, rec_id=None, parent=None):
        super().__init__(parent)
        self.head_type, self.rec_id = head_type, rec_id
        self.setWindowTitle("Investment Head")
        self.setMinimumWidth(360)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.code = QLineEdit(); self.code.setReadOnly(True)
        self.name = QLineEdit()
        form.addRow("Code", self.code)
        form.addRow("Name", self.name)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)
        if rec_id:
            r = db().fetch_one("SELECT * FROM investment_heads WHERE id = %s", (rec_id,))
            self.code.setText(r["code"]); self.name.setText(r["name"])
        else:
            self.code.setText(db().next_code("investment_heads"))

    def save(self):
        if not self.name.text().strip():
            error(self, "Name is required.")
            return
        if self.rec_id:
            db().execute("UPDATE investment_heads SET name = %s WHERE id = %s",
                         (self.name.text().strip(), self.rec_id))
        else:
            db().execute(
                "INSERT INTO investment_heads (code, name, head_type) VALUES (%s,%s,%s)",
                (self.code.text(), self.name.text().strip(), self.head_type))
        self.accept()


HEAD_TABS = [("Fixed Asset", "FIXED"), ("Current Asset", "CURRENT"), ("Liability", "LIABILITY")]
INV_TABS = [("Fixed Assets", "FIXED"), ("Current Assets", "CURRENT"),
            ("Liabilites Rec.", "LIAB_REC"), ("Liabilities Pay", "LIAB_PAY")]


class InvestmentHeadsDialog(QDialog):
    """Investment Heads window with Fixed/Current/Liability tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Investment Heads")
        self.setMinimumSize(620, 460)
        self.setStyleSheet(DIALOG_QSS)
        outer = QHBoxLayout(self)
        self.tabs = QTabWidget()
        self.tables = {}
        for label, kind in HEAD_TABS:
            w = QWidget()
            lay = QVBoxLayout(w)
            t = DataTable(["Code", "Name"])
            lay.addWidget(t)
            self.tables[kind] = t
            self.tabs.addTab(w, label)
        outer.addWidget(self.tabs, 1)
        side = QVBoxLayout()
        for name, fn in [("New", self.on_new), ("Edit", self.on_edit),
                         ("Delete", self.on_delete), ("Close", self.accept)]:
            b = QPushButton(name); b.setMinimumWidth(90); b.clicked.connect(fn)
            side.addWidget(b)
        side.addStretch(1)
        self.total_lbl = QLabel("Total : 0")
        side.addWidget(self.total_lbl)
        outer.addLayout(side)
        self.tabs.currentChanged.connect(lambda *_: self.reload())
        self.reload()

    def _kind(self):
        return HEAD_TABS[self.tabs.currentIndex()][1]

    def reload(self):
        rows = db().fetch_all(
            "SELECT id, code, name FROM investment_heads WHERE head_type = %s ORDER BY code",
            (self._kind(),))
        self.tables[self._kind()].set_rows([(r["id"], r["code"], r["name"]) for r in rows])
        self.total_lbl.setText(f"Total : {len(rows)}")

    def on_new(self):
        if InvestmentHeadForm(self._kind(), None, self).exec():
            self.reload()

    def on_edit(self):
        rec_id = self.tables[self._kind()].current_id()
        if rec_id is None:
            info(self, "Select a record first.")
            return
        if InvestmentHeadForm(self._kind(), rec_id, self).exec():
            self.reload()

    def on_delete(self):
        rec_id = self.tables[self._kind()].current_id()
        if rec_id is None:
            info(self, "Select a record first.")
            return
        try:
            db().execute("DELETE FROM investment_heads WHERE id = %s", (rec_id,))
        except Exception as exc:
            db().conn.rollback()
            error(self, f"Cannot delete:\n{exc}")
            return
        self.reload()


class InvestmentForm(QDialog):
    def __init__(self, inv_type: str, rec_id=None, parent=None):
        super().__init__(parent)
        self.inv_type, self.rec_id = inv_type, rec_id
        self.setWindowTitle("Share Investment")
        self.setMinimumWidth(420)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.entry_date = dedit()
        head_type = "LIABILITY" if inv_type.startswith("LIAB") else inv_type
        self.head = QComboBox()
        for h in db().fetch_all(
                "SELECT id, name FROM investment_heads WHERE head_type = %s ORDER BY code",
                (head_type,)):
            self.head.addItem(h["name"], h["id"])
        self.purpose = QLineEdit()
        self.amount = dspin()
        form.addRow("Enter Date", self.entry_date)
        form.addRow("Invest Head", self.head)
        form.addRow("Purpose", self.purpose)
        form.addRow("Amount", self.amount)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)
        if rec_id:
            r = db().fetch_one("SELECT * FROM investments WHERE id = %s", (rec_id,))
            d = r["entry_date"]; self.entry_date.setDate(QDate(d.year, d.month, d.day))
            self.head.setCurrentIndex(max(self.head.findData(r["head_id"]), 0))
            self.purpose.setText(r["purpose"])
            self.amount.setValue(float(r["amount"]))

    def save(self):
        if self.head.currentData() is None:
            error(self, "Create an investment head first.")
            return
        if self.rec_id:
            db().execute(
                """UPDATE investments SET entry_date=%s, head_id=%s, purpose=%s, amount=%s
                   WHERE id=%s""",
                (pydate(self.entry_date), self.head.currentData(), self.purpose.text(),
                 self.amount.value(), self.rec_id))
        else:
            db().execute(
                """INSERT INTO investments (entry_date, head_id, purpose, amount, inv_type)
                   VALUES (%s,%s,%s,%s,%s)""",
                (pydate(self.entry_date), self.head.currentData(), self.purpose.text(),
                 self.amount.value(), self.inv_type))
        self.accept()


class InvestmentsDialog(QDialog):
    """Share Investments window with 4 tabs, as in the video."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share Investments")
        self.setMinimumSize(700, 480)
        self.setStyleSheet(DIALOG_QSS)
        outer = QHBoxLayout(self)
        self.tabs = QTabWidget()
        self.tables = {}
        for label, kind in INV_TABS:
            w = QWidget()
            lay = QVBoxLayout(w)
            t = DataTable(["Enter Date", "Invest Head", "Purpose", "Amount"])
            lay.addWidget(t)
            self.tables[kind] = t
            self.tabs.addTab(w, label)
        outer.addWidget(self.tabs, 1)
        side = QVBoxLayout()
        for name, fn in [("New", self.on_new), ("Edit", self.on_edit),
                         ("Delete", self.on_delete), ("Close", self.accept)]:
            b = QPushButton(name); b.setMinimumWidth(90); b.clicked.connect(fn)
            side.addWidget(b)
        side.addStretch(1)
        self.amount_lbl = QLabel("T.Amount: 0.00")
        self.amount_lbl.setStyleSheet("font-weight:bold; color:#a00;")
        side.addWidget(self.amount_lbl)
        self.total_lbl = QLabel("Total : 0")
        side.addWidget(self.total_lbl)
        outer.addLayout(side)
        self.tabs.currentChanged.connect(lambda *_: self.reload())
        self.reload()

    def _kind(self):
        return INV_TABS[self.tabs.currentIndex()][1]

    def reload(self):
        rows = db().fetch_all(
            """SELECT i.id, i.entry_date, h.name AS head, i.purpose, i.amount
               FROM investments i JOIN investment_heads h ON h.id = i.head_id
               WHERE i.inv_type = %s ORDER BY i.entry_date, i.id""", (self._kind(),))
        self.tables[self._kind()].set_rows(
            [(r["id"], r["entry_date"].strftime("%d %b %Y"), r["head"], r["purpose"],
              money(r["amount"])) for r in rows])
        self.total_lbl.setText(f"Total : {len(rows)}")
        self.amount_lbl.setText(f"T.Amount: {money(sum(r['amount'] for r in rows))}")

    def on_new(self):
        if InvestmentForm(self._kind(), None, self).exec():
            self.reload()

    def on_edit(self):
        rec_id = self.tables[self._kind()].current_id()
        if rec_id is None:
            info(self, "Select a record first.")
            return
        if InvestmentForm(self._kind(), rec_id, self).exec():
            self.reload()

    def on_delete(self):
        rec_id = self.tables[self._kind()].current_id()
        if rec_id is None:
            info(self, "Select a record first.")
            return
        db().execute("DELETE FROM investments WHERE id = %s", (rec_id,))
        self.reload()
