"""The /jobs endpoints: create a job, list all jobs, read one job.

Every statement is parameterized. Validation happens in ``schemas.JobCreate`` so an
invalid body answers 422 before anything is written. Job text is never logged.
"""

import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from db import DbConnection
from fastapi import APIRouter, HTTPException, Path, status
from schemas import JobCreate, JobOut

router = APIRouter(tags=["jobs"])

_COLUMNS = "id, text, analysis, status, result, error, created_at, updated_at"


def _now_iso() -> str:
    """Current time as ISO 8601 in UTC."""
    return datetime.now(UTC).isoformat()


def _row_to_job(row: sqlite3.Row) -> JobOut:
    return JobOut(**dict(row))


@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, conn: DbConnection) -> JobOut:
    """Store a new pending job and return it (201)."""
    now = _now_iso()
    with conn:
        cursor = conn.execute(
            "INSERT INTO jobs (text, analysis, status, created_at, updated_at) "
            "VALUES (?, ?, 'pending', ?, ?)",
            (payload.text, payload.analysis, now, now),
        )
    row = conn.execute(f"SELECT {_COLUMNS} FROM jobs WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_job(row)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(conn: DbConnection) -> list[JobOut]:
    """Return every job, newest first (id descending)."""
    rows = conn.execute(f"SELECT {_COLUMNS} FROM jobs ORDER BY id DESC").fetchall()
    return [_row_to_job(r) for r in rows]


@router.get("/jobs/{id}", response_model=JobOut)
def get_job(job_id: Annotated[int, Path(alias="id")], conn: DbConnection) -> JobOut:
    """Return one job; an unknown id answers 404."""
    row = conn.execute(f"SELECT {_COLUMNS} FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _row_to_job(row)
