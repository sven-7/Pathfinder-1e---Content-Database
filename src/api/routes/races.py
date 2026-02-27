"""GET /api/races — race listing and detail."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["races"])

# ── Hardcoded ability modifiers for standard PF1e races ─────────────────── #
# The scraped DB has empty ability_modifiers for many races.
# These are the canonical values from the Core Rulebook.

_CORE_ABILITY_MODS: dict[str, dict] = {
    "Dwarves":    {"con": 2, "wis": 2, "cha": -2},
    "Elves":      {"dex": 2, "int": 2, "con": -2},
    "Gnomes":     {"con": 2, "cha": 2, "str": -2},
    "Half-Elves": {},  # flexible +2 to any one score
    "Half-Orcs":  {},  # flexible +2 to any one score
    "Halflings":  {"dex": 2, "cha": 2, "str": -2},
    "Humans":     {},  # flexible +2 to any one score
}

# Races that get a free +2 to a player-chosen ability score
_FLEXIBLE_BONUS = {"Half-Elves", "Half-Orcs", "Humans"}

_CORE_RACE_SIZES: dict[str, str] = {
    "Dwarves": "Medium", "Elves": "Medium", "Gnomes": "Small",
    "Half-Elves": "Medium", "Half-Orcs": "Medium", "Halflings": "Small", "Humans": "Medium",
}

_CORE_RACE_SPEED: dict[str, int] = {
    "Dwarves": 20, "Gnomes": 20, "Halflings": 20,
}


def _enrich_race(row: dict) -> dict:
    name = row["name"]

    # ability_modifiers: parse JSON from DB, or fall back to hardcoded
    mods = {}
    raw = row.get("ability_modifiers") or ""
    if raw:
        try:
            mods = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    if not mods and name in _CORE_ABILITY_MODS:
        mods = _CORE_ABILITY_MODS[name]

    size = row.get("size") or _CORE_RACE_SIZES.get(name, "Medium")
    speed = row.get("base_speed") or _CORE_SPEED_FALLBACK(name)

    return {
        "id": row["id"],
        "name": name,
        "race_type": row.get("race_type") or "other",
        "size": size,
        "base_speed": speed,
        "ability_modifiers": mods,
        "flexible_bonus": name in _FLEXIBLE_BONUS,
        "type": row.get("type") or "Humanoid",
        "description": row.get("description") or "",
        "url": row.get("url") or "",
    }


def _CORE_SPEED_FALLBACK(name: str) -> int:
    return _CORE_RACE_SPEED.get(name, 30)


@router.get("/races")
async def list_races(request: Request):
    db = request.app.state.db
    rows = db._many(
        """SELECT r.*, s.name as source_name
           FROM races r
           LEFT JOIN sources s ON s.id = r.source_id
           ORDER BY
             CASE r.race_type
               WHEN 'core'     THEN 0
               WHEN 'featured' THEN 1
               WHEN 'uncommon' THEN 2
               ELSE 3
             END, r.name"""
    )
    return [_enrich_race(r) for r in rows]


@router.get("/races/{name}")
async def get_race(name: str, request: Request):
    db = request.app.state.db
    row = db.get_race(name)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Race '{name}' not found")
    return _enrich_race(row)
