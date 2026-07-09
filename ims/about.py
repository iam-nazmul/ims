"""About menu: application information and help."""

from __future__ import annotations

from .qt import *
from .db import db
from .widgets import DIALOG_QSS

HELP_HTML = """
<h2>Getting Started</h2>
<p>Log in, then use the menu bar or the colored shortcut buttons on the dashboard
to open each area of the application. The menus you see depend on your assigned
role — ask an Admin if a menu you need is missing.</p>

<h3>Basic</h3>
<p>Set up System Information, Companies, Categories, Products, Banks and Card
Types. Do this before entering purchases or sales, since transactions reference
these records.</p>

<h3>Employee / Customer and Supplier</h3>
<p>Maintain employee records, and customer/supplier accounts with running dues.</p>

<h3>Inventory Management</h3>
<p>Record Purchase Orders to bring stock in; Sales Orders or Credit Sales to sell
it. Use Sales Return, Purchase Return or Damage Product to adjust stock afterward.</p>

<h3>Account Management</h3>
<p>Track Cash Collection/Delivery, Bank Transactions, Investments, Income and
Expense.</p>

<h3>MIS Report</h3>
<p>Print daily/monthly/yearly sales and purchase reports, stock and dues reports,
and the combined Summary Report.</p>

<h3>Settings</h3>
<p>Change your password, and (Admin only) manage users, role permissions, and
back up or restore the database.</p>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.setMinimumSize(560, 480)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(HELP_HTML)
        lay.addWidget(text, 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)


SUPPORT_CONTACT = {
    "name": "MD. NAZMUL HOSSAIN",
    "phone": "+8801761777748",
    "email": "nazmul.cse48@gmail.com",
}


class ContactSupportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contact Support")
        self.setFixedWidth(380)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)

        title = QLabel("Need help with IMS?")
        title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        lay.addWidget(title)

        c = SUPPORT_CONTACT
        info = QLabel(
            f"<b>{c['name']}</b><br>Phone: {c['phone']}<br>Email: {c['email']}")
        info.setWordWrap(True)
        lay.addWidget(info)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About IMS")
        self.setFixedWidth(420)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)

        title = QLabel("IMS — Inventory Management Software")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title.setWordWrap(True)
        lay.addWidget(title)

        si = db().fetch_one("SELECT * FROM system_info WHERE id = 1") or {}
        lines = [
            f"<b>{si.get('company_name', '')}</b>" if si.get("company_name") else "",
            si.get("company_address", "") or "",
            f"Phone: {si['telephone_no']}" if si.get("telephone_no") else "",
            f"Email: {si['email_address']}" if si.get("email_address") else "",
            f"Web: {si['web_address']}" if si.get("web_address") else "",
        ]
        info = QLabel("<br>".join(line for line in lines if line))
        info.setWordWrap(True)
        lay.addWidget(info)

        credit = QLabel("Developed By © SOFTIFE")
        credit.setStyleSheet("margin-top: 10px; font-style: italic;")
        lay.addWidget(credit)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
