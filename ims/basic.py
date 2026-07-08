"""Basic menu: System Information, Companies, Category, Product, Bank, Card Types."""

from __future__ import annotations

from .qt import *
from .db import db, money
from .widgets import (DIALOG_QSS, ListDialog, LookupField, dedit, pydate,
                      dspin, info, error)


class SystemInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Information")
        self.setMinimumWidth(520)
        self.setStyleSheet(DIALOG_QSS)

        lay = QVBoxLayout(self)
        box = QGroupBox("Company Information")
        form = QFormLayout(box)
        self.name = QLineEdit()
        self.address = QTextEdit()
        self.address.setMaximumHeight(60)
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.web = QLineEdit()
        self.start = dedit()
        form.addRow("Company Name", self.name)
        form.addRow("Company Address", self.address)
        form.addRow("Telephone No", self.phone)
        form.addRow("E-mail Address", self.email)
        form.addRow("Web Address", self.web)
        form.addRow("System Start Date", self.start)
        lay.addWidget(box)

        row = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(close)
        lay.addLayout(row)

        si = db().fetch_one("SELECT * FROM system_info WHERE id = 1")
        if si:
            self.name.setText(si["company_name"])
            self.address.setPlainText(si["company_address"] or "")
            self.phone.setText(si["telephone_no"] or "")
            self.email.setText(si["email_address"] or "")
            self.web.setText(si["web_address"] or "")
            if si["system_start_date"]:
                d = si["system_start_date"]
                self.start.setDate(QDate(d.year, d.month, d.day))

    def save(self):
        db().execute(
            """INSERT INTO system_info (id, company_name, company_address, telephone_no,
                                        email_address, web_address, system_start_date)
               VALUES (1, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET
                 company_name = EXCLUDED.company_name,
                 company_address = EXCLUDED.company_address,
                 telephone_no = EXCLUDED.telephone_no,
                 email_address = EXCLUDED.email_address,
                 web_address = EXCLUDED.web_address,
                 system_start_date = EXCLUDED.system_start_date""",
            (self.name.text(), self.address.toPlainText(), self.phone.text(),
             self.email.text(), self.web.text(), pydate(self.start)))
        info(self, "System information saved.")
        self.accept()


class SimpleNameForm(QDialog):
    """Code + Name form for companies / categories / banks / card types."""

    def __init__(self, table: str, label: str, rec_id=None, parent=None):
        super().__init__(parent)
        self.table, self.rec_id = table, rec_id
        self.setWindowTitle(label)
        self.setMinimumWidth(360)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        self.name = QLineEdit()
        form.addRow(f"{label} Code", self.code)
        form.addRow(f"{label} Name", self.name)
        row = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(close)
        form.addRow(row)

        if rec_id:
            rec = db().fetch_one(f"SELECT * FROM {table} WHERE id = %s", (rec_id,))
            self.code.setText(rec["code"])
            self.name.setText(rec["name"])
        else:
            self.code.setText(db().next_code(table))

    def save(self):
        name = self.name.text().strip()
        if not name:
            error(self, "Name is required.")
            return
        if self.rec_id:
            db().execute(f"UPDATE {self.table} SET name = %s WHERE id = %s", (name, self.rec_id))
        else:
            db().execute(f"INSERT INTO {self.table} (code, name) VALUES (%s, %s)",
                         (self.code.text(), name))
        self.accept()


class SimpleNameDialog(ListDialog):
    headers = ["Code", "Name"]

    def __init__(self, table: str, title: str, parent=None):
        self._table, self._label = table, title
        self.title = f"All {title}"
        super().__init__(parent)
        self.setWindowTitle(self.title)

    def load_rows(self, search):
        rows = db().fetch_all(
            f"SELECT id, code, name FROM {self._table} "
            f"WHERE code ILIKE %s OR name ILIKE %s ORDER BY code",
            (f"%{search}%", f"%{search}%"))
        return [(r["id"], r["code"], r["name"]) for r in rows]

    def open_form(self, rec_id=None):
        return bool(SimpleNameForm(self._table, self._label, rec_id, self).exec())

    def delete_sql(self):
        return f"DELETE FROM {self._table} WHERE id = %s"


class ProductDetailDialog(QDialog):
    """Product Detail form: company/category lookups, warranty group, rates."""

    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("Product Detail")
        self.setMinimumWidth(620)
        self.setStyleSheet(DIALOG_QSS)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        self.company = LookupField("All Companies", ["Code", "Name"],
                                   "SELECT id, code, name FROM companies WHERE name ILIKE %s ORDER BY code")
        self.category = LookupField("All Category", ["Code", "Name"],
                                    "SELECT id, code, name FROM categories WHERE name ILIKE %s ORDER BY code")
        self.ptype = QComboBox()
        self.ptype.addItems(["NoBarCode", "BarCode"])
        self.model = QLineEdit()
        self.warning = dspin(999999, 0)
        form.addRow("Code", self.code)
        form.addRow("Company", self.company)
        form.addRow("Category", self.category)
        form.addRow("Product Type", self.ptype)
        form.addRow("Model Name", self.model)
        form.addRow("Warning Qty", self.warning)
        lay.addLayout(form)

        wbox = QGroupBox("Warrenty")
        wgrid = QGridLayout(wbox)
        self.warranty = {}
        for i, part in enumerate(["Compressor", "Motor", "Service", "Panel", "Spareparts"]):
            spin = QSpinBox()
            spin.setRange(0, 99)
            self.warranty[part] = spin
            r, c = i % 3, (i // 3) * 3
            wgrid.addWidget(QLabel(part), r, c)
            wgrid.addWidget(spin, r, c + 1)
            wgrid.addWidget(QLabel("Years"), r, c + 2)
        lay.addWidget(wbox)

        rbox = QGroupBox("Rates")
        rform = QGridLayout(rbox)
        self.pur_rate = dspin()
        self.sales_rate = dspin()
        self.mrp_rate = dspin()
        rform.addWidget(QLabel("Purchase Rate"), 0, 0)
        rform.addWidget(self.pur_rate, 0, 1)
        rform.addWidget(QLabel("Sales Rate"), 0, 2)
        rform.addWidget(self.sales_rate, 0, 3)
        rform.addWidget(QLabel("MRP"), 0, 4)
        rform.addWidget(self.mrp_rate, 0, 5)
        lay.addWidget(rbox)

        row = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(close)
        lay.addLayout(row)

        if rec_id:
            p = db().fetch_one("SELECT * FROM products WHERE id = %s", (rec_id,))
            self.code.setText(p["code"])
            if p["company_id"]:
                self.company.set_record(db().fetch_one(
                    "SELECT id, code, name FROM companies WHERE id = %s", (p["company_id"],)))
            if p["category_id"]:
                self.category.set_record(db().fetch_one(
                    "SELECT id, code, name FROM categories WHERE id = %s", (p["category_id"],)))
            self.ptype.setCurrentText(p["product_type"])
            self.model.setText(p["model_name"])
            self.warning.setValue(float(p["warning_qty"]))
            for part, col in [("Compressor", "warranty_compressor"), ("Panel", "warranty_panel"),
                              ("Motor", "warranty_motor"), ("Spareparts", "warranty_spareparts"),
                              ("Service", "warranty_service")]:
                self.warranty[part].setValue(p[col])
            self.pur_rate.setValue(float(p["purchase_rate"]))
            self.sales_rate.setValue(float(p["sales_rate"]))
            self.mrp_rate.setValue(float(p["mrp_rate"]))
        else:
            self.code.setText(db().next_code("products", 6))

    def save(self):
        if not self.model.text().strip():
            error(self, "Model name is required.")
            return
        params = (self.company.value(), self.category.value(), self.ptype.currentText(),
                  self.model.text().strip(), self.warning.value(),
                  self.warranty["Compressor"].value(), self.warranty["Panel"].value(),
                  self.warranty["Motor"].value(), self.warranty["Spareparts"].value(),
                  self.warranty["Service"].value(), self.pur_rate.value(),
                  self.sales_rate.value(), self.mrp_rate.value())
        if self.rec_id:
            db().execute(
                """UPDATE products SET company_id=%s, category_id=%s, product_type=%s,
                       model_name=%s, warning_qty=%s, warranty_compressor=%s, warranty_panel=%s,
                       warranty_motor=%s, warranty_spareparts=%s, warranty_service=%s,
                       purchase_rate=%s, sales_rate=%s, mrp_rate=%s WHERE id=%s""",
                params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO products (company_id, category_id, product_type, model_name,
                       warning_qty, warranty_compressor, warranty_panel, warranty_motor,
                       warranty_spareparts, warranty_service, purchase_rate, sales_rate,
                       mrp_rate, code)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                params + (self.code.text(),))
        self.accept()


class ProductsDialog(ListDialog):
    title = "Products"
    headers = ["Code", "Model Name", "Category", "Company", "Stock", "Pur.Rate", "Sales Rate", "MRP"]

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT p.id, p.code, p.model_name, cat.name AS category, com.name AS company,
                      p.stock_qty, p.purchase_rate, p.sales_rate, p.mrp_rate
               FROM products p
               LEFT JOIN categories cat ON cat.id = p.category_id
               LEFT JOIN companies com ON com.id = p.company_id
               WHERE p.code ILIKE %s OR p.model_name ILIKE %s
                     OR cat.name ILIKE %s OR com.name ILIKE %s
               ORDER BY p.code""", (f"%{search}%",) * 4)
        return [(r["id"], r["code"], r["model_name"], r["category"], r["company"],
                 money(r["stock_qty"]), money(r["purchase_rate"]),
                 money(r["sales_rate"]), money(r["mrp_rate"])) for r in rows]

    def open_form(self, rec_id=None):
        return bool(ProductDetailDialog(rec_id, self).exec())

    def delete_sql(self):
        return "DELETE FROM products WHERE id = %s"
