"""Content API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.config import settings
from app.db import fetch_feats_sqlite, fetch_races_sqlite, is_sqlite_dsn

router = APIRouter(prefix="/content", tags=["content-v2"])


@router.get("/feats")
def list_feats(_: Request):
    if not is_sqlite_dsn(settings.database_url):
        return []
    return fetch_feats_sqlite(settings.database_url)


@router.get("/races")
def list_races(_: Request):
    if not is_sqlite_dsn(settings.database_url):
        return []
    return fetch_races_sqlite(settings.database_url)
