"""GET /api/races — race listing and detail."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["races"])

# ── Canonical playable race data ──────────────────────────────────────────── #
# The scraped DB has 423 rows, mostly non-playable content scraped alongside
# class feature tables and other page fragments.  We whitelist the 37 canonical
# playable races from the Advanced Race Guide (Core + Featured + Uncommon) and
# provide hardcoded ability modifiers / sizes / speeds since the scraped data
# for these fields is incomplete.

_RACE_DATA: dict[str, dict] = {
    # ── Core (7) ─────────────────────────────────────────────────────────────
    "Dwarves":    {"race_type": "core",     "ability_modifiers": {"con": 2, "wis": 2, "cha": -2},           "size": "Medium", "base_speed": 20, "flexible_bonus": False},
    "Elves":      {"race_type": "core",     "ability_modifiers": {"dex": 2, "int": 2, "con": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Gnomes":     {"race_type": "core",     "ability_modifiers": {"con": 2, "cha": 2, "str": -2},           "size": "Small",  "base_speed": 20, "flexible_bonus": False},
    "Half-Elves": {"race_type": "core",     "ability_modifiers": {},                                        "size": "Medium", "base_speed": 30, "flexible_bonus": True},
    "Half-Orcs":  {"race_type": "core",     "ability_modifiers": {},                                        "size": "Medium", "base_speed": 30, "flexible_bonus": True},
    "Halflings":  {"race_type": "core",     "ability_modifiers": {"dex": 2, "cha": 2, "str": -2},           "size": "Small",  "base_speed": 20, "flexible_bonus": False},
    "Humans":     {"race_type": "core",     "ability_modifiers": {},                                        "size": "Medium", "base_speed": 30, "flexible_bonus": True},
    # ── Featured (16) ────────────────────────────────────────────────────────
    "Aasimar":    {"race_type": "featured", "ability_modifiers": {"wis": 2, "cha": 2},                      "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Catfolk":    {"race_type": "featured", "ability_modifiers": {"dex": 2, "cha": 2, "wis": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Dhampir":    {"race_type": "featured", "ability_modifiers": {"dex": 2, "cha": 2, "con": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Drow":       {"race_type": "featured", "ability_modifiers": {"dex": 2, "cha": 2, "con": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Fetchling":  {"race_type": "featured", "ability_modifiers": {"dex": 2, "cha": 2, "wis": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Goblin":     {"race_type": "featured", "ability_modifiers": {"dex": 4, "str": -2, "cha": -2},          "size": "Small",  "base_speed": 30, "flexible_bonus": False},
    "Hobgoblin":  {"race_type": "featured", "ability_modifiers": {"dex": 2, "con": 2},                      "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Ifrit":      {"race_type": "featured", "ability_modifiers": {"dex": 2, "cha": 2, "wis": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Kobold":     {"race_type": "featured", "ability_modifiers": {"dex": 2, "str": -4, "con": -2},          "size": "Small",  "base_speed": 30, "flexible_bonus": False},
    "Orc":        {"race_type": "featured", "ability_modifiers": {"str": 4, "int": -2, "wis": -2, "cha": -2}, "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Oread":      {"race_type": "featured", "ability_modifiers": {"str": 2, "wis": 2, "dex": -2},           "size": "Medium", "base_speed": 20, "flexible_bonus": False},
    "Ratfolk":    {"race_type": "featured", "ability_modifiers": {"dex": 2, "int": 2, "str": -2},           "size": "Small",  "base_speed": 20, "flexible_bonus": False},
    "Sylph":      {"race_type": "featured", "ability_modifiers": {"dex": 2, "int": 2, "con": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Tengu":      {"race_type": "featured", "ability_modifiers": {"dex": 2, "wis": 2, "con": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Tiefling":   {"race_type": "featured", "ability_modifiers": {"dex": 2, "int": 2, "cha": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Undine":     {"race_type": "featured", "ability_modifiers": {"dex": 2, "wis": 2, "str": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    # ── Uncommon (14) ────────────────────────────────────────────────────────
    "Changeling": {"race_type": "uncommon", "ability_modifiers": {"wis": 2, "con": -2},                     "size": "Medium", "base_speed": 30, "flexible_bonus": True},
    "Duergar":    {"race_type": "uncommon", "ability_modifiers": {"con": 2, "wis": 2, "cha": -4},           "size": "Medium", "base_speed": 20, "flexible_bonus": False},
    "Grippli":    {"race_type": "uncommon", "ability_modifiers": {"dex": 2, "wis": 2, "str": -2},           "size": "Small",  "base_speed": 30, "flexible_bonus": False},
    "Kitsune":    {"race_type": "uncommon", "ability_modifiers": {"dex": 2, "cha": 2, "str": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Merfolk":    {"race_type": "uncommon", "ability_modifiers": {"dex": 2, "con": 2, "cha": 2},            "size": "Medium", "base_speed": 5,  "flexible_bonus": False},
    "Nagaji":     {"race_type": "uncommon", "ability_modifiers": {"str": 2, "cha": 2, "int": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Samsaran":   {"race_type": "uncommon", "ability_modifiers": {"int": 2, "wis": 2, "con": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Strix":      {"race_type": "uncommon", "ability_modifiers": {"dex": 2, "cha": -2},                     "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Suli":       {"race_type": "uncommon", "ability_modifiers": {"str": 2, "cha": 2, "int": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Svirfneblin":{"race_type": "uncommon", "ability_modifiers": {"dex": 2, "wis": 2, "str": -2, "cha": -4}, "size": "Small", "base_speed": 20, "flexible_bonus": False},
    "Vanara":     {"race_type": "uncommon", "ability_modifiers": {"dex": 2, "wis": 2, "cha": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Vishkanya":  {"race_type": "uncommon", "ability_modifiers": {"dex": 2, "cha": 2, "wis": -2},           "size": "Medium", "base_speed": 30, "flexible_bonus": False},
    "Wayang":     {"race_type": "uncommon", "ability_modifiers": {"dex": 2, "int": 2, "wis": -2},           "size": "Small",  "base_speed": 20, "flexible_bonus": False},
    "Wyvaran":    {"race_type": "uncommon", "ability_modifiers": {"int": 2, "cha": 2},                      "size": "Medium", "base_speed": 30, "flexible_bonus": False},
}

_PLAYABLE_NAMES = tuple(_RACE_DATA.keys())


def _enrich_race(row: dict) -> dict:
    name = row["name"]
    data = _RACE_DATA.get(name, {})
    return {
        "id": row["id"],
        "name": name,
        "race_type": data.get("race_type") or row.get("race_type") or "other",
        "size": data.get("size") or row.get("size") or "Medium",
        "base_speed": data.get("base_speed") or row.get("base_speed") or 30,
        "ability_modifiers": data.get("ability_modifiers") or {},
        "flexible_bonus": data.get("flexible_bonus", False),
        "type": row.get("type") or "Humanoid",
        "description": row.get("description") or "",
        "url": row.get("url") or "",
    }


@router.get("/races")
async def list_races(request: Request):
    db = request.app.state.db
    placeholders = ",".join("?" * len(_PLAYABLE_NAMES))
    rows = db._many(
        f"""SELECT * FROM races
           WHERE name IN ({placeholders})
           ORDER BY
             CASE race_type
               WHEN 'core'     THEN 0
               WHEN 'featured' THEN 1
               WHEN 'uncommon' THEN 2
               ELSE 3
             END, name""",
        _PLAYABLE_NAMES,
    )
    # Some names may not be in DB yet — supplement from hardcoded data
    found = {r["name"] for r in rows}
    result = [_enrich_race(r) for r in rows]
    # Add any whitelisted races not in DB (stub entries)
    for name, data in _RACE_DATA.items():
        if name not in found:
            result.append({
                "id": None,
                "name": name,
                **{k: v for k, v in data.items()},
                "type": "Humanoid",
                "description": "",
                "url": "",
            })
    # Sort: core first, then featured, then uncommon, alphabetical within group
    order = {"core": 0, "featured": 1, "uncommon": 2}
    result.sort(key=lambda r: (order.get(r["race_type"], 3), r["name"]))
    return result


@router.get("/races/{name}")
async def get_race(name: str, request: Request):
    db = request.app.state.db
    row = db.get_race(name)
    if row is None:
        # Try hardcoded data as fallback
        if name in _RACE_DATA:
            data = _RACE_DATA[name]
            return {"id": None, "name": name, **data, "type": "Humanoid", "description": "", "url": ""}
        raise HTTPException(status_code=404, detail=f"Race '{name}' not found")
    return _enrich_race(row)
