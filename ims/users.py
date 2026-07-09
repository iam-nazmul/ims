"""User Management: user accounts, roles and password changes."""

from __future__ import annotations

import hashlib

from .qt import *
from .db import db
from .widgets import DIALOG_QSS, ListDialog, info, error, confirm

ROLES = ["Admin", "Manager", "Supervisor", "Staff"]

# Top-level menus that are gated by role. Admin always has all of them;
# Settings and About are always visible to everyone regardless of this table.
MENU_KEYS = ["Basic", "Employee", "Customer and Supplier", "Inventory Management",
             "Account Management", "MIS Report"]


def get_role_permissions(role: str) -> set[str]:
    rows = db().fetch_all("SELECT menu_key FROM role_permissions WHERE role = %s", (role,))
    return {r["menu_key"] for r in rows}


def set_role_permissions(role: str, menu_keys: set[str]):
    with db().transaction() as cur:
        cur.execute("DELETE FROM role_permissions WHERE role = %s", (role,))
        for key in menu_keys:
            cur.execute("INSERT INTO role_permissions (role, menu_key) VALUES (%s, %s)",
                        (role, key))


def hash_pw(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class UserForm(QDialog):
    def __init__(self, rec_id=None, parent=None):
        super().__init__(parent)
        self.rec_id = rec_id
        self.setWindowTitle("User")
        self.setMinimumWidth(380)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.username = QLineEdit()
        self.full_name = QLineEdit()
        self.role = QComboBox()
        self.role.addItems(ROLES)
        self.active = QCheckBox("Active")
        self.active.setChecked(True)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("User Name", self.username)
        form.addRow("Full Name", self.full_name)
        form.addRow("Role", self.role)
        form.addRow("", self.active)
        form.addRow("Password", self.password)
        form.addRow("Confirm Password", self.confirm)
        row = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(close)
        form.addRow(row)

        self.employee_id = None
        if rec_id:
            u = db().fetch_one("SELECT * FROM users WHERE id = %s", (rec_id,))
            self.username.setText(u["username"])
            self.full_name.setText(u["full_name"] or "")
            self.role.setCurrentText(u["role"])
            self.active.setChecked(u["is_active"])
            self.employee_id = u["employee_id"]
            self.password.setPlaceholderText("Leave blank to keep current password")
            self.confirm.setPlaceholderText("Leave blank to keep current password")

    def save(self):
        username = self.username.text().strip()
        if not username:
            error(self, "User name is required.")
            return
        pw, cpw = self.password.text(), self.confirm.text()
        if not self.rec_id and not pw:
            error(self, "Password is required for a new user.")
            return
        if pw != cpw:
            error(self, "Password and Confirm Password do not match.")
            return
        full_name = self.full_name.text().strip()
        if not self.rec_id and not full_name:
            error(self, "Full name is required for a new user.")
            return
        role = self.role.currentText()
        active = self.active.isChecked()
        try:
            if self.rec_id:
                with db().transaction() as cur:
                    if pw:
                        cur.execute(
                            """UPDATE users SET username=%s, full_name=%s, role=%s,
                                   is_active=%s, password_hash=%s WHERE id=%s""",
                            (username, full_name, role, active, hash_pw(pw), self.rec_id))
                    else:
                        cur.execute(
                            """UPDATE users SET username=%s, full_name=%s, role=%s,
                                   is_active=%s WHERE id=%s""",
                            (username, full_name, role, active, self.rec_id))
                    if self.employee_id:
                        cur.execute("UPDATE employees SET name=%s WHERE id=%s",
                                    (full_name, self.employee_id))
            else:
                emp_code = db().next_code("employees")
                with db().transaction() as cur:
                    cur.execute(
                        "INSERT INTO employees (code, name) VALUES (%s,%s) RETURNING id",
                        (emp_code, full_name))
                    employee_id = cur.fetchone()["id"]
                    cur.execute(
                        """INSERT INTO users (username, full_name, role, is_active,
                               password_hash, employee_id) VALUES (%s,%s,%s,%s,%s,%s)""",
                        (username, full_name, role, active, hash_pw(pw), employee_id))
        except Exception as exc:
            db().conn.rollback()
            error(self, f"Cannot save user:\n{exc}")
            return
        self.accept()


class UsersDialog(ListDialog):
    title = "User Management"
    headers = ["User Name", "Full Name", "Role", "Active"]

    def __init__(self, current_user: dict, parent=None):
        self.current_user = current_user
        super().__init__(parent)

    def load_rows(self, search):
        rows = db().fetch_all(
            """SELECT id, username, full_name, role, is_active FROM users
               WHERE username ILIKE %s OR full_name ILIKE %s ORDER BY username""",
            (f"%{search}%", f"%{search}%"))
        return [(r["id"], r["username"], r["full_name"], r["role"],
                 "Yes" if r["is_active"] else "No") for r in rows]

    def open_form(self, rec_id=None):
        return bool(UserForm(rec_id, self).exec())

    def on_delete(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a record first.")
            return
        if rec_id == self.current_user["id"]:
            error(self, "You cannot delete the account you are logged in with.")
            return
        if not confirm(self, "Delete the selected user?"):
            return
        try:
            db().execute("DELETE FROM users WHERE id = %s", (rec_id,))
        except Exception as exc:
            db().conn.rollback()
            error(self, f"Cannot delete:\n{exc}")
            return
        self.reload()


class ChangePasswordDialog(QDialog):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(360)
        self.setStyleSheet(DIALOG_QSS)
        form = QFormLayout(self)
        self.old = QLineEdit()
        self.old.setEchoMode(QLineEdit.EchoMode.Password)
        self.new = QLineEdit()
        self.new.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Current Password", self.old)
        form.addRow("New Password", self.new)
        form.addRow("Confirm New Password", self.confirm)
        row = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(close)
        form.addRow(row)

    def save(self):
        cur = db().fetch_one("SELECT password_hash FROM users WHERE id = %s", (self.user["id"],))
        if not cur or cur["password_hash"] != hash_pw(self.old.text()):
            error(self, "Current password is incorrect.")
            return
        if not self.new.text():
            error(self, "New password is required.")
            return
        if self.new.text() != self.confirm.text():
            error(self, "New password and confirmation do not match.")
            return
        db().execute("UPDATE users SET password_hash = %s WHERE id = %s",
                     (hash_pw(self.new.text()), self.user["id"]))
        info(self, "Password changed successfully.")
        self.accept()


class RolesDialog(QDialog):
    """Editable permission matrix: which top-level menus each role can access.
    Admin always has full access (locked, not editable). Settings and About
    stay visible to everyone regardless of this matrix."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Roles and Permissions")
        self.setMinimumSize(560, 360)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Choose which menus each role can access. Admin always has full access.\n"
            "Settings and About stay available to every logged-in user."))

        self.table = QTableWidget(len(MENU_KEYS), len(ROLES))
        self.table.setHorizontalHeaderLabels(ROLES)
        self.table.setVerticalHeaderLabels(MENU_KEYS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self._items: dict[tuple[str, str], QTableWidgetItem] = {}
        current = {role: (set(MENU_KEYS) if role == "Admin" else get_role_permissions(role))
                   for role in ROLES}
        for r, key in enumerate(MENU_KEYS):
            for c, role in enumerate(ROLES):
                item = QTableWidgetItem()
                checked = key in current[role]
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                if role == "Admin":
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                else:
                    item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, c, item)
                self._items[(key, role)] = item
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(close)
        lay.addLayout(row)

    def save(self):
        for role in ROLES:
            if role == "Admin":
                continue
            keys = {key for key in MENU_KEYS
                    if self._items[(key, role)].checkState() == Qt.CheckState.Checked}
            set_role_permissions(role, keys)
        info(self, "Permissions saved. Affected users must log out and back in "
                   "for the change to take effect.")
        self.accept()
