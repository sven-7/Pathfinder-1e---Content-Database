from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.persistence.database import get_db_session, get_sessionmaker
from app.persistence.migrations import run_app_migrations


@pytest.fixture()
def isolated_db(tmp_path: Path):
    db_path = tmp_path / "api_domain.db"
    dsn = f"sqlite:///{db_path}"
    run_app_migrations(database_url=dsn)
    session_local = get_sessionmaker(dsn)
    return {"dsn": dsn, "session_local": session_local}


@pytest.fixture()
def isolated_db_session(isolated_db):
    session_local = isolated_db["session_local"]
    with session_local() as session:
        yield session


@pytest.fixture()
def isolated_db_client(isolated_db):
    session_local = isolated_db["session_local"]

    def _override_get_db_session():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
