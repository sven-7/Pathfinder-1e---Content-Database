"""GET /api/equipment/weapons, /api/equipment/armor, /api/equipment/gear."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["equipment"])


@router.get("/equipment/weapons")
async def list_weapons(
    request: Request,
    source_ids: str | None = Query(default=None, description="Comma-separated source IDs"),
):
    db = request.app.state.db
    rows = db.get_weapons()
    if source_ids:
        allowed = {int(s) for s in source_ids.split(",") if s.strip()}
        rows = [r for r in rows if r.get("source_id") in allowed]
    return [
        {
            "equipment_id": r["equipment_id"],
            "name": r["name"],
            "cost": r.get("cost") or "",
            "cost_copper": r.get("cost_copper"),
            "weight": r.get("weight") or "",
            "proficiency": r["proficiency"],
            "weapon_type": r["weapon_type"],
            "handedness": r.get("handedness") or "",
            "damage_small": r.get("damage_small") or "",
            "damage_medium": r.get("damage_medium") or "",
            "critical": r.get("critical") or "",
            "range_increment": r.get("range_increment") or "",
            "damage_type": r.get("damage_type") or "",
            "special": r.get("special") or "",
        }
        for r in rows
    ]


@router.get("/equipment/armor")
async def list_armor(
    request: Request,
    source_ids: str | None = Query(default=None, description="Comma-separated source IDs"),
):
    db = request.app.state.db
    rows = db.get_armor()
    if source_ids:
        allowed = {int(s) for s in source_ids.split(",") if s.strip()}
        rows = [r for r in rows if r.get("source_id") in allowed]
    return [
        {
            "equipment_id": r["equipment_id"],
            "name": r["name"],
            "cost": r.get("cost") or "",
            "cost_copper": r.get("cost_copper"),
            "weight": r.get("weight") or "",
            "armor_type": r["armor_type"],
            "armor_bonus": r["armor_bonus"],
            "max_dex": r.get("max_dex"),        # None = no limit
            "armor_check_penalty": r.get("armor_check_penalty") or 0,
            "arcane_spell_failure": r.get("arcane_spell_failure") or 0,
            "speed_30": r.get("speed_30") or "",
            "speed_20": r.get("speed_20") or "",
        }
        for r in rows
    ]


@router.get("/equipment/gear/types")
async def gear_types():
    """Available gear subtypes."""
    return ["gear", "alchemical", "tool", "clothing", "mount", "vehicle", "service"]


@router.get("/equipment/gear")
async def list_gear(
    request: Request,
    type: str | None = Query(default=None, description="Gear subtype filter"),
    search: str | None = Query(default=None, description="Name search"),
    source_ids: str | None = Query(default=None, description="Comma-separated source IDs"),
    limit: int = Query(default=200, ge=1, le=1000),
):
    db = request.app.state.db
    rows = db.get_gear(equipment_type=type)

    if source_ids:
        allowed = {int(s) for s in source_ids.split(",") if s.strip()}
        rows = [r for r in rows if r.get("source_id") in allowed]

    if search:
        s = search.lower()
        rows = [r for r in rows if s in r["name"].lower()]

    rows = rows[:limit]

    return [
        {
            "equipment_id": r["equipment_id"],
            "name": r["name"],
            "equipment_type": r.get("equipment_type") or "gear",
            "cost": r.get("cost") or "",
            "cost_copper": r.get("cost_copper"),
            "weight": r.get("weight"),
            "description": r.get("description") or "",
        }
        for r in rows
    ]
