import sqlite3

import click

from .config import DB_PATH


def get_db():
    """Open SQLite connection with WAL mode."""
    if not DB_PATH.exists():
        click.secho(f"✗ Database not found: {DB_PATH}", fg="red", err=True)
        click.secho("  Run: python tools/init_db.py", fg="yellow", err=True)
        raise SystemExit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn
