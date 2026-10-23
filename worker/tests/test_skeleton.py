"""Tests for the worker skeleton: connections, waiting for the schema and the poll loop."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

import db
import main
import processor
import pytest

SECRET_TEXT = "Vertraulicher Auftragstext 4711"


def _stop_after(limit: int) -> tuple[Callable[[], bool], list[int]]:
    """A should_stop callable that lets exactly ``limit`` iterations run."""
    checks = [0]

    def should_stop() -> bool:
        checks[0] += 1
        return checks[0] > limit

    return should_stop, checks


def test_get_connection_uses_wal_and_busy_timeout(tmp_db: str) -> None:
    conn = db.get_connection(tmp_db)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == db.BUSY_TIMEOUT_MS
    finally:
        conn.close()


def test_get_connection_creates_missing_parent_directory(tmp_path: Path) -> None:
    target = tmp_path / "data" / "jobs.db"
    conn = db.get_connection(str(target))
    conn.close()
    assert target.parent.is_dir()


def test_missing_database_path_fails_at_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv(db.DATABASE_PATH_ENV, raising=False)
    with pytest.raises(db.ConfigError, match="DATABASE_PATH"):
        db.database_path_from_env()

    def must_not_wait(seconds: float) -> None:
        raise AssertionError("the worker must not wait without DATABASE_PATH")

    monkeypatch.setattr(main.time, "sleep", must_not_wait)
    with caplog.at_level(logging.ERROR):
        assert main.main() != 0
    assert "DATABASE_PATH" in caplog.text


def test_poll_interval_defaults_to_one_second_and_rejects_nonsense(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(main.POLL_INTERVAL_ENV, raising=False)
    assert main.poll_interval_from_env() == 1.0
    monkeypatch.setenv(main.POLL_INTERVAL_ENV, "0.25")
    assert main.poll_interval_from_env() == pytest.approx(0.25)
    for bad in ("abc", "0", "-1", "nan"):
        monkeypatch.setenv(main.POLL_INTERVAL_ENV, bad)
        with pytest.raises(db.ConfigError, match=main.POLL_INTERVAL_ENV):
            main.poll_interval_from_env()


def test_wait_for_schema_returns_at_once_when_table_exists(db_conn: sqlite3.Connection) -> None:
    sleeps: list[float] = []
    db.wait_for_schema(db_conn, sleep=sleeps.append)
    assert sleeps == []


def test_wait_for_schema_returns_once_table_exists(
    tmp_path: Path,
    create_schema: Callable[[str | Path], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = tmp_path / "late.db"
    conn = db.get_connection(str(path))
    sleeps: list[float] = []

    def sleep_then_maybe_create(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 6:
            create_schema(path)

    try:
        with caplog.at_level(logging.INFO, logger="worker.db"):
            db.wait_for_schema(
                conn, initial_delay=0.1, max_delay=0.5, sleep=sleep_then_maybe_create
            )
    finally:
        conn.close()

    assert len(sleeps) == 6
    # Backoff grows and is bounded by the cap.
    assert sleeps == sorted(sleeps)
    assert max(sleeps) <= 0.5
    assert sleeps[-1] == pytest.approx(0.5)
    # Every wait is logged.
    waits = [r for r in caplog.records if "does not exist yet" in r.getMessage()]
    assert len(waits) == 6


def test_main_loop_function_can_be_imported() -> None:
    from main import run_loop

    assert callable(run_loop)


def test_run_loop_keeps_running_after_unexpected_error(
    db_conn: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    outcomes: list[object] = [RuntimeError(SECRET_TEXT), True, False]
    calls: list[int] = []

    def fake_process_next(conn: sqlite3.Connection) -> bool:
        calls.append(1)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return bool(outcome)

    monkeypatch.setattr(processor, "process_next", fake_process_next)
    should_stop, _ = _stop_after(3)
    sleeps: list[float] = []

    with caplog.at_level(logging.INFO):
        main.run_loop(db_conn, 0.5, should_stop=should_stop, sleep=sleeps.append)

    assert len(calls) == 3
    # Sleeps after the failure and after the idle poll, not after a processed job.
    assert sleeps == [0.5, 0.5]
    assert "RuntimeError" in caplog.text
    assert SECRET_TEXT not in caplog.text


def test_run_loop_releases_a_transaction_left_open_by_a_failure(
    db_conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing_process_next(conn: sqlite3.Connection) -> bool:
        conn.execute("BEGIN IMMEDIATE")
        raise sqlite3.OperationalError("simulated failure")

    monkeypatch.setattr(processor, "process_next", failing_process_next)
    should_stop, _ = _stop_after(2)
    main.run_loop(db_conn, 0.01, should_stop=should_stop, sleep=lambda _s: None)
    assert not db_conn.in_transaction


def test_run_waits_for_a_late_schema_and_then_keeps_polling(
    tmp_path: Path,
    create_schema: Callable[[str | Path], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data" / "jobs.db"
    polls: list[int] = []

    def counting_process_next(conn: sqlite3.Connection) -> bool:
        polls.append(1)
        return False

    monkeypatch.setattr(processor, "process_next", counting_process_next)
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 2:
            create_schema(path)

    should_stop, _ = _stop_after(4)
    main.run(
        main.Settings(database_path=str(path), poll_interval=0.2),
        should_stop=should_stop,
        sleep=sleep,
    )

    assert len(polls) == 4
    # Two waits for the schema, then one idle pause per poll.
    assert sleeps[2:] == [0.2, 0.2, 0.2, 0.2]
