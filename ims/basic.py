"""Basic menu: System Information, Companies (shops), Brands, Category,
Product, Bank, Card Types."""

from __future__ import annotations

import os
import shutil

from .qt import *
from .db import db, money, set_current_company, current_company_id
from .widgets import (DIALOG_QSS, ListDialog, LookupField, dedit, pydate,
                      dspin, info, error)

from .bootstrap import media_root

REPO_ROOT = media_root()
PRODUCT_IMAGE_DIR = os.path.join(REPO_ROOT, "media", "images", "products")
PRODUCT_IMAGE_RELDIR = "media/images/products"


class CompanyForm(QDialog):
    """Create / edit one company (shop)."""

    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("Company")
        self.setMinimumWidth(520)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        self.name = QLineEdit()
        self.address = QTextEdit()
        self.address.setMaximumHeight(60)
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.web = QLineEdit()
        self.start = dedit()
        self.active = QCheckBox("Active")
        self.active.setChecked(True)
        form.addRow("Company Code", self.code)
        form.addRow("Company Name", self.name)
        form.addRow("Company Address", self.address)
        form.addRow("Telephone No", self.phone)
        form.addRow("E-mail Address", self.email)
        form.addRow("Web Address", self.web)
        form.addRow("Start Date", self.start)
        form.addRow("", self.active)
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
            c = db().fetch_one("SELECT * FROM companies WHERE id = %s", (rec_id,))
            self.code.setText(c["code"])
            self.name.setText(c["name"])
            self.address.setPlainText(c["address"] or "")
            self.phone.setText(c["telephone_no"] or "")
            self.email.setText(c["email_address"] or "")
            self.web.setText(c["web_address"] or "")
            if c["start_date"]:
                d = c["start_date"]
                self.start.setDate(QDate(d.year, d.month, d.day))
            self.active.setChecked(c["is_active"])
        else:
            self.code.setText(db().next_code("companies"))

    def save(self):
        name = self.name.text().strip()
        if not name:
            error(self, "Company name is required.")
            return
        params = (name, self.address.toPlainText(), self.phone.text(),
                  self.email.text(), self.web.text(), pydate(self.start),
                  self.active.isChecked())
        if self.rec_id:
            db().execute(
                """UPDATE companies SET name=%s, address=%s, telephone_no=%s,
                       email_address=%s, web_address=%s, start_date=%s, is_active=%s
                   WHERE id=%s""", params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO companies (name, address, telephone_no, email_address,
                       web_address, start_date, is_active, code)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", params + (self.code.text(),))
        self.accept()


class CompaniesDialog(ListDialog):
    title = "All Companies"
    headers = ["Code", "Name", "Address", "Telephone", "Active", "Default"]

    def load_rows(self, search):
        default_id = db().scalar("SELECT default_company_id FROM system_info WHERE id = 1")
        rows = db().fetch_all(
            """SELECT id, code, name, address, telephone_no, is_active FROM companies
               WHERE code ILIKE %s OR name ILIKE %s ORDER BY code""",
            (f"%{search}%", f"%{search}%"))
        return [(r["id"], r["code"], r["name"], r["address"], r["telephone_no"],
                 "Yes" if r["is_active"] else "No",
                 "Yes" if r["id"] == default_id else "") for r in rows]

    def open_form(self, rec_id=None):
        return bool(CompanyForm(rec_id, self).exec())

    def on_delete(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a record first.")
            return
        if rec_id == current_company_id():
            error(self, "You cannot delete the company you are currently working in.")
            return
        super().on_delete()

    def delete_sql(self):
        return "DELETE FROM companies WHERE id = %s"


class SystemInfoDialog(QDialog):
    """Pick the working company and edit its information. Saving makes the
    selected company the default for every part of the application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Information")
        self.setMinimumWidth(520)
        self.setStyleSheet(DIALOG_QSS)
        self.company_switched = False

        lay = QVBoxLayout(self)
        pick_box = QGroupBox("Select Company")
        pick_form = QFormLayout(pick_box)
        self.company = QComboBox()
        for c in db().fetch_all("SELECT id, code, name FROM companies ORDER BY code"):
            self.company.addItem(f"{c['code']} — {c['name']}", c["id"])
        self.company.currentIndexChanged.connect(self._load_company)
        pick_form.addRow("Company", self.company)
        lay.addWidget(pick_box)

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
        save = QPushButton("Save && Use This Company")
        save.clicked.connect(self.save)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(close)
        lay.addLayout(row)

        cid = current_company_id()
        if cid is not None:
            i = self.company.findData(cid)
            if i >= 0:
                self.company.setCurrentIndex(i)
        self._load_company()

    def _load_company(self):
        cid = self.company.currentData()
        if cid is None:
            return
        c = db().fetch_one("SELECT * FROM companies WHERE id = %s", (cid,))
        self.name.setText(c["name"])
        self.address.setPlainText(c["address"] or "")
        self.phone.setText(c["telephone_no"] or "")
        self.email.setText(c["email_address"] or "")
        self.web.setText(c["web_address"] or "")
        if c["start_date"]:
            d = c["start_date"]
            self.start.setDate(QDate(d.year, d.month, d.day))

    def save(self):
        cid = self.company.currentData()
        if cid is None:
            error(self, "Create a company first (Basic > Companies).")
            return
        if not self.name.text().strip():
            error(self, "Company name is required.")
            return
        db().execute(
            """UPDATE companies SET name=%s, address=%s, telephone_no=%s,
                   email_address=%s, web_address=%s, start_date=%s WHERE id=%s""",
            (self.name.text().strip(), self.address.toPlainText(), self.phone.text(),
             self.email.text(), self.web.text(), pydate(self.start), cid))
        db().execute(
            """INSERT INTO system_info (id, default_company_id) VALUES (1, %s)
               ON CONFLICT (id) DO UPDATE SET default_company_id = EXCLUDED.default_company_id""",
            (cid,))
        self.company_switched = cid != current_company_id()
        set_current_company(cid)
        info(self, "System information saved. The application now works with "
                   f"'{self.name.text().strip()}'.")
        self.accept()


class SimpleNameForm(QDialog):
    """Code + Name form for brands / categories / banks / card types."""

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
            rec = db().fetch_one(
                f"SELECT * FROM {table} WHERE id = %s AND company_id = app_company_id()",
                (rec_id,))
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
            db().execute(
                f"UPDATE {self.table} SET name = %s WHERE id = %s AND company_id = app_company_id()",
                (name, self.rec_id))
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
            f"WHERE company_id = app_company_id() AND (code ILIKE %s OR name ILIKE %s) "
            f"ORDER BY code",
            (f"%{search}%", f"%{search}%"))
        return [(r["id"], r["code"], r["name"]) for r in rows]

    def open_form(self, rec_id=None):
        return bool(SimpleNameForm(self._table, self._label, rec_id, self).exec())

    def delete_sql(self):
        return f"DELETE FROM {self._table} WHERE id = %s AND company_id = app_company_id()"


class ProductDetailDialog(QDialog):
    """Product Detail form: brand/category lookups, warranty group, rates."""

    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.image_filename = ""
        self.setWindowTitle("Product Detail")
        self.setMinimumWidth(620)
        self.setStyleSheet(DIALOG_QSS)

        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        form = QFormLayout()
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        self.brand = LookupField(
            "All Brands", ["Code", "Name"],
            "SELECT id, code, name FROM brands "
            "WHERE company_id = app_company_id() AND name ILIKE %s ORDER BY code",
            new_form_factory=lambda p: SimpleNameForm("brands", "Brand", None, p))
        self.category = LookupField(
            "All Category", ["Code", "Name"],
            "SELECT id, code, name FROM categories "
            "WHERE company_id = app_company_id() AND name ILIKE %s ORDER BY code",
            new_form_factory=lambda p: SimpleNameForm("categories", "Category", None, p))
        self.ptype = QComboBox()
        self.ptype.addItems(["NoBarCode", "BarCode"])
        self.model = QLineEdit()
        self.warning = dspin(999999, 0)
        form.addRow("Code", self.code)
        form.addRow("Brand", self.brand)
        form.addRow("Category", self.category)
        form.addRow("Product Type", self.ptype)
        form.addRow("Model Name", self.model)
        form.addRow("Warning Qty", self.warning)
        top.addLayout(form, 1)

        img_col = QVBoxLayout()
        self.image_preview = QLabel("No Image")
        self.image_preview.setFixedSize(120, 120)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet("border: 1px solid #7f9db9; background: white;")
        img_col.addWidget(self.image_preview)
        upload_btn = QPushButton("Upload Image")
        upload_btn.clicked.connect(self.choose_image)
        img_col.addWidget(upload_btn)
        remove_btn = QPushButton("Remove Image")
        remove_btn.clicked.connect(self.remove_image)
        img_col.addWidget(remove_btn)
        img_col.addStretch(1)
        top.addLayout(img_col)
        lay.addLayout(top)

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
            p = db().fetch_one(
                "SELECT * FROM products WHERE id = %s AND company_id = app_company_id()",
                (rec_id,))
            self.code.setText(p["code"])
            if p["brand_id"]:
                self.brand.set_record(db().fetch_one(
                    "SELECT id, code, name FROM brands WHERE id = %s", (p["brand_id"],)))
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
            self.image_filename = p["image_path"] or ""
        else:
            self.code.setText(db().next_code("products", 6))
        self._update_preview()

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Upload Product Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        os.makedirs(PRODUCT_IMAGE_DIR, exist_ok=True)
        ext = os.path.splitext(path)[1].lower()
        filename = f"product_{self.code.text()}{ext}"
        shutil.copyfile(path, os.path.join(PRODUCT_IMAGE_DIR, filename))
        self.image_filename = f"{PRODUCT_IMAGE_RELDIR}/{filename}"
        self._update_preview()

    def remove_image(self):
        self.image_filename = ""
        self._update_preview()

    def _update_preview(self):
        pix = QPixmap(os.path.join(REPO_ROOT, self.image_filename)) \
            if self.image_filename else QPixmap()
        if pix.isNull():
            self.image_preview.clear()
            self.image_preview.setText("No Image")
        else:
            self.image_preview.setPixmap(pix.scaled(
                120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def save(self):
        if not self.model.text().strip():
            error(self, "Model name is required.")
            return
        params = (self.brand.value(), self.category.value(), self.ptype.currentText(),
                  self.model.text().strip(), self.warning.value(),
                  self.warranty["Compressor"].value(), self.warranty["Panel"].value(),
                  self.warranty["Motor"].value(), self.warranty["Spareparts"].value(),
                  self.warranty["Service"].value(), self.pur_rate.value(),
                  self.sales_rate.value(), self.mrp_rate.value(), self.image_filename)
        if self.rec_id:
            db().execute(
                """UPDATE products SET brand_id=%s, category_id=%s, product_type=%s,
                       model_name=%s, warning_qty=%s, warranty_compressor=%s, warranty_panel=%s,
                       warranty_motor=%s, warranty_spareparts=%s, warranty_service=%s,
                       purchase_rate=%s, sales_rate=%s, mrp_rate=%s, image_path=%s
                   WHERE id=%s AND company_id = app_company_id()""",
                params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO products (brand_id, category_id, product_type, model_name,
                       warning_qty, warranty_compressor, warranty_panel, warranty_motor,
                       warranty_spareparts, warranty_service, purchase_rate, sales_rate,
                       mrp_rate, image_path, code)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                params + (self.code.text(),))
        self.accept()


class ProductsDialog(ListDialog):
    title = "Products"
    headers = ["Code", "Model Name", "Category", "Brand", "Stock", "Pur.Rate", "Sales Rate", "MRP"]

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT p.id, p.code, p.model_name, cat.name AS category, b.name AS brand,
                      p.stock_qty, p.purchase_rate, p.sales_rate, p.mrp_rate
               FROM products p
               LEFT JOIN categories cat ON cat.id = p.category_id
               LEFT JOIN brands b ON b.id = p.brand_id
               WHERE p.company_id = app_company_id()
                     AND (p.code ILIKE %s OR p.model_name ILIKE %s
                          OR cat.name ILIKE %s OR b.name ILIKE %s)
               ORDER BY p.code""", (f"%{search}%",) * 4)
        return [(r["id"], r["code"], r["model_name"], r["category"], r["brand"],
                 money(r["stock_qty"]), money(r["purchase_rate"]),
                 money(r["sales_rate"]), money(r["mrp_rate"])) for r in rows]

    def open_form(self, rec_id=None):
        return bool(ProductDetailDialog(rec_id, self).exec())

    def delete_sql(self):
        return "DELETE FROM products WHERE id = %s AND company_id = app_company_id()"
