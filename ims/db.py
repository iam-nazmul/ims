"""PostgreSQL access layer. One shared connection, dict rows, small helpers."""

from __future__ import annotations

import os
from contextlib import contextmanager
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

DEFAULT_DSN = "dbname=ims_db"


class Database:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.environ.get("IMS_DATABASE_URL") or DEFAULT_DSN
        self.conn = psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: tuple = ()):
        row = self.fetch_one(sql, params)
        return next(iter(row.values())) if row else None

    def execute(self, sql: str, params: tuple = ()):
        """Run one statement and commit. Returns first row when RETURNING is used."""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone() if cur.description else None
        self.conn.commit()
        return row

    @contextmanager
    def transaction(self):
        """Multi-statement transaction: yields a cursor, commits on success."""
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def next_code(self, table: str, width: int = 5, column: str = "code") -> str:
        """Next zero-padded numeric code for a table ('00001', '00002', ...)."""
        val = self.scalar(
            f"SELECT COALESCE(MAX(NULLIF(regexp_replace({column}, '\\D', '', 'g'), '')::bigint), 0) + 1 FROM {table}"
        )
        return str(val).zfill(width)

    def next_serial(self, table: str) -> int:
        return int(self.scalar(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"))

    def close(self):
        self.conn.close()


_db: Database | None = None


def db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


def reset_connection():
    """Close the shared connection so the next db() call reconnects fresh."""
    global _db
    if _db is not None:
        _db.close()
        _db = None


def money(v) -> str:
    """Format a numeric as 1,234.56."""
    if v is None:
        v = 0
    return f"{Decimal(v):,.2f}"
