"""Shared fixtures of the API tests.

Every test gets its own SQLite file under pytest's tmp_path (in a directory that
does not exist yet) and an application whose lifespan has run against it.
"""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make the api/ modules importable when pytest is started without PYTHONPATH=.
API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """A fresh database path whose parent directory does not exist yet."""
    return tmp_path / "data" / "jobs.db"


@pytest.fixture
def client(tmp_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A TestClient on a fresh app; entering it runs the startup (schema creation)."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_db_path))
    from main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
