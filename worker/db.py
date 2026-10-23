"""SQLite access for the worker.

The worker shares one SQLite file with the API; both read its location from
``DATABASE_PATH``. The API owns the schema (``init_schema`` in ``api/db.py``): the
worker never creates tables, it waits until the ``jobs`` table exists and then works
against it.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from collections.abc import Callable

logger = logging.getLogger("worker.db")

DATABASE_PATH_ENV = "DATABASE_PATH"
SCHEMA_TABLE = "jobs"

# How long a statement waits for a lock held by the other process (API or a second
# worker) before it fails with "database is locked".
BUSY_TIMEOUT_MS = 5000
_BUSY_TIMEOUT_PRAGMA = "PRAGMA busy_timeout = 5000"

# Backoff while the schema is missing: the delay doubles from the first value up to
# the cap and then stays there, so a late API is noticed within a few seconds.
INITIAL_SCHEMA_DELAY_S = 0.5
MAX_SCHEMA_DELAY_S = 5.0


class ConfigError(RuntimeError):
    """The worker's configuration is missing or invalid; the message names the variable."""


def database_path_from_env() -> str:
    """Return ``DATABASE_PATH`` from the environment, or fail at once naming it.

    A relative path is resolved against the working directory, which is ``worker/``
    for the documented start command.
    """
    value = os.environ.get(DATABASE_PATH_ENV, "").strip()
    if not value:
        raise ConfigError(
            f"{DATABASE_PATH_ENV} is not set: point it at the SQLite file the API uses "
            "(RUN.json declares '../data/jobs.db' relative to worker/)"
        )
    return value


def get_connection(path: str | os.PathLike[str]) -> sqlite3.Connection:
    """Open the shared SQLite database at ``path``.

    Every connection runs in WAL mode with a busy timeout, so the API and one or more
    workers can read and write the same file concurrently. The connection is in
    autocommit mode (``isolation_level=None``): each statement commits on its own
    unless a transaction is opened explicitly with ``BEGIN`` / ``BEGIN IMMEDIATE``.
    Rows come back as ``sqlite3.Row`` (``dict(row)`` gives a plain dict).

    The parent directory is created when it is missing, so the worker can start
    before the API has created the database.
    """
    target = os.fspath(path)
    if not target.strip():
        raise ValueError("database path must not be empty")
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)

    conn = sqlite3.connect(target, timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None)
    try:
        conn.execute(_BUSY_TIMEOUT_PRAGMA)
        mode = conn.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            logger.warning("database refused WAL mode, journal mode is %s", mode)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        conn.close()
        raise
    return conn


def _schema_ready(conn: sqlite3.Connection) -> bool:
    """True when the ``jobs`` table exists; a database error counts as not ready."""
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (SCHEMA_TABLE,),
        ).fetchone()
    except sqlite3.Error as exc:
        logger.warning("database not readable yet: %s", exc)
        return False
    return row is not None


def wait_for_schema(
    conn: sqlite3.Connection,
    *,
    initial_delay: float = INITIAL_SCHEMA_DELAY_S,
    max_delay: float = MAX_SCHEMA_DELAY_S,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Block until the ``jobs`` table exists in the database behind ``conn``.

    Checks right away, then retries with a backoff that doubles from
    ``initial_delay`` and is capped at ``max_delay``. It waits as long as it takes
    (the API may start much later) and logs every wait; the log lines name only the
    table and the delay, never anything stored in a job.
    """
    if initial_delay <= 0 or max_delay < initial_delay:
        raise ValueError("backoff needs 0 < initial_delay <= max_delay")

    delay = initial_delay
    attempt = 0
    while not _schema_ready(conn):
        attempt += 1
        logger.info(
            "table '%s' does not exist yet (attempt %d); checking again in %.1fs",
            SCHEMA_TABLE,
            attempt,
            delay,
        )
        sleep(delay)
        delay = min(delay * 2, max_delay)
