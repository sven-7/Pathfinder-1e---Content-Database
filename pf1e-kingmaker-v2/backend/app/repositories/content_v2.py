"""Repository access for API V2 content endpoints."""

from __future__ import annotations

from app.db import fetch_feats_sqlite, fetch_policy_summary_sqlite, fetch_races_sqlite, is_sqlite_dsn


class ContentRepositoryV2:
    """Read-only content repository for API V2."""

    def __init__(self, database_url: str):
        self._database_url = database_url

    def list_feats(self, *, include_deferred: bool) -> list[dict]:
        if not is_sqlite_dsn(self._database_url):
            return []
        return fetch_feats_sqlite(self._database_url, include_deferred=include_deferred)

    def list_races(self, *, include_deferred: bool) -> list[dict]:
        if not is_sqlite_dsn(self._database_url):
            return []
        return fetch_races_sqlite(self._database_url, include_deferred=include_deferred)

    def policy_summary(self) -> dict:
        if not is_sqlite_dsn(self._database_url):
            return {
                "accepted_total": 0,
                "active_total": 0,
                "deferred_total": 0,
                "reason_counts": {},
                "tier_counts": {},
            }
        return fetch_policy_summary_sqlite(self._database_url)

