"""Settings menu: Backup / Restore Database."""

from __future__ import annotations

import subprocess
from datetime import date

from .qt import *
from .bootstrap import SUBPROCESS_FLAGS
from .db import db, reset_connection
from .widgets import DIALOG_QSS, info, error, confirm


class BackupDatabaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backup Database")
        self.setMinimumWidth(440)
        self.setStyleSheet(DIALOG_QSS)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Save a full copy of the database to a .sql file.\n"
            "The file can later be used to restore the database."))
        browse_row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setReadOnly(True)
        browse_row.addWidget(self.path, 1)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self.choose_path)
        browse_row.addWidget(browse)
        lay.addLayout(browse_row)

        row = QHBoxLayout()
        backup = QPushButton("Backup")
        backup.clicked.connect(self.run_backup)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(backup)
        row.addWidget(close)
        lay.addLayout(row)

    def choose_path(self):
        default = f"ims_backup_{date.today():%Y%m%d}.sql"
        path, _ = QFileDialog.getSaveFileName(self, "Backup Database", default, "SQL Files (*.sql)")
        if path:
            self.path.setText(path)

    def run_backup(self):
        path = self.path.text().strip()
        if not path:
            error(self, "Choose a destination file first.")
            return
        try:
            result = subprocess.run(
                ["pg_dump", "--no-owner", "--no-privileges", "--clean", "--if-exists",
                 "-f", path, db().dsn],
                capture_output=True, text=True, timeout=120, creationflags=SUBPROCESS_FLAGS)
        except FileNotFoundError:
            error(self, "pg_dump was not found. Make sure the PostgreSQL client tools are installed.")
            return
        except subprocess.TimeoutExpired:
            error(self, "Backup timed out.")
            return
        if result.returncode != 0:
            error(self, f"Backup failed:\n{result.stderr}")
            return
        info(self, f"Database backed up to:\n{path}")
        self.accept()


class RestoreDatabaseDialog(QDialog):
    """Overwrites the live database with the contents of a backup file.
    Destructive and irreversible, so it requires an explicit acknowledgement
    before the Restore button is even enabled."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore Database")
        self.setMinimumWidth(460)
        self.setStyleSheet(DIALOG_QSS)

        lay = QVBoxLayout(self)
        warn = QLabel(
            "Restoring will permanently ERASE all current data and replace it\n"
            "with the contents of the selected backup file. This cannot be undone.\n"
            "Make sure you have a current backup before continuing.")
        warn.setStyleSheet("color: #7a0000; font-weight: bold;")
        lay.addWidget(warn)

        browse_row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setReadOnly(True)
        browse_row.addWidget(self.path, 1)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self.choose_path)
        browse_row.addWidget(browse)
        lay.addLayout(browse_row)

        self.ack = QCheckBox("I understand this will permanently overwrite all current data.")
        self.ack.toggled.connect(self._update_enabled)
        lay.addWidget(self.ack)

        row = QHBoxLayout()
        self.restore_btn = QPushButton("Restore")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.run_restore)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(self.restore_btn)
        row.addWidget(close)
        lay.addLayout(row)

    def _update_enabled(self):
        self.restore_btn.setEnabled(self.ack.isChecked() and bool(self.path.text().strip()))

    def choose_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore Database", "", "SQL Files (*.sql)")
        if path:
            self.path.setText(path)
        self._update_enabled()

    def run_restore(self):
        path = self.path.text().strip()
        if not path:
            error(self, "Choose a backup file first.")
            return
        if not confirm(self, "This will permanently overwrite the current database with the "
                              "selected backup. This action cannot be undone.\n\nContinue?"):
            return
        try:
            result = subprocess.run(
                ["psql", "-v", "ON_ERROR_STOP=1", "-f", path, db().dsn],
                capture_output=True, text=True, timeout=120, creationflags=SUBPROCESS_FLAGS)
        except FileNotFoundError:
            error(self, "psql was not found. Make sure the PostgreSQL client tools are installed.")
            return
        except subprocess.TimeoutExpired:
            error(self, "Restore timed out. Another session may be holding a lock on the "
                        "database — close other IMS windows/instances and try again.")
            return
        reset_connection()
        if result.returncode != 0:
            error(self, f"Restore failed:\n{result.stderr}")
            return
        info(self, "Database restored successfully. The application will now log you out.")
        self.accept()
