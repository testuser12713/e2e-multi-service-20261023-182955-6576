"""Tests of the /jobs endpoints."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient


def _count(client: TestClient) -> int:
    return len(client.get("/jobs").json())


def test_create_list_get(client: TestClient) -> None:
    resp = client.post("/jobs", json={"text": "  eins zwei drei  ", "analysis": "word_count"})
    assert resp.status_code == 201
    job = resp.json()
    assert job["status"] == "pending"
    assert job["text"] == "eins zwei drei"
    assert job["result"] is None and job["error"] is None
    created = datetime.fromisoformat(job["created_at"])
    assert created.utcoffset() is not None and created.utcoffset().total_seconds() == 0
    assert job["created_at"] == job["updated_at"]

    listed = client.get("/jobs")
    assert listed.status_code == 200
    assert listed.json()[0] == job

    got = client.get(f"/jobs/{job['id']}")
    assert got.status_code == 200
    assert got.json() == job


def test_list_newest_first(client: TestClient) -> None:
    ids = [
        client.post("/jobs", json={"text": f"t{i}", "analysis": "top_words"}).json()["id"]
        for i in range(3)
    ]
    assert [j["id"] for j in client.get("/jobs").json()] == list(reversed(ids))


def test_unknown_id_404(client: TestClient) -> None:
    resp = client.get("/jobs/9999")
    assert resp.status_code == 404
    assert isinstance(resp.json()["detail"], str)


@pytest.mark.parametrize(
    "body",
    [
        {"text": "", "analysis": "word_count"},
        {"text": "   \n\t ", "analysis": "word_count"},
        {"text": "hallo", "analysis": "sentiment"},
        {"text": "a" * 100_001, "analysis": "reading_time"},
    ],
)
def test_invalid_body_422_and_nothing_stored(client: TestClient, body: dict) -> None:
    resp = client.post("/jobs", json=body)
    assert resp.status_code == 422
    assert _count(client) == 0


def test_max_length_accepted(client: TestClient) -> None:
    assert (
        client.post("/jobs", json={"text": "a" * 100_000, "analysis": "word_count"}).status_code
        == 201
    )


def test_sql_injection_text_stored_unchanged(client: TestClient) -> None:
    text = "x'; DROP TABLE jobs;--"
    job = client.post("/jobs", json={"text": text, "analysis": "word_count"}).json()
    assert client.get(f"/jobs/{job['id']}").json()["text"] == text
    assert client.get("/health").status_code == 200


def test_5xx_body_has_no_trace(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import routers.jobs as jobs_module

    def boom(row: object) -> object:
        raise RuntimeError("secret job text /etc/passwd")

    client.post("/jobs", json={"text": "geheim", "analysis": "word_count"})
    monkeypatch.setattr(jobs_module, "_row_to_job", boom)
    resp = client.get("/jobs")
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal Server Error"}
    assert "Traceback" not in resp.text and "geheim" not in resp.text and "/" not in resp.text
