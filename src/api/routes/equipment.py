"""GET /api/equipment/weapons and /api/equipment/armor."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["equipment"])


@router.get("/equipment/weapons")
async def list_weapons(request: Request):
    db = request.app.state.db
    rows = db.get_weapons()
    return [
        {
            "equipment_id": r["equipment_id"],
            "name": r["name"],
            "cost": r.get("cost") or "",
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
async def list_armor(request: Request):
    db = request.app.state.db
    rows = db.get_armor()
    return [
        {
            "equipment_id": r["equipment_id"],
            "name": r["name"],
            "cost": r.get("cost") or "",
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
