"""Processing claimed jobs.

``process_next`` is what the worker loop calls on every poll: it claims one pending
job and processes it, and reports whether there was anything to do.

``process_job`` stores the outcome. A failure is stored as a short message of our own
that never contains the exception's message, a traceback, a path or the job text.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

import analyses
import claim

logger = logging.getLogger("worker.processor")

_FINISH_SQL = "UPDATE jobs SET status = ?, result = ?, error = ?, updated_at = ? WHERE id = ?"


def failure_message(analysis: str, exc: BaseException) -> str:
    """A short readable error built only from our own words and the exception class."""
    if isinstance(exc, ValueError) and analysis not in analyses.ANALYSIS_KINDS:
        return "Unbekannte Analyse"
    return f"Analyse fehlgeschlagen ({type(exc).__name__})"


def process_job(conn: sqlite3.Connection, job: dict[str, Any]) -> None:
    """Run the job's analysis and store the outcome.

    Success sets ``status='done'`` and ``result``; any failure sets
    ``status='failed'`` and a short, readable ``error`` that never quotes the text.
    ``updated_at`` is refreshed either way.
    """
    job_id = job["id"]
    analysis = str(job.get("analysis", ""))
    try:
        result = analyses.run_analysis(analysis, job["text"])
    except Exception as exc:
        error = failure_message(analysis, exc)
        conn.execute(_FINISH_SQL, ("failed", None, error, claim.utc_now(), job_id))
        logger.warning("job %s failed: %s", job_id, type(exc).__name__)
        return
    conn.execute(_FINISH_SQL, ("done", result, None, claim.utc_now(), job_id))
    logger.info("job %s done", job_id)


def process_next(conn: sqlite3.Connection) -> bool:
    """Claim and process the next pending job.

    Returns ``True`` when a job was processed, ``False`` when none was pending.
    """
    job = claim.claim_next_job(conn)
    if job is None:
        return False
    process_job(conn, job)
    return True
