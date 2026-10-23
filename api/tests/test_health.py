"""Tests of the API skeleton: health route, schema creation, CORS, generic 500."""

import logging
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import db
import pytest
from fastapi.testclient import TestClient
from main import DEFAULT_CORS_ORIGIN, create_app, get_cors_origins
from pydantic import ValidationError
from schemas import MAX_TEXT_LENGTH, JobCreate

ALLOWED_ORIGIN = "http://localhost:5173"
OTHER_ALLOWED_ORIGIN = "https://jobs.example.test"
FOREIGN_ORIGIN = "http://evil.example.test"

ClientFactory = Callable[[str | None], AbstractContextManager[TestClient]]


@pytest.fixture
def make_client(tmp_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> ClientFactory:
    """Build a started app with the given CORS_ORIGINS (None = variable unset)."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_db_path))

    @contextmanager
    def factory(cors_origins: str | None) -> Iterator[TestClient]:
        if cors_origins is None:
            monkeypatch.delenv("CORS_ORIGINS", raising=False)
        else:
            monkeypatch.setenv("CORS_ORIGINS", cors_origins)
        with TestClient(create_app()) as test_client:
            yield test_client

    return factory


# --- health -------------------------------------------------------------------------


def test_health_answers_200_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- schema creation on startup -----------------------------------------------------


def test_startup_creates_schema_at_database_path(
    tmp_db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_db_path))
    assert not tmp_db_path.parent.exists()

    with TestClient(create_app()) as test_client:
        assert test_client.get("/health").status_code == 200

    assert tmp_db_path.is_file()
    conn = sqlite3.connect(tmp_db_path)
    try:
        columns = {row[1]: row for row in conn.execute("PRAGMA table_info(jobs)")}
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        index_columns = [
            [info[2] for info in conn.execute("SELECT * FROM pragma_index_info(?)", (index[1],))]
            for index in conn.execute("PRAGMA index_list(jobs)").fetchall()
        ]
    finally:
        conn.close()

    assert set(columns) == {
        "id",
        "text",
        "analysis",
        "status",
        "result",
        "error",
        "created_at",
        "updated_at",
    }
    assert columns["status"][4] == "'pending'"  # default value
    assert columns["text"][3] == 1  # NOT NULL
    assert journal_mode == "wal"
    assert ["status", "id"] in index_columns


def test_startup_keeps_an_existing_database(
    tmp_db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_db_path))
    with TestClient(create_app()):
        pass
    conn = db.get_connection(tmp_db_path)
    try:
        conn.execute(
            "INSERT INTO jobs (text, analysis, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("eins zwei drei", "word_count", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        conn.commit()
    finally:
        conn.close()

    with TestClient(create_app()) as test_client:
        assert test_client.get("/health").status_code == 200

    conn = db.get_connection(tmp_db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    finally:
        conn.close()


def test_get_connection_uses_wal_and_busy_timeout(tmp_path: Path) -> None:
    conn = db.get_connection(tmp_path / "jobs.db")
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == db.BUSY_TIMEOUT_MS
    finally:
        conn.close()


def test_database_path_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_PATH", raising=False)

    assert db.get_database_path() == db.DEFAULT_DATABASE_PATH


# --- CORS ---------------------------------------------------------------------------


def test_cors_allows_a_listed_origin_without_credentials(make_client: ClientFactory) -> None:
    with make_client(f"{ALLOWED_ORIGIN}, {OTHER_ALLOWED_ORIGIN}") as test_client:
        simple = test_client.get("/health", headers={"Origin": OTHER_ALLOWED_ORIGIN})
        preflight = test_client.options(
            "/jobs",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert simple.status_code == 200
    assert simple.headers["access-control-allow-origin"] == OTHER_ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in simple.headers
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in preflight.headers


def test_cors_rejects_an_unlisted_origin(make_client: ClientFactory) -> None:
    with make_client(ALLOWED_ORIGIN) as test_client:
        simple = test_client.get("/health", headers={"Origin": FOREIGN_ORIGIN})
        preflight = test_client.options(
            "/jobs",
            headers={"Origin": FOREIGN_ORIGIN, "Access-Control-Request-Method": "POST"},
        )

    assert "access-control-allow-origin" not in simple.headers
    assert "access-control-allow-credentials" not in simple.headers
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers


def test_cors_defaults_to_the_local_vite_origin_only(make_client: ClientFactory) -> None:
    with make_client(None) as test_client:
        allowed = test_client.get("/health", headers={"Origin": DEFAULT_CORS_ORIGIN})
        foreign = test_client.get("/health", headers={"Origin": FOREIGN_ORIGIN})

    assert allowed.headers["access-control-allow-origin"] == DEFAULT_CORS_ORIGIN
    assert "access-control-allow-origin" not in foreign.headers


def test_cors_never_accepts_a_wildcard(
    make_client: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")
    assert get_cors_origins() == [DEFAULT_CORS_ORIGIN]

    with make_client(f"*, {OTHER_ALLOWED_ORIGIN}") as test_client:
        response = test_client.get("/health", headers={"Origin": FOREIGN_ORIGIN})

    assert response.headers.get("access-control-allow-origin") not in ("*", FOREIGN_ORIGIN)


def test_cors_origins_ignore_entries_that_are_not_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", f" {OTHER_ALLOWED_ORIGIN}/ , ${{service:web.origin}}, ,")

    assert get_cors_origins() == [OTHER_ALLOWED_ORIGIN]


# --- generic 500 --------------------------------------------------------------------


def test_unhandled_error_answers_generic_500_with_cors_and_no_details(
    make_client: ClientFactory, caplog: pytest.LogCaptureFixture
) -> None:
    sentinel = "private job text 4711"

    def explode() -> None:
        raise RuntimeError(sentinel)

    with make_client(ALLOWED_ORIGIN) as test_client:
        test_client.app.add_api_route("/test-explode", explode, methods=["GET"])
        with caplog.at_level(logging.ERROR, logger="api"):
            response = test_client.get("/test-explode", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert sentinel not in response.text
    assert "Traceback" not in response.text
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "RuntimeError" in caplog.text
    assert sentinel not in caplog.text


# --- routes and request model -------------------------------------------------------


def test_jobs_routes_are_registered(client: TestClient) -> None:
    paths = client.app.openapi()["paths"]

    assert "post" in paths["/jobs"]
    assert "get" in paths["/jobs"]
    assert "get" in paths["/jobs/{id}"]
    assert "get" in paths["/health"]


def test_job_create_trims_text() -> None:
    job = JobCreate(text="  eins zwei drei \n", analysis="word_count")

    assert job.text == "eins zwei drei"
    assert job.analysis == "word_count"


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "", "analysis": "word_count"},
        {"text": "   \n\t ", "analysis": "top_words"},
        {"text": "x" * (MAX_TEXT_LENGTH + 1), "analysis": "reading_time"},
        {"text": "eins", "analysis": "sentiment"},
        {"analysis": "word_count"},
        {"text": "eins"},
    ],
)
def test_job_create_rejects_invalid_input(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        JobCreate(**payload)


def test_job_create_accepts_text_at_the_limit() -> None:
    job = JobCreate(text="x" * MAX_TEXT_LENGTH, analysis="reading_time")

    assert len(job.text) == MAX_TEXT_LENGTH
