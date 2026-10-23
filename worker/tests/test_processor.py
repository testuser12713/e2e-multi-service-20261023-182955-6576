"""Tests for job processing and status transitions."""

from __future__ import annotations

import sqlite3

import analyses
import processor
import pytest

NOW = "2026-01-01T00:00:00+00:00"
SECRET = "geheimer Auftragstext /home/user/x"


def insert(conn: sqlite3.Connection, text: str, analysis: str) -> int:
    cur = conn.execute(
        "INSERT INTO jobs (text, analysis, status, created_at, updated_at) "
        "VALUES (?, ?, 'pending', ?, ?)",
        (text, analysis, NOW, NOW),
    )
    return int(cur.lastrowid)


def row(conn: sqlite3.Connection, job_id: int) -> sqlite3.Row:
    return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def test_done_transition(db_conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analyses, "run_analysis", lambda a, t: "3")
    job_id = insert(db_conn, "eins zwei drei", "word_count")
    assert processor.process_next(db_conn) is True
    r = row(db_conn, job_id)
    assert (r["status"], r["result"], r["error"]) == ("done", "3", None)
    assert r["updated_at"] != NOW
    assert processor.process_next(db_conn) is False


def test_unknown_analysis_fails_without_text(db_conn: sqlite3.Connection) -> None:
    job_id = insert(db_conn, SECRET, "nonsense")
    assert processor.process_next(db_conn) is True
    r = row(db_conn, job_id)
    assert r["status"] == "failed"
    assert r["result"] is None
    assert r["error"]
    assert "geheim" not in r["error"] and "/" not in r["error"]
    assert "Traceback" not in r["error"]


def test_exception_message_never_stored(
    db_conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(analysis: str, text: str) -> str:
        raise RuntimeError(f"failed on {text}")

    monkeypatch.setattr(analyses, "run_analysis", boom)
    job_id = insert(db_conn, SECRET, "word_count")
    processor.process_next(db_conn)
    r = row(db_conn, job_id)
    assert r["status"] == "failed"
    assert "geheim" not in r["error"]


def test_continues_with_next_job(
    db_conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = insert(db_conn, "x", "nonsense")
    real = analyses.run_analysis
    monkeypatch.setattr(
        analyses, "run_analysis", lambda a, t: real(a, t) if a == "nonsense" else "ok"
    )
    good = insert(db_conn, "'; DROP TABLE jobs;--", "word_count")
    assert processor.process_next(db_conn) is True
    assert processor.process_next(db_conn) is True
    assert row(db_conn, bad)["status"] == "failed"
    r = row(db_conn, good)
    assert r["status"] == "done"
    assert r["text"] == "'; DROP TABLE jobs;--"
