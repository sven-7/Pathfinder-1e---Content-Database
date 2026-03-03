"""Application domain migration runner."""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import text

from app.persistence.database import get_engine

_APP_MIGRATION_PATTERN = re.compile(r"^1\d{3}_.+\.sql$")


def _migration_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "migrations"


def _iter_app_migration_files() -> list[Path]:
    migration_dir = _migration_dir()
    return sorted(path for path in migration_dir.glob("*.sql") if _APP_MIGRATION_PATTERN.match(path.name))


def _split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []

    for raw_line in sql_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        buffer.append(raw_line)
        if line.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement.endswith(";"):
                statement = statement[:-1]
            if statement:
                statements.append(statement)
            buffer = []

    if buffer:
        statement = "\n".join(buffer).strip()
        if statement.endswith(";"):
            statement = statement[:-1]
        if statement:
            statements.append(statement)

    return statements


def run_app_migrations(database_url: str | None = None) -> None:
    """Apply API-domain migrations exactly once per database."""
    engine = get_engine(database_url)
    migrations = _iter_app_migration_files()
    if not migrations:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS app_schema_migrations (
                  version TEXT PRIMARY KEY,
                  applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        rows = conn.execute(text("SELECT version FROM app_schema_migrations")).fetchall()
        applied = {str(row[0]) for row in rows}

        for migration_file in migrations:
            if migration_file.name in applied:
                continue

            sql_text = migration_file.read_text(encoding="utf-8")
            for statement in _split_sql_statements(sql_text):
                conn.exec_driver_sql(statement)

            conn.execute(
                text("INSERT INTO app_schema_migrations (version) VALUES (:version)"),
                {"version": migration_file.name},
            )

