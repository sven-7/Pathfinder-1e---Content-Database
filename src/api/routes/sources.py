"""GET /api/sources — list all available content sources."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["sources"])


@router.get("/sources")
async def list_sources(request: Request):
    """Return all source books from the content database."""
    db = request.app.state.db
    rows = db._many("SELECT id, name, abbreviation FROM sources ORDER BY id")
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "abbreviation": r.get("abbreviation") or "",
        }
        for r in rows
    ]
