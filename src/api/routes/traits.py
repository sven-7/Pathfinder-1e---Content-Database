"""GET /api/traits — trait listing with optional type filter."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["traits"])


@router.get("/traits")
async def list_traits(
    request: Request,
    type: str | None = Query(default=None, description="Trait type (Combat, Faith, Magic, Social, etc.)"),
    search: str | None = Query(default=None),
    source_ids: str | None = Query(default=None, description="Comma-separated source IDs to filter by"),
):
    db = request.app.state.db

    if type:
        rows = db._many(
            "SELECT * FROM traits WHERE LOWER(trait_type) = LOWER(?) ORDER BY name",
            (type,),
        )
    else:
        rows = db._many("SELECT * FROM traits ORDER BY trait_type, name")

    # Filter by allowed sources
    if source_ids:
        allowed = {int(s) for s in source_ids.split(",") if s.strip()}
        rows = [r for r in rows if r.get("source_id") in allowed]

    if search:
        s = search.lower()
        rows = [r for r in rows if s in r["name"].lower() or s in (r.get("benefit") or "").lower()]

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "trait_type": r.get("trait_type") or "General",
            "prerequisites": r.get("prerequisites") or "",
            "benefit": r.get("benefit") or "",
            "description": r.get("description") or "",
        }
        for r in rows
    ]


@router.get("/traits/types")
async def list_trait_types(request: Request):
    db = request.app.state.db
    rows = db._many("SELECT DISTINCT trait_type FROM traits ORDER BY trait_type")
    return [r["trait_type"] for r in rows if r["trait_type"]]
