"""Embedded PostgreSQL for packaged builds.

Installers bundle a private PostgreSQL under <bundle>/pgsql. On startup
ensure_database() initializes a cluster in the per-user data directory
(outside the install dir, so upgrades/uninstalls never touch it), starts
the server on 127.0.0.1, loads db_schema.sql on first run and exports
IMS_DATABASE_URL for db.py. On a dev checkout (no pgsql dir) it is a no-op.
"""

from __future__ import annotations

import atexit
import os
import subprocess
import sys

PG_PORT = int(os.environ.get("IMS_PG_PORT", "5455"))
PG_USER = "ims"
DB_NAME = "ims_db"

# Keep console windows of child processes (initdb, pg_ctl, pg_dump...) hidden
# when running as a windowed exe.
SUBPROCESS_FLAGS = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> str:
    """Read-only bundled files: db_schema.sql, media/, pgsql/. Repo root in dev."""
    if frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_root() -> str:
    """Per-user writable directory that survives upgrades and uninstalls."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "IMS")
    os.makedirs(path, exist_ok=True)
    return path


def media_root() -> str:
    """Base dir for user-added files (product images): repo in dev, data dir frozen."""
    return data_root() if frozen() else resource_root()


def pg_home() -> str:
    return os.environ.get("IMS_PGSQL_DIR") or os.path.join(resource_root(), "pgsql")


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True,
                          creationflags=SUBPROCESS_FLAGS, **kw)


def _fail(step: str, result: subprocess.CompletedProcess, log: str | None = None):
    detail = (result.stderr or result.stdout or "").strip()
    if log and os.path.exists(log):
        with open(log, errors="replace") as f:
            detail += "\n" + "".join(f.readlines()[-15:])
    raise RuntimeError(f"{step} failed:\n{detail.strip()}")


def ensure_database():
    """Start (initializing if needed) the bundled PostgreSQL and point db.py at it."""
    bin_dir = os.path.join(pg_home(), "bin")
    if not os.path.isdir(bin_dir):
        return  # dev checkout / system PostgreSQL
    # Also puts pg_dump/psql on PATH for settings.py backup/restore.
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    if os.environ.get("IMS_DATABASE_URL"):
        return

    pg_ctl = os.path.join(bin_dir, "pg_ctl")
    datadir = os.path.join(data_root(), "pgdata")
    log = os.path.join(data_root(), "postgres.log")

    if not os.path.exists(os.path.join(datadir, "PG_VERSION")):
        r = _run([os.path.join(bin_dir, "initdb"), "-D", datadir, "-U", PG_USER,
                  "-A", "trust", "-E", "UTF8", "--locale=C"])
        if r.returncode != 0:
            _fail("Database initialization (initdb)", r)

    if _run([pg_ctl, "status", "-D", datadir]).returncode != 0:
        # TCP only: every client (psycopg2, psql, pg_dump) connects to 127.0.0.1.
        opts = f"-p {PG_PORT} -c listen_addresses=127.0.0.1"
        if sys.platform != "win32":  # Windows builds already default to no socket
            opts += " -c unix_socket_directories=''"
        r = _run([pg_ctl, "start", "-w", "-D", datadir, "-l", log, "-o", opts])
        if r.returncode != 0:
            _fail("Database server startup", r, log)
        atexit.register(lambda: _run([pg_ctl, "stop", "-D", datadir, "-m", "fast", "-w"]))

    dsn = f"host=127.0.0.1 port={PG_PORT} user={PG_USER} dbname={DB_NAME}"
    import psycopg2
    conn = psycopg2.connect(f"host=127.0.0.1 port={PG_PORT} user={PG_USER} dbname=postgres")
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            fresh = cur.fetchone() is None
            if fresh:
                cur.execute(f"CREATE DATABASE {DB_NAME}")
        if fresh:
            schema = os.path.join(resource_root(), "db_schema.sql")
            r = _run([os.path.join(bin_dir, "psql"), "-v", "ON_ERROR_STOP=1", "-q",
                      "-f", schema, dsn])
            if r.returncode != 0:
                with conn.cursor() as cur:
                    cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
                _fail("Loading db_schema.sql", r)
    finally:
        conn.close()
    os.environ["IMS_DATABASE_URL"] = dsn
