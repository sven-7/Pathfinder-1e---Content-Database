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


def fetch_policy_summary_sqlite(dsn: str) -> dict:
    default = {
        "accepted_total": 0,
        "active_total": 0,
        "deferred_total": 0,
        "reason_counts": {},
        "tier_counts": {},
    }
    try:
        with sqlite_conn_from_dsn(dsn) as conn:
            totals = conn.execute(
                """
                SELECT
                  COUNT(*) AS accepted_total,
                  SUM(CASE WHEN COALESCE(ui_enabled, 1) = 1 THEN 1 ELSE 0 END) AS active_total,
                  SUM(CASE WHEN COALESCE(ui_enabled, 1) = 0 THEN 1 ELSE 0 END) AS deferred_total
                FROM source_records
                WHERE parse_status = 'accepted'
                """
            ).fetchone()

            reason_rows = conn.execute(
                """
                SELECT COALESCE(policy_reason, 'allowlisted') AS policy_reason, COUNT(*) AS count
                FROM source_records
                WHERE parse_status = 'accepted'
                GROUP BY COALESCE(policy_reason, 'allowlisted')
                ORDER BY count DESC, policy_reason
                """
            ).fetchall()

            tier_rows = conn.execute(
                """
                SELECT COALESCE(ui_tier, 'active') AS ui_tier, COUNT(*) AS count
                FROM source_records
                WHERE parse_status = 'accepted'
                GROUP BY COALESCE(ui_tier, 'active')
                ORDER BY count DESC, ui_tier
                """
            ).fetchall()

            return {
                "accepted_total": int(totals["accepted_total"] or 0),
                "active_total": int(totals["active_total"] or 0),
                "deferred_total": int(totals["deferred_total"] or 0),
                "reason_counts": {str(r["policy_reason"]): int(r["count"]) for r in reason_rows},
                "tier_counts": {str(r["ui_tier"]): int(r["count"]) for r in tier_rows},
            }
    except sqlite3.Error:
        return default
