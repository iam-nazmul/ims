"""Shared UI building blocks: list dialogs, lookup fields, print preview."""

from __future__ import annotations

from datetime import date

from .qt import *
from .db import db, money

DIALOG_QSS = """
QDialog { background-color: #b8cce4; }
QLabel, QGroupBox, QCheckBox, QRadioButton, QTabBar::tab { color: #10243c; }
QGroupBox { font-weight: bold; border: 1px solid #7f9db9; border-radius: 3px;
            margin-top: 8px; padding-top: 6px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; }
QTableWidget { background: white; alternate-background-color: #eaf1fb;
               color: black; gridline-color: #c0c0c0;
               selection-background-color: #316ac5; selection-color: white; }
QTableWidget::item { background-color: white; color: black; }
QTableWidget::item:alternate { background-color: #eaf1fb; }
QTableWidget::item:selected { background-color: #316ac5; color: white; }
QHeaderView::section { background: #dbe5f1; color: #10243c; padding: 3px;
                       border: 1px solid #aab8c9; }
QPushButton { background: #e8eef7; color: #10243c; border: 1px solid #7f9db9;
              padding: 5px 14px; border-radius: 2px; }
QPushButton:hover { background: #d2e0f0; }
QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit {
    background: white; color: black; border: 1px solid #7f9db9; padding: 2px; }
QComboBox QAbstractItemView { background: white; color: black; }
QCalendarWidget QWidget { color: black; }
QLineEdit:read-only, QDoubleSpinBox:read-only { background: #f5c8cf; }
QTabWidget::pane { border: 1px solid #7f9db9; background: #b8cce4; }
QTabBar::tab { background: #dbe5f1; padding: 5px 14px; border: 1px solid #7f9db9; }
QTabBar::tab:selected { background: #b8cce4; font-weight: bold; }
"""


def magnifier_icon(size: int = 16, color: str = "#10243c") -> QIcon:
    """Magnifying-glass icon: theme icon if available, else drawn by hand."""
    icon = QIcon.fromTheme("edit-find")
    if not icon.isNull():
        return icon
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), max(2.0, size / 8)))
    d = round(size * 0.55)
    p.drawEllipse(2, 2, d, d)
    off = 2 + round(d * 0.85)
    p.drawLine(off, off, size - 2, size - 2)
    p.end()
    return QIcon(pm)


def dedit(d: date | None = None) -> QDateEdit:
    w = QDateEdit()
    w.setCalendarPopup(True)
    w.setDisplayFormat("dd MMM yyyy")
    dd = d or date.today()
    w.setDate(QDate(dd.year, dd.month, dd.day))
    return w


def pydate(w: QDateEdit) -> date:
    q = w.date()
    return date(q.year(), q.month(), q.day())


def dspin(maximum: float = 999999999, decimals: int = 2, read_only: bool = False) -> QDoubleSpinBox:
    w = QDoubleSpinBox()
    w.setRange(-maximum, maximum)
    w.setDecimals(decimals)
    w.setGroupSeparatorShown(True)
    if read_only:
        w.setReadOnly(True)
        w.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
    return w


def info(parent, msg: str):
    QMessageBox.information(parent, "IMS", msg)


def error(parent, msg: str):
    QMessageBox.critical(parent, "IMS", msg)


def confirm(parent, msg: str) -> bool:
    b = QMessageBox.question(parent, "IMS", msg)
    return b == QMessageBox.StandardButton.Yes


class SearchBar(QWidget):
    """'Enter text to search...' + Find + Clear, like every list form in the video."""
    searched = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Enter text to search...")
        self.edit.returnPressed.connect(self._find)
        find = QPushButton("Find")
        find.clicked.connect(self._find)
        clear = QPushButton("Clear")
        clear.clicked.connect(self._clear)
        lay.addWidget(self.edit, 1)
        lay.addWidget(find)
        lay.addWidget(clear)

    def _find(self):
        self.searched.emit(self.edit.text().strip())

    def _clear(self):
        self.edit.clear()
        self.searched.emit("")


class DataTable(QTableWidget):
    """Read-only, row-select table; keeps a hidden record id per row."""

    def __init__(self, headers: list[str], parent=None):
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self._ids: list = []

    def set_rows(self, rows: list[tuple]):
        """rows: (record_id, cell, cell, ...). Numeric cells are right-aligned."""
        self.setRowCount(0)
        self._ids = []
        for row in rows:
            r = self.rowCount()
            self.insertRow(r)
            self._ids.append(row[0])
            for c, val in enumerate(row[1:]):
                it = QTableWidgetItem("" if val is None else str(val))
                if isinstance(val, (int, float)) or (
                        isinstance(val, str) and val.replace(",", "").replace(".", "").replace("-", "").isdigit()):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.setItem(r, c, it)
        self.resizeColumnsToContents()

    def current_id(self):
        r = self.currentRow()
        return self._ids[r] if 0 <= r < len(self._ids) else None


class ListDialog(QDialog):
    """Base for every list window: search bar, grid, New/Edit/Delete/Close column."""

    title = "List"
    headers: list[str] = []
    buttons = ("New", "Edit", "Delete", "Close")   # subset/order per subclass

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.title)
        self.setMinimumSize(760, 480)
        self.setStyleSheet(DIALOG_QSS)

        outer = QHBoxLayout(self)
        left = QVBoxLayout()
        self.search = SearchBar()
        self.search.searched.connect(self.reload)
        left.addWidget(self.search)
        self.table = DataTable(self.headers)
        self.table.doubleClicked.connect(lambda *_: self.on_edit())
        left.addWidget(self.table, 1)
        outer.addLayout(left, 1)

        side = QVBoxLayout()
        handlers = {"New": self.on_new, "Edit": self.on_edit, "Delete": self.on_delete,
                    "Invoice": self.on_invoice, "Return": self.on_return, "Close": self.accept}
        for name in self.buttons:
            b = QPushButton(name)
            b.setMinimumWidth(90)
            b.clicked.connect(handlers[name])
            side.addWidget(b)
        side.addStretch(1)
        self.total_label = QLabel("Total : 0")
        self.total_label.setStyleSheet("font-weight: bold;")
        side.addWidget(self.total_label)
        outer.addLayout(side)

        self.reload("")

    # -- subclass API -------------------------------------------------------
    def load_rows(self, search: str) -> list[tuple]:
        raise NotImplementedError

    def open_form(self, rec_id=None) -> bool:
        raise NotImplementedError

    def delete_sql(self) -> str | None:
        return None

    def on_invoice(self):
        pass

    def on_return(self):
        pass

    # -- behavior -----------------------------------------------------------
    def reload(self, search: str | None = None):
        if search is None:
            search = self.search.edit.text().strip()
        rows = self.load_rows(search)
        self.table.set_rows(rows)
        self.total_label.setText(f"Total : {len(rows)}")

    def on_new(self):
        if self.open_form(None):
            self.reload()

    def on_edit(self):
        rec_id = self.table.current_id()
        if rec_id is None:
            info(self, "Select a record first.")
            return
        if self.open_form(rec_id):
            self.reload()

    def on_delete(self):
        rec_id = self.table.current_id()
        sql = self.delete_sql()
        if rec_id is None or not sql:
            info(self, "Select a record first.")
            return
        if not confirm(self, "Delete the selected record?"):
            return
        try:
            db().execute(sql, (rec_id,))
        except Exception as exc:
            db().conn.rollback()
            error(self, f"Cannot delete:\n{exc}")
            return
        self.reload()


class PickerDialog(QDialog):
    """Generic search-and-pick popup used by the magnifier buttons."""

    def __init__(self, title: str, headers: list[str], sql: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(560, 420)
        self.setStyleSheet(DIALOG_QSS)
        self.sql = sql
        self.selected: dict | None = None
        self._rows: list[dict] = []

        lay = QVBoxLayout(self)
        self.search = SearchBar()
        self.search.searched.connect(self.reload)
        lay.addWidget(self.search)
        self.table = DataTable(headers)
        self.table.doubleClicked.connect(lambda *_: self._choose())
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        ok = QPushButton("Select")
        ok.clicked.connect(self._choose)
        cancel = QPushButton("Close")
        cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(ok)
        row.addWidget(cancel)
        lay.addLayout(row)
        self.reload("")

    def reload(self, search: str = ""):
        self._rows = db().fetch_all(self.sql, (f"%{search}%",) * self.sql.count("%s"))
        self.table.set_rows([tuple(r.values()) for r in self._rows])

    def _choose(self):
        r = self.table.currentRow()
        if 0 <= r < len(self._rows):
            self.selected = self._rows[r]
            self.accept()

    @staticmethod
    def pick(title, headers, sql, parent=None) -> dict | None:
        dlg = PickerDialog(title, headers, sql, parent)
        return dlg.selected if dlg.exec() else None


class LookupField(QWidget):
    """code box + magnifier button + name box (read-only), as in the video forms."""
    selected = Signal(dict)

    def __init__(self, title: str, headers: list[str], sql: str, parent=None):
        super().__init__(parent)
        self.title, self.headers, self.sql = title, headers, sql
        self.record: dict | None = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        self.code.setMaximumWidth(90)
        btn = QPushButton()
        btn.setIcon(magnifier_icon())
        btn.setToolTip("Search…")
        btn.setMaximumWidth(32)
        btn.clicked.connect(self.open_picker)
        self.name = QLineEdit()
        self.name.setReadOnly(True)
        lay.addWidget(self.code)
        lay.addWidget(btn)
        lay.addWidget(self.name, 1)

    def open_picker(self):
        rec = PickerDialog.pick(self.title, self.headers, self.sql, self)
        if rec:
            self.set_record(rec)

    def set_record(self, rec: dict | None):
        self.record = rec
        self.code.setText(str(rec.get("code", rec.get("id", ""))) if rec else "")
        self.name.setText(str(rec.get("name", "")) if rec else "")
        if rec:
            self.selected.emit(rec)

    def value(self):
        return self.record["id"] if self.record else None


# ---------------------------------------------------------------------------
# Reporting helpers

def company_header_html() -> str:
    si = db().fetch_one("SELECT * FROM system_info WHERE id = 1") or {}
    return (
        f"<div style='text-align:center'>"
        f"<h1 style='margin:0'>{si.get('company_name', '')}</h1>"
        f"<p style='margin:2px'>{si.get('company_address', '')}<br>"
        f"<b>Mobile: {si.get('telephone_no', '')}</b></p></div><hr>"
    )


def html_table(headers: list[str], rows: list[list], totals: list | None = None) -> str:
    head = "".join(f"<th style='border:1px solid #444;padding:4px;background:#dbe5f1'>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        tds = ""
        for v in row:
            align = "right" if isinstance(v, (int, float)) else "left"
            text = money(v) if isinstance(v, float) else ("" if v is None else str(v))
            tds += f"<td style='border:1px solid #666;padding:4px;text-align:{align}'>{text}</td>"
        body += f"<tr>{tds}</tr>"
    if totals:
        tds = ""
        for v in totals:
            text = money(v) if isinstance(v, float) else ("" if v is None else str(v))
            align = "right" if isinstance(v, float) else "left"
            tds += f"<td style='border:1px solid #666;padding:4px;font-weight:bold;text-align:{align}'>{text}</td>"
        body += f"<tr>{tds}</tr>"
    return f"<table width='100%' style='border-collapse:collapse;font-size:9pt'><tr>{head}</tr>{body}</table>"


def preview_html(parent, title: str, body_html: str):
    """Print-preview window, standing in for the Crystal-Reports viewer."""
    doc = QTextDocument()
    doc.setHtml(company_header_html()
                + f"<div style='text-align:center'><h3 style='border:1px solid #000;"
                  f"display:inline-block;padding:2px 20px'>{title}</h3></div>"
                + body_html
                + f"<p style='font-size:8pt'>Printed on {date.today():%d %b %Y}</p>")
    dlg = QPrintPreviewDialog(parent)
    dlg.setWindowTitle(title)
    dlg.paintRequested.connect(doc.print_)
    dlg.resize(1000, 700)
    dlg.exec()
