# PyInstaller spec: builds dist/ims (onedir) on all platforms, plus IMS.app on macOS.
# Bundles db_schema.sql + media/, and packaging/pgsql/ (embedded PostgreSQL) when
# fetch_postgres.py has been run first.

import os
import sys

ROOT = os.path.dirname(SPECPATH)

datas = [
    (os.path.join(ROOT, "db_schema.sql"), "."),
    (os.path.join(ROOT, "migrate_multicompany.sql"), "."),
    (os.path.join(ROOT, "migrate_audit_log.sql"), "."),
    (os.path.join(ROOT, "media"), "media"),
]

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=[
        "ims." + m for m in [
            "about", "accounts", "basic", "bootstrap", "db", "history",
            "inventory", "login", "main_window", "people", "qt", "reports",
            "settings", "users", "widgets",
        ]
    ],
    excludes=["PyQt6", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

icon = None
if sys.platform == "win32":
    icon = os.path.join(SPECPATH, "icons", "ims.ico")
elif sys.platform == "darwin":
    icon = os.path.join(SPECPATH, "icons", "ims.icns")
if icon and not os.path.exists(icon):
    icon = None

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="ims",
    icon=icon,
    console=False,
    upx=False,
)

pgsql = os.path.join(SPECPATH, "pgsql")
extra_trees = [Tree(pgsql, prefix="pgsql")] if os.path.isdir(pgsql) else []

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    *extra_trees,
    name="ims",
    upx=False,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="IMS.app",
        icon=icon,
        bundle_identifier="com.glascutr.ims",
        info_plist={"NSHighResolutionCapable": True},
    )
