"""SQLAlchemy database/session wiring for API persistence."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def normalize_database_url(database_url: str) -> str:
    """Normalize configured database URLs to SQLAlchemy driver URLs."""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@lru_cache(maxsize=16)
def get_engine(database_url: str | None = None) -> Engine:
    url = normalize_database_url(database_url or settings.database_url)
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        parsed = make_url(url)
        db_path = parsed.database
        if db_path and db_path != ":memory:":
            path = Path(db_path)
            if not path.is_absolute():
                path = Path.cwd() / path
            path.parent.mkdir(parents=True, exist_ok=True)
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


@lru_cache(maxsize=16)
def get_sessionmaker(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(database_url),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db_session() -> Generator[Session, None, None]:
    session_local = get_sessionmaker()
    with session_local() as session:
        yield session
