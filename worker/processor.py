"""Processing claimed jobs.

``process_next`` is what the worker loop calls on every poll: it claims one pending
job and processes it, and reports whether there was anything to do.

``process_job`` is a skeleton placeholder that changes nothing; the ticket "Implement
atomic claiming and job processing in the worker" fills it in.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import claim


def process_job(conn: sqlite3.Connection, job: dict[str, Any]) -> None:
    """Run the job's analysis and store the outcome.

    Success sets ``status='done'`` and ``result``; any failure sets
    ``status='failed'`` and a short, readable ``error`` that never quotes the text.
    ``updated_at`` is refreshed either way.
    """
    return None


def process_next(conn: sqlite3.Connection) -> bool:
    """Claim and process the next pending job.

    Returns ``True`` when a job was processed, ``False`` when none was pending.
    """
    job = claim.claim_next_job(conn)
    if job is None:
        return False
    process_job(conn, job)
    return True
