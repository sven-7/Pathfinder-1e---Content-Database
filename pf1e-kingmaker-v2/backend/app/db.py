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


def fetch_feats_sqlite(dsn: str) -> list[dict]:
    try:
        with sqlite_conn_from_dsn(dsn) as conn:
            rows = conn.execute(
                """
                SELECT id, name, feat_type, prerequisites, benefit, source_book
                FROM feats
                ORDER BY name
                """
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def fetch_races_sqlite(dsn: str) -> list[dict]:
    try:
        with sqlite_conn_from_dsn(dsn) as conn:
            rows = conn.execute(
                """
                SELECT id, name, race_type, size, base_speed, source_book
                FROM races
                ORDER BY name
                """
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error:
        return []
