"""Worker process: polls the shared SQLite database for pending jobs and processes them.

Start it from the ``worker/`` directory with ``python main.py``. Configuration:

- ``DATABASE_PATH`` (required): the SQLite file the API uses.
- ``WORKER_POLL_INTERVAL`` (optional, seconds, default 1): pause after a poll that
  found no pending job.

The worker waits for the API to create the ``jobs`` table, then runs until it is
stopped (Ctrl+C or SIGTERM). An unexpected error while processing is logged and the
loop carries on with the next poll.
"""

from __future__ import annotations

import logging
import math
import os
import signal
import sqlite3
import sys
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from types import FrameType

import db
import processor

logger = logging.getLogger("worker")

POLL_INTERVAL_ENV = "WORKER_POLL_INTERVAL"
DEFAULT_POLL_INTERVAL_S = 1.0


@dataclass(frozen=True)
class Settings:
    """Everything the worker needs to run, validated once at startup."""

    database_path: str
    poll_interval: float


def poll_interval_from_env() -> float:
    """``WORKER_POLL_INTERVAL`` in seconds; the default when unset, an error when invalid."""
    raw = os.environ.get(POLL_INTERVAL_ENV, "").strip()
    if not raw:
        return DEFAULT_POLL_INTERVAL_S
    try:
        value = float(raw)
    except ValueError:
        raise db.ConfigError(
            f"{POLL_INTERVAL_ENV} must be a number of seconds, got {raw!r}"
        ) from None
    if not math.isfinite(value) or value <= 0:
        raise db.ConfigError(f"{POLL_INTERVAL_ENV} must be a positive number of seconds")
    return value


def load_settings() -> Settings:
    """Read and validate the whole configuration; raises ``db.ConfigError`` naming the variable."""
    return Settings(
        database_path=db.database_path_from_env(),
        poll_interval=poll_interval_from_env(),
    )


def describe_failure(exc: BaseException) -> str:
    """The exception's type and the place it was raised.

    Deliberately leaves out the exception's message: it could quote a job's text,
    and the job text must never reach a log.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return type(exc).__name__
    last = frames[-1]
    return f"{type(exc).__name__} at {os.path.basename(last.filename)}:{last.lineno} in {last.name}"


def _rollback_open_transaction(conn: sqlite3.Connection) -> None:
    """Release a transaction a failed iteration left open, so no lock is held forever."""
    if not conn.in_transaction:
        return
    try:
        conn.rollback()
    except sqlite3.Error as exc:
        logger.warning("rollback after a failed iteration failed: %s", type(exc).__name__)


def run_loop(
    conn: sqlite3.Connection,
    poll_interval: float,
    *,
    should_stop: Callable[[], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Process jobs forever: one ``processor.process_next`` call per iteration.

    Sleeps ``poll_interval`` seconds whenever an iteration found nothing to do or
    failed; goes straight on after a processed job. An exception in one iteration is
    logged (without its message) and never ends the loop. ``should_stop`` is checked
    before every iteration; without it the loop runs until the process is stopped.
    """
    while should_stop is None or not should_stop():
        try:
            worked = processor.process_next(conn)
        except Exception as exc:
            _rollback_open_transaction(conn)
            logger.error(
                "processing failed with %s; the worker keeps running", describe_failure(exc)
            )
            worked = False
        if not worked:
            sleep(poll_interval)


def run(
    settings: Settings,
    *,
    should_stop: Callable[[], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Connect, wait for the API's schema, then poll for jobs until stopped."""
    location = os.path.abspath(settings.database_path)
    conn = db.get_connection(settings.database_path)
    try:
        logger.info("worker connected to %s", location)
        db.wait_for_schema(conn, sleep=sleep)
        logger.info("table 'jobs' found; polling every %gs", settings.poll_interval)
        run_loop(conn, settings.poll_interval, should_stop=should_stop, sleep=sleep)
    finally:
        conn.close()


def _stop_on_sigterm(signum: int, frame: FrameType | None) -> None:
    """Turn SIGTERM into the same orderly stop as Ctrl+C."""
    raise KeyboardInterrupt


def main() -> int:
    """Entry point of ``python main.py``; returns the process exit code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = load_settings()
    except db.ConfigError as exc:
        logger.error("worker cannot start: %s", exc)
        return 2

    signal.signal(signal.SIGTERM, _stop_on_sigterm)
    try:
        run(settings)
    except KeyboardInterrupt:
        logger.info("worker stopped")
    except (OSError, sqlite3.Error) as exc:
        logger.error(
            "worker cannot open the database at %s: %s",
            os.path.abspath(settings.database_path),
            exc,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
