"""Lightweight DB helpers for API read paths."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class DbConfig:
    dsn: str


def is_sqlite_dsn(dsn: str) -> bool:
    return dsn.startswith("sqlite:///")


def sqlite_path_from_dsn(dsn: str) -> str:
    return dsn.replace("sqlite:///", "", 1)


@contextmanager
def sqlite_conn_from_dsn(dsn: str):
    path = sqlite_path_from_dsn(dsn)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def fetch_feats_sqlite(dsn: str, *, include_deferred: bool = False) -> list[dict]:
    try:
        with sqlite_conn_from_dsn(dsn) as conn:
            if include_deferred:
                rows = conn.execute(
                    """
                    SELECT f.id, f.name, f.feat_type, f.prerequisites, f.benefit, f.source_book,
                           COALESCE(sr.ui_enabled, 1) AS ui_enabled,
                           COALESCE(sr.ui_tier, 'active') AS ui_tier,
                           COALESCE(sr.policy_reason, 'allowlisted') AS policy_reason
                    FROM feats f
                    LEFT JOIN source_records sr ON sr.id = f.source_record_id
                    ORDER BY f.name
                    """
                ).fetchall()
                return [dict(r) for r in rows]

            rows = conn.execute(
                """
                SELECT f.id, f.name, f.feat_type, f.prerequisites, f.benefit, f.source_book
                FROM feats f
                LEFT JOIN source_records sr ON sr.id = f.source_record_id
                WHERE COALESCE(sr.ui_enabled, 1) = 1
                ORDER BY f.name
                """
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def fetch_races_sqlite(dsn: str, *, include_deferred: bool = False) -> list[dict]:
    try:
        with sqlite_conn_from_dsn(dsn) as conn:
            if include_deferred:
                rows = conn.execute(
                    """
                    SELECT r.id, r.name, r.race_type, r.size, r.base_speed, r.source_book,
                           COALESCE(sr.ui_enabled, 1) AS ui_enabled,
                           COALESCE(sr.ui_tier, 'active') AS ui_tier,
                           COALESCE(sr.policy_reason, 'allowlisted') AS policy_reason
                    FROM races r
                    LEFT JOIN source_records sr ON sr.id = r.source_record_id
                    ORDER BY r.name
                    """
                ).fetchall()
                return [dict(r) for r in rows]

            rows = conn.execute(
                """
                SELECT r.id, r.name, r.race_type, r.size, r.base_speed, r.source_book
                FROM races r
                LEFT JOIN source_records sr ON sr.id = r.source_record_id
                WHERE COALESCE(sr.ui_enabled, 1) = 1
                ORDER BY r.name
                """
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error:
        return []
