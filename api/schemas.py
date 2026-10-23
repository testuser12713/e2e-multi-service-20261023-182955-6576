"""Request and response models of the jobs API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_TEXT_LENGTH = 100_000

AnalysisKind = Literal["word_count", "top_words", "reading_time"]
JobStatus = Literal["pending", "running", "done", "failed"]


class JobCreate(BaseModel):
    """Body of POST /jobs.

    ``text`` is trimmed first; the trimmed text must be non-empty and at most
    MAX_TEXT_LENGTH characters. The limit is enforced here, during request
    validation, so an oversized text is rejected with 422 before anything is stored.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    analysis: AnalysisKind


class JobOut(BaseModel):
    """A job as the API returns it.

    ``analysis`` is a plain string on the way out: a row may hold a value the worker
    cannot analyse (it then ends as ``failed``), and listing it must still work.
    ``created_at``/``updated_at`` are ISO 8601 timestamps in UTC.
    """

    id: int
    text: str
    analysis: str
    status: JobStatus
    result: str | None
    error: str | None
    created_at: str
    updated_at: str
