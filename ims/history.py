"""Admin-only audit trail viewer (History -> Log).

Every create/edit/delete in the application is captured by database triggers
into audit_log (see migrate_audit_log.sql); this dialog lists those entries
and shows field-by-field details for a selected one.
"""

from __future__ import annotations

from .qt import *
from .db import db
from .widgets import DIALOG_QSS, SearchBar, DataTable, info

ACTION_LABELS = {"INSERT": "Create", "UPDATE": "Edit", "DELETE": "Delete"}

# First matching field becomes the "Record" label shown in the grid.
LABEL_FIELDS = ("name", "model_name", "invoice_no", "return_no", "damage_no",
                "voucher_no", "receipt_no", "tran_no", "username", "full_name",
                "purpose", "description", "code")


def _record_label(row: dict) -> str:
    data = row.get("new_data") or row.get("old_data") or {}
    for f in LABEL_FIELDS:
        if data.get(f):
            return str(data[f])
    return "" if row.get("record_id") is None else f"#{row['record_id']}"


def _changed_fields(row: dict) -> list[str]:
    old, new = row.get("old_data") or {}, row.get("new_data") or {}
    return [k for k in new if old.get(k) != new.get(k)]


def _section(table_name: str) -> str:
    return table_name.replace("_", " ").title()


class HistoryDialog(QDialog):
    """Search/filter over the audit log; double-click a row for details."""

    LIMIT = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activity Log")
        self.setMinimumSize(980, 540)
        self.setStyleSheet(DIALOG_QSS)
        self._rows: list[dict] = []

        outer = QHBoxLayout(self)
        left = QVBoxLayout()

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Action"))
        self.action_combo = QComboBox()
        self.action_combo.addItem("All", None)
        for op, label in ACTION_LABELS.items():
            self.action_combo.addItem(label, op)
        self.action_combo.currentIndexChanged.connect(lambda *_: self.reload())
        filters.addWidget(self.action_combo)
        filters.addSpacing(12)
        filters.addWidget(QLabel("Section"))
        self.table_combo = QComboBox()
        self.table_combo.addItem("All", None)
        for r in db().fetch_all(
                "SELECT DISTINCT table_name FROM audit_log ORDER BY table_name"):
            self.table_combo.addItem(_section(r["table_name"]), r["table_name"])
        self.table_combo.currentIndexChanged.connect(lambda *_: self.reload())
        filters.addWidget(self.table_combo, 1)
        left.addLayout(filters)

        self.search = SearchBar()
        self.search.searched.connect(lambda *_: self.reload())
        left.addWidget(self.search)

        self.table = DataTable(["Date & Time", "User", "Action", "Section",
                                "Record", "Changes"])
        self.table.doubleClicked.connect(lambda *_: self.show_details())
        left.addWidget(self.table, 1)
        outer.addLayout(left, 1)

        side = QVBoxLayout()
        details = QPushButton("Details")
        details.setMinimumWidth(90)
        details.clicked.connect(self.show_details)
        side.addWidget(details)
        close = QPushButton("Close")
        close.setMinimumWidth(90)
        close.clicked.connect(self.accept)
        side.addWidget(close)
        side.addStretch(1)
        self.total_label = QLabel("Total : 0")
        self.total_label.setStyleSheet("font-weight: bold;")
        side.addWidget(self.total_label)
        outer.addLayout(side)

        self.reload()

    def reload(self):
        wheres, params = [], []
        if op := self.action_combo.currentData():
            wheres.append("operation = %s")
            params.append(op)
        if tbl := self.table_combo.currentData():
            wheres.append("table_name = %s")
            params.append(tbl)
        if s := self.search.edit.text().strip():
            like = f"%{s}%"
            wheres.append("(username ILIKE %s OR table_name ILIKE %s "
                          "OR old_data::text ILIKE %s OR new_data::text ILIKE %s)")
            params += [like] * 4
        where = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        self._rows = db().fetch_all(
            f"""SELECT id, logged_at, username, table_name, operation, record_id,
                       old_data, new_data
                FROM audit_log {where}
                ORDER BY id DESC LIMIT {self.LIMIT}""", tuple(params))

        grid = []
        for r in self._rows:
            if r["operation"] == "UPDATE":
                changed = _changed_fields(r)
                changes = ", ".join(changed[:4]) + (" ..." if len(changed) > 4 else "")
            else:
                changes = ""
            grid.append((r["id"], f"{r['logged_at']:%d %b %Y %H:%M:%S}",
                         r["username"] or "(unknown)",
                         ACTION_LABELS.get(r["operation"], r["operation"]),
                         _section(r["table_name"]), _record_label(r), changes))
        self.table.set_rows(grid)
        self.total_label.setText(f"Total : {len(grid)}")

    def show_details(self):
        log_id = self.table.current_id()
        row = next((r for r in self._rows if r["id"] == log_id), None)
        if row is None:
            info(self, "Select a log entry first.")
            return
        LogDetailsDialog(row, self).exec()


class LogDetailsDialog(QDialog):
    """Field-by-field view of one audit entry (old vs new values)."""

    def __init__(self, row: dict, parent=None):
        super().__init__(parent)
        action = ACTION_LABELS.get(row["operation"], row["operation"])
        self.setWindowTitle(f"Log Details — {action}")
        self.setMinimumSize(560, 480)
        self.setStyleSheet(DIALOG_QSS)

        lay = QVBoxLayout(self)
        head = QLabel(
            f"<b>{action}</b> in <b>{_section(row['table_name'])}</b> "
            f"by <b>{row['username'] or '(unknown)'}</b><br>"
            f"{row['logged_at']:%d %b %Y %H:%M:%S} — Record: {_record_label(row)}")
        lay.addWidget(head)

        old, new = row.get("old_data") or {}, row.get("new_data") or {}
        if row["operation"] == "UPDATE":
            table = DataTable(["Field", "Old Value", "New Value"])
            rows = [(k, k, _fmt(old.get(k)), _fmt(new.get(k)))
                    for k in _changed_fields(row)]
        elif row["operation"] == "INSERT":
            table = DataTable(["Field", "Value"])
            rows = [(k, k, _fmt(v)) for k, v in new.items()]
        else:
            table = DataTable(["Field", "Deleted Value"])
            rows = [(k, k, _fmt(v)) for k, v in old.items()]
        table.set_rows(rows)
        lay.addWidget(table, 1)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)


def _fmt(v) -> str:
    return "" if v is None else str(v)
