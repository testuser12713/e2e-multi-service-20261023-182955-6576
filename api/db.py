"""SQLite access for the API.

API and worker share one SQLite file (``DATABASE_PATH``). Every connection runs in
WAL mode with a busy timeout so the two processes can read and write concurrently.
All statements in this service are parameterized; nothing user-supplied is ever
formatted into SQL.
"""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

# How long a statement waits for a lock held by the other process before failing.
BUSY_TIMEOUT_MS = 5000

# Used when DATABASE_PATH is not set: <repo>/data/jobs.db, the same file the
# relative value "../data/jobs.db" names when the API is started inside api/.
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    analysis TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_id ON jobs (status, id);
"""


def get_database_path() -> Path:
    """Return the database file named by DATABASE_PATH, or the default location.

    Read on every call (never at import time), so a missing variable cannot keep the
    process from starting. A relative path is resolved against the working directory.
    """
    raw = os.environ.get("DATABASE_PATH", "").strip()
    return Path(raw) if raw else DEFAULT_DATABASE_PATH


def get_connection(path: str | os.PathLike[str]) -> sqlite3.Connection:
    """Open a connection to the SQLite file at ``path`` in WAL mode with a busy timeout.

    Rows come back as ``sqlite3.Row``. ``check_same_thread`` is off because FastAPI may
    open, use and close one request's connection on different threadpool threads; a
    connection is still never shared between requests.
    """
    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000, check_same_thread=False)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        # Same value as BUSY_TIMEOUT_MS; PRAGMA statements take no bound parameters.
        conn.execute("PRAGMA busy_timeout = 5000")
    except sqlite3.Error:
        conn.close()
        raise
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the jobs table and its (status, id) index if they do not exist yet."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, closed afterwards.

    Uses the path the application resolved (and created the schema at) on startup.
    """
    path = getattr(request.app.state, "database_path", None) or get_database_path()
    conn = get_connection(path)
    try:
        yield conn
    finally:
        conn.close()


# Annotated dependency shared by every route that needs the database.
DbConnection = Annotated[sqlite3.Connection, Depends(get_db)]
