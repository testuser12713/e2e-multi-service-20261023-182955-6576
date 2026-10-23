"""Claiming the next pending job.

Several worker processes may poll the same database, so a claim must move exactly
one job from ``pending`` to ``running`` in one atomic step: no two workers may ever
receive the same job.

The claim is a single ``UPDATE ... WHERE id = (SELECT ...) RETURNING *`` run inside
``BEGIN IMMEDIATE``, so the write lock is taken before the oldest pending row is read.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

_CLAIM_SQL = """
UPDATE jobs
SET status = 'running', updated_at = ?
WHERE id = (SELECT id FROM jobs WHERE status = 'pending' ORDER BY id ASC LIMIT 1)
  AND status = 'pending'
RETURNING id, text, analysis, status, result, error, created_at, updated_at
"""


def utc_now() -> str:
    """Current time as an ISO 8601 UTC string."""
    return datetime.now(UTC).isoformat()


def claim_next_job(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """Atomically set the oldest ``pending`` job to ``running`` and return it as a dict.

    The dict has the ``jobs`` columns as keys. Returns ``None`` when no job is pending.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(_CLAIM_SQL, (utc_now(),)).fetchone()
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    if row is None:
        return None
    keys = ("id", "text", "analysis", "status", "result", "error", "created_at", "updated_at")
    return dict(zip(keys, tuple(row), strict=True))
