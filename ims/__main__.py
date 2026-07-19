"""Entry point: `python -m ims` (or `python -m ims --initdb` to load the schema)."""

from __future__ import annotations

import os
import subprocess
import sys


def initdb() -> int:
    """Load db_schema.sql into the ims_db database using psql."""
    schema = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "db_schema.sql")
    dbname = os.environ.get("IMS_DBNAME", "ims_db")
    subprocess.run(["createdb", dbname], check=False)
    return subprocess.run(["psql", "-d", dbname, "-v", "ON_ERROR_STOP=1", "-f", schema]).returncode


def main() -> int:
    if "--initdb" in sys.argv:
        return initdb()

    from .qt import QApplication, QMessageBox, QColor, QIcon
    app = QApplication(sys.argv)
    icon = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "media", "icons", "appicon.png")
    app.setWindowIcon(QIcon(icon))
    # Force a light look so the OS dark theme never bleeds into the WinForms-style UI.
    app.setStyle("Fusion")
    palette = app.style().standardPalette()
    from .qt import Qt
    for role, color in [("Window", "#ece9d8"), ("WindowText", "#000000"),
                        ("Base", "#ffffff"), ("AlternateBase", "#eaf1fb"),
                        ("Text", "#000000"), ("Button", "#e8eef7"),
                        ("ButtonText", "#10243c"), ("ToolTipBase", "#ffffdc"),
                        ("ToolTipText", "#000000"),
                        ("Highlight", "#316ac5"), ("HighlightedText", "#ffffff")]:
        palette.setColor(getattr(palette.ColorRole, role), QColor(color))
    app.setPalette(palette)

    from .bootstrap import ensure_database, frozen
    try:
        ensure_database()
        from .db import db
        db()
    except Exception as exc:
        hint = ("Try restarting the application or your computer."
                if frozen() else
                "Create the database with:  python -m ims --initdb\n"
                "or set IMS_DATABASE_URL, e.g. 'dbname=ims_db user=postgres'.")
        QMessageBox.critical(
            None, "IMS", f"Cannot start the database:\n{exc}\n\n{hint}")
        return 1

    from .login import LoginDialog
    from .main_window import MainWindow

    def select_startup_company() -> bool:
        """Point the session at the default company (or any existing one)."""
        from .db import db, set_current_company
        cid = db().scalar("SELECT default_company_id FROM system_info WHERE id = 1")
        if cid is None:
            cid = db().scalar("SELECT id FROM companies ORDER BY id LIMIT 1")
        if cid is None:
            QMessageBox.critical(
                None, "IMS",
                "No company found. Load the schema with:  python -m ims --initdb")
            return False
        set_current_company(cid)
        return True

    while True:
        login = LoginDialog()
        if not login.exec():
            return 0
        if not select_startup_company():
            return 1
        window = MainWindow(login.user)
        window.showMaximized()
        app.exec()
        if not window.logout_requested:
            return 0


if __name__ == "__main__":
    sys.exit(main())
