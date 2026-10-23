"""Tests for atomic claiming of pending jobs."""

from __future__ import annotations

import multiprocessing
import sqlite3

import claim
import db

NOW = "2026-01-01T00:00:00+00:00"


def insert(conn: sqlite3.Connection, text: str = "a b", status: str = "pending") -> int:
    cur = conn.execute(
        "INSERT INTO jobs (text, analysis, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (text, "word_count", status, NOW, NOW),
    )
    return int(cur.lastrowid)


def test_claim_returns_none_when_empty(db_conn: sqlite3.Connection) -> None:
    assert claim.claim_next_job(db_conn) is None


def test_claims_oldest_first_and_sets_running(db_conn: sqlite3.Connection) -> None:
    insert(db_conn, status="done")
    first = insert(db_conn)
    second = insert(db_conn)
    job = claim.claim_next_job(db_conn)
    assert job is not None
    assert job["id"] == first
    assert job["status"] == "running"
    assert job["updated_at"] != NOW
    row = db_conn.execute("SELECT status FROM jobs WHERE id = ?", (first,)).fetchone()
    assert row[0] == "running"
    assert claim.claim_next_job(db_conn)["id"] == second
    assert claim.claim_next_job(db_conn) is None


def test_no_double_claim_across_two_connections(tmp_db: str) -> None:
    a, b = db.get_connection(tmp_db), db.get_connection(tmp_db)
    try:
        ids = [insert(a) for _ in range(10)]
        claimed: list[int] = []
        while True:
            got = [claim.claim_next_job(c) for c in (a, b)]
            got = [j["id"] for j in got if j]
            if not got:
                break
            claimed.extend(got)
        assert sorted(claimed) == ids
    finally:
        a.close()
        b.close()


def _claim_all(path: str, out: multiprocessing.Queue) -> None:
    conn = db.get_connection(path)
    got = []
    while (job := claim.claim_next_job(conn)) is not None:
        got.append(job["id"])
    conn.close()
    out.put(got)


def test_no_double_claim_across_processes(tmp_db: str) -> None:
    conn = db.get_connection(tmp_db)
    ids = [insert(conn) for _ in range(60)]
    conn.close()
    ctx = multiprocessing.get_context("spawn")
    out = ctx.Queue()
    procs = [ctx.Process(target=_claim_all, args=(tmp_db, out)) for _ in range(3)]
    for p in procs:
        p.start()
    results = [out.get(timeout=60) for _ in procs]
    for p in procs:
        p.join(timeout=30)
    claimed = [i for r in results for i in r]
    assert sorted(claimed) == ids
