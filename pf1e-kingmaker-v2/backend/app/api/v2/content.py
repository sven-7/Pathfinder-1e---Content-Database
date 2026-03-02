"""Content API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.config import settings
from app.db import fetch_feats_sqlite, fetch_policy_summary_sqlite, fetch_races_sqlite, is_sqlite_dsn

router = APIRouter(prefix="/content", tags=["content-v2"])


@router.get("/feats")
def list_feats(_: Request, include_deferred: bool = Query(default=False)):
    if not is_sqlite_dsn(settings.database_url):
        return []
    return fetch_feats_sqlite(settings.database_url, include_deferred=include_deferred)


@router.get("/races")
def list_races(_: Request, include_deferred: bool = Query(default=False)):
    if not is_sqlite_dsn(settings.database_url):
        return []
    return fetch_races_sqlite(settings.database_url, include_deferred=include_deferred)


@router.get("/policy-summary")
def policy_summary(_: Request):
    if not is_sqlite_dsn(settings.database_url):
        return {
            "accepted_total": 0,
            "active_total": 0,
            "deferred_total": 0,
            "reason_counts": {},
            "tier_counts": {},
        }
    return fetch_policy_summary_sqlite(settings.database_url)
