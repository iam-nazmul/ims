"""LogIn dialog, as in the video (User Name / Password, LogIn / Close)."""

from __future__ import annotations

import hashlib

from .qt import *
from .db import db
from .widgets import DIALOG_QSS, error


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LogIn")
        self.setFixedSize(380, 170)
        self.setStyleSheet(DIALOG_QSS)
        self.user: dict | None = None

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.returnPressed.connect(self.login)
        form.addRow("User Name", self.username)
        form.addRow("Password", self.password)
        lay.addLayout(form)
        row = QHBoxLayout()
        row.addStretch(1)
        btn = QPushButton("LogIn")
        btn.setDefault(True)
        btn.clicked.connect(self.login)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addWidget(btn)
        row.addWidget(close)
        lay.addLayout(row)

    def login(self):
        name = self.username.text().strip()
        pw_hash = hashlib.sha256(self.password.text().encode()).hexdigest()
        user = db().fetch_one(
            "SELECT * FROM users WHERE username = %s AND password_hash = %s",
            (name, pw_hash))
        if not user:
            error(self, "Invalid user name or password.")
            return
        if not user["is_active"]:
            error(self, "This account has been disabled. Contact an administrator.")
            return
        self.user = user
        self.accept()
