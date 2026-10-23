"""Shared fixtures for the worker tests.

Every test gets its own SQLite file under pytest's ``tmp_path``; nothing is written
into the repository tree.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path

import db
import pytest

# The jobs schema as the sprint contract defines it. The API's ``init_schema`` owns
# the real one; the worker only ever reads and updates this table.
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


def _create_schema(path: str | Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def create_schema() -> Callable[[str | Path], None]:
    """A function that creates the jobs schema in the SQLite file at the given path."""
    return _create_schema


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    """Path (as str) of a fresh SQLite file that already holds the jobs schema."""
    path = tmp_path / "jobs.db"
    _create_schema(path)
    return str(path)


@pytest.fixture
def db_conn(tmp_db: str) -> Iterator[sqlite3.Connection]:
    """A worker connection (``db.get_connection``) to ``tmp_db``, closed afterwards."""
    conn = db.get_connection(tmp_db)
    try:
        yield conn
    finally:
        conn.close()
