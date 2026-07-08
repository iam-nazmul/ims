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

    from .qt import QApplication, QMessageBox, QColor
    app = QApplication(sys.argv)
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

    try:
        from .db import db
        db()
    except Exception as exc:
        QMessageBox.critical(
            None, "IMS",
            f"Cannot connect to PostgreSQL:\n{exc}\n\n"
            "Create the database with:  python -m ims --initdb\n"
            "or set IMS_DATABASE_URL, e.g. 'dbname=ims_db user=postgres'.")
        return 1

    from .login import LoginDialog
    from .main_window import MainWindow

    while True:
        login = LoginDialog()
        if not login.exec():
            return 0
        window = MainWindow(login.user)
        window.showMaximized()
        app.exec()
        if not window.logout_requested:
            return 0


if __name__ == "__main__":
    sys.exit(main())
