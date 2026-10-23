"""The /jobs endpoints: create a job, list all jobs, read one job.

The routes, their verbs, request bodies and response models are final. Their bodies
are filled in by the ticket 'Implement the jobs endpoints'; until then each answers
501 Not Implemented explicitly.
"""

from typing import Annotated

from db import DbConnection
from fastapi import APIRouter, HTTPException, Path, status
from schemas import JobCreate, JobOut

router = APIRouter(tags=["jobs"])

_NOT_IMPLEMENTED = "Implement the jobs endpoints ticket implements this"


@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, conn: DbConnection) -> JobOut:
    """Store a new pending job and return it (201)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_IMPLEMENTED)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(conn: DbConnection) -> list[JobOut]:
    """Return every job, newest first (id descending)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_IMPLEMENTED)


@router.get("/jobs/{id}", response_model=JobOut)
def get_job(job_id: Annotated[int, Path(alias="id")], conn: DbConnection) -> JobOut:
    """Return one job; an unknown id answers 404."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_IMPLEMENTED)
