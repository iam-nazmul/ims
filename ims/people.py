"""Employee, Customer and Supplier windows."""

from __future__ import annotations

from .qt import *
from .db import db, money
from .widgets import DIALOG_QSS, ListDialog, dedit, pydate, dspin, error


class EmployeeForm(QDialog):
    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("Employee")
        self.setMinimumWidth(520)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.code = QLineEdit(); self.code.setReadOnly(True)
        self.name = QLineEdit()
        self.father = QLineEdit()
        self.mother = QLineEdit()
        self.contact = QLineEdit()
        self.email = QLineEdit()
        self.nid = QLineEdit()
        self.blood = QComboBox()
        self.blood.addItems(["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        self.joining = dedit()
        self.designation = QComboBox()
        self.designation.setEditable(True)
        self.designation.addItems(["", "Show Room Manager", "Sales Man", "Accountant", "Guard"])
        self.present = QTextEdit(); self.present.setMaximumHeight(50)
        self.perm = QTextEdit(); self.perm.setMaximumHeight(50)
        self.salary = dspin()
        for label, w in [("Employee Code", self.code), ("Employee Name", self.name),
                         ("Father Name", self.father), ("Mother Name", self.mother),
                         ("Contact No", self.contact), ("Email ID", self.email),
                         ("National ID", self.nid), ("Blood Group", self.blood),
                         ("Joining Date", self.joining), ("Designation", self.designation),
                         ("Present Address", self.present), ("Perm. Address", self.perm),
                         ("Gross Salary", self.salary)]:
            form.addRow(label, w)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)

        if rec_id:
            e = db().fetch_one("SELECT * FROM employees WHERE id = %s", (rec_id,))
            self.code.setText(e["code"]); self.name.setText(e["name"])
            self.father.setText(e["father_name"]); self.mother.setText(e["mother_name"])
            self.contact.setText(e["contact_no"]); self.email.setText(e["email"])
            self.nid.setText(e["national_id"]); self.blood.setCurrentText(e["blood_group"])
            d = e["joining_date"]; self.joining.setDate(QDate(d.year, d.month, d.day))
            self.designation.setCurrentText(e["designation"])
            self.present.setPlainText(e["present_address"] or "")
            self.perm.setPlainText(e["permanent_address"] or "")
            self.salary.setValue(float(e["gross_salary"]))
        else:
            self.code.setText(db().next_code("employees"))

    def save(self):
        if not self.name.text().strip():
            error(self, "Employee name is required.")
            return
        params = (self.name.text().strip(), self.father.text(), self.mother.text(),
                  self.contact.text(), self.email.text(), self.nid.text(),
                  self.blood.currentText(), pydate(self.joining),
                  self.designation.currentText(), self.present.toPlainText(),
                  self.perm.toPlainText(), self.salary.value())
        if self.rec_id:
            db().execute(
                """UPDATE employees SET name=%s, father_name=%s, mother_name=%s, contact_no=%s,
                       email=%s, national_id=%s, blood_group=%s, joining_date=%s, designation=%s,
                       present_address=%s, permanent_address=%s, gross_salary=%s WHERE id=%s""",
                params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO employees (name, father_name, mother_name, contact_no, email,
                       national_id, blood_group, joining_date, designation, present_address,
                       permanent_address, gross_salary, code)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                params + (self.code.text(),))
        self.accept()


class EmployeesDialog(ListDialog):
    title = "Employees"
    headers = ["Code", "Name", "Contact No", "Designation", "Joining Date", "Gross Salary"]

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT id, code, name, contact_no, designation, joining_date, gross_salary
               FROM employees WHERE code ILIKE %s OR name ILIKE %s OR designation ILIKE %s
               ORDER BY code""", (f"%{search}%",) * 3)
        return [(r["id"], r["code"], r["name"], r["contact_no"], r["designation"],
                 r["joining_date"].strftime("%d %b %Y"), money(r["gross_salary"])) for r in rows]

    def open_form(self, rec_id=None):
        return bool(EmployeeForm(rec_id, self).exec())

    def delete_sql(self):
        return "DELETE FROM employees WHERE id = %s"


class CustomerForm(QDialog):
    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("Customer")
        self.setMinimumWidth(460)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.code = QLineEdit(); self.code.setReadOnly(True)
        self.name = QLineEdit()
        self.contact = QLineEdit()
        self.address = QTextEdit(); self.address.setMaximumHeight(60)
        self.ctype = QComboBox(); self.ctype.addItems(["Retail", "Wholesale"])
        self.opening = dspin()
        form.addRow("Customer Code", self.code)
        form.addRow("Customer Name", self.name)
        form.addRow("Contact No", self.contact)
        form.addRow("Address", self.address)
        form.addRow("Customer Type", self.ctype)
        form.addRow("Opening Due", self.opening)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)

        if rec_id:
            c = db().fetch_one("SELECT * FROM customers WHERE id = %s", (rec_id,))
            self.code.setText(c["code"]); self.name.setText(c["name"])
            self.contact.setText(c["contact_no"])
            self.address.setPlainText(c["address"] or "")
            self.ctype.setCurrentText(c["customer_type"])
            self.opening.setValue(float(c["opening_due"]))
        else:
            self.code.setText("NEW" + db().next_code("customers", 3))

    def save(self):
        if not self.name.text().strip():
            error(self, "Customer name is required.")
            return
        params = (self.name.text().strip(), self.contact.text(),
                  self.address.toPlainText(), self.ctype.currentText(), self.opening.value())
        if self.rec_id:
            db().execute(
                """UPDATE customers SET name=%s, contact_no=%s, address=%s,
                       customer_type=%s, opening_due=%s WHERE id=%s""",
                params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO customers (name, contact_no, address, customer_type,
                       opening_due, code) VALUES (%s,%s,%s,%s,%s,%s)""",
                params + (self.code.text(),))
        self.accept()


class CustomersDialog(ListDialog):
    title = "Customers"
    headers = ["A/C", "Name", "Address", "Contact No", "Total Due"]

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT c.id, c.code, c.name, c.address, c.contact_no, d.total_due
               FROM customers c JOIN customer_dues d ON d.id = c.id
               WHERE c.code ILIKE %s OR c.name ILIKE %s OR c.contact_no ILIKE %s
               ORDER BY c.name""", (f"%{search}%",) * 3)
        return [(r["id"], r["code"], r["name"], r["address"], r["contact_no"],
                 money(r["total_due"])) for r in rows]

    def open_form(self, rec_id=None):
        return bool(CustomerForm(rec_id, self).exec())

    def delete_sql(self):
        return "DELETE FROM customers WHERE id = %s"


class SupplierForm(QDialog):
    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("Supplier")
        self.setMinimumWidth(460)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.code = QLineEdit(); self.code.setReadOnly(True)
        self.name = QLineEdit()
        self.person = QLineEdit()
        self.contact = QLineEdit()
        self.address = QTextEdit(); self.address.setMaximumHeight(60)
        self.opening = dspin()
        form.addRow("Supplier Code", self.code)
        form.addRow("Supplier Name", self.name)
        form.addRow("Contact Per.", self.person)
        form.addRow("Contact No", self.contact)
        form.addRow("Address", self.address)
        form.addRow("Opening Due", self.opening)
        row = QHBoxLayout()
        save = QPushButton("Save"); save.clicked.connect(self.save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(save); row.addWidget(close)
        form.addRow(row)

        if rec_id:
            s = db().fetch_one("SELECT * FROM suppliers WHERE id = %s", (rec_id,))
            self.code.setText(s["code"]); self.name.setText(s["name"])
            self.person.setText(s["contact_person"]); self.contact.setText(s["contact_no"])
            self.address.setPlainText(s["address"] or "")
            self.opening.setValue(float(s["opening_due"]))
        else:
            self.code.setText(db().next_code("suppliers"))

    def save(self):
        if not self.name.text().strip():
            error(self, "Supplier name is required.")
            return
        params = (self.name.text().strip(), self.person.text(), self.contact.text(),
                  self.address.toPlainText(), self.opening.value())
        if self.rec_id:
            db().execute(
                """UPDATE suppliers SET name=%s, contact_person=%s, contact_no=%s,
                       address=%s, opening_due=%s WHERE id=%s""",
                params + (self.rec_id,))
        else:
            db().execute(
                """INSERT INTO suppliers (name, contact_person, contact_no, address,
                       opening_due, code) VALUES (%s,%s,%s,%s,%s,%s)""",
                params + (self.code.text(),))
        self.accept()


class SuppliersDialog(ListDialog):
    title = "All Suppliers"
    headers = ["Code", "Name", "Contact No", "Total Due"]

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT s.id, s.code, s.name, s.contact_no, d.total_due
               FROM suppliers s JOIN supplier_dues d ON d.id = s.id
               WHERE s.code ILIKE %s OR s.name ILIKE %s OR s.contact_no ILIKE %s
               ORDER BY s.code""", (f"%{search}%",) * 3)
        return [(r["id"], r["code"], r["name"], r["contact_no"], money(r["total_due"]))
                for r in rows]

    def open_form(self, rec_id=None):
        return bool(SupplierForm(rec_id, self).exec())

    def delete_sql(self):
        return "DELETE FROM suppliers WHERE id = %s"
