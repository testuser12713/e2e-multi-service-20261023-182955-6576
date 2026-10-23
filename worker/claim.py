"""Claiming the next pending job.

Several worker processes may poll the same database, so a claim must move exactly
one job from ``pending`` to ``running`` in one atomic step: no two workers may ever
receive the same job.

The body is a skeleton placeholder that claims nothing, so the worker loop runs idle;
the ticket "Implement atomic claiming and job processing in the worker" fills it in.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def claim_next_job(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """Atomically set the oldest ``pending`` job to ``running`` and return it as a dict.

    The dict has the ``jobs`` columns as keys. Returns ``None`` when no job is pending.
    """
    return None
