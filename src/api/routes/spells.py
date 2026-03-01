"""GET /api/spells — spell listing with optional class/level filtering."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["spells"])


@router.get("/spells")
async def list_spells(
    request: Request,
    class_name: str | None = Query(default=None, description="Filter by class name (e.g. 'wizard')"),
    level: int | None = Query(default=None, description="Filter by spell level (0-9)"),
    search: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    source_ids: str | None = Query(default=None, description="Comma-separated source IDs to filter by"),
):
    db = request.app.state.db

    # Build optional source filter clause
    source_filter = ""
    source_params: tuple = ()
    if source_ids:
        allowed = [int(s) for s in source_ids.split(",") if s.strip()]
        if allowed:
            placeholders = ",".join("?" for _ in allowed)
            source_filter = f" AND s.source_id IN ({placeholders})"
            source_params = tuple(allowed)

    if class_name and level is not None:
        rows = db._many(
            f"""SELECT s.id, s.name, s.school, s.subschool, s.descriptors,
                      s.casting_time, s.components, s.range, s.duration,
                      s.saving_throw, s.description, s.url, scl.level as spell_level
               FROM spells s
               JOIN spell_class_levels scl ON scl.spell_id = s.id
               WHERE LOWER(scl.class_name) = LOWER(?)
                 AND scl.level = ?{source_filter}
               ORDER BY s.name
               LIMIT ?""",
            (class_name, level, *source_params, limit),
        )
    elif class_name:
        rows = db._many(
            f"""SELECT s.id, s.name, s.school, s.subschool, s.descriptors,
                      s.casting_time, s.components, s.range, s.duration,
                      s.saving_throw, s.description, s.url,
                      MIN(scl.level) as spell_level
               FROM spells s
               JOIN spell_class_levels scl ON scl.spell_id = s.id
               WHERE LOWER(scl.class_name) = LOWER(?){source_filter}
               GROUP BY s.id
               ORDER BY MIN(scl.level), s.name
               LIMIT ?""",
            (class_name, *source_params, limit),
        )
    elif level is not None:
        rows = db._many(
            f"""SELECT DISTINCT s.id, s.name, s.school, s.subschool, s.descriptors,
                      s.casting_time, s.components, s.range, s.duration,
                      s.saving_throw, s.description, s.url, scl.level as spell_level
               FROM spells s
               JOIN spell_class_levels scl ON scl.spell_id = s.id
               WHERE scl.level = ?{source_filter}
               ORDER BY s.name
               LIMIT ?""",
            (level, *source_params, limit),
        )
    else:
        # No join on scl — use bare table alias
        bare_source_filter = ""
        if source_ids:
            allowed = [int(s) for s in source_ids.split(",") if s.strip()]
            if allowed:
                placeholders = ",".join("?" for _ in allowed)
                bare_source_filter = f" WHERE source_id IN ({placeholders})"
                source_params = tuple(allowed)
            else:
                source_params = ()
        rows = db._many(
            f"""SELECT id, name, school, subschool, descriptors,
                      casting_time, components, range, duration,
                      saving_throw, description, url
               FROM spells{bare_source_filter}
               ORDER BY name
               LIMIT ?""",
            (*source_params, limit),
        )

    if search:
        s = search.lower()
        rows = [r for r in rows if s in r["name"].lower()]

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "school": r.get("school") or "",
            "subschool": r.get("subschool") or "",
            "spell_level": r.get("spell_level"),
            "casting_time": r.get("casting_time") or "",
            "components": r.get("components") or "",
            "range": r.get("range") or "",
            "duration": r.get("duration") or "",
            "saving_throw": r.get("saving_throw") or "",
            "description": (r.get("description") or "")[:200],
            "url": r.get("url") or "",
        }
        for r in rows
    ]
