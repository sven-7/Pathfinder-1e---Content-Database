"""GET /api/classes — class listing, detail, and archetypes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from src.character_creator.builder import CLASS_HIT_DIE, CLASS_SKILL_RANKS

router = APIRouter(tags=["classes"])

# Classes available for character creation (excludes NPC classes)
_EXCLUDE_TYPES = {"npc"}

_SAVE_LABELS = {"good": "Good", "poor": "Poor"}
_BAB_LABELS = {"full": "Full (+1/lvl)", "three_quarter": "¾ (+3/4 lvl)", "half": "Half (+1/2 lvl)"}


def _enrich_class(row: dict) -> dict:
    name = row["name"]
    hit_die = row.get("hit_die") or CLASS_HIT_DIE.get(name, "d8")
    skill_ranks = row.get("skill_ranks_per_level") or CLASS_SKILL_RANKS.get(name, 2)
    return {
        "id": row["id"],
        "name": name,
        "class_type": row.get("class_type") or "base",
        "hit_die": hit_die,
        "skill_ranks_per_level": skill_ranks,
        "bab_progression": row.get("bab_progression") or "three_quarter",
        "fort_progression": row.get("fort_progression") or "poor",
        "ref_progression": row.get("ref_progression") or "poor",
        "will_progression": row.get("will_progression") or "poor",
        "spellcasting_type": row.get("spellcasting_type"),
        "spellcasting_style": row.get("spellcasting_style"),
        "alignment_restriction": row.get("alignment_restriction") or "",
        "description": row.get("description") or "",
        "url": row.get("url") or "",
    }


@router.get("/classes")
async def list_classes(request: Request):
    db = request.app.state.db
    rows = db._many(
        """SELECT * FROM classes
           WHERE class_type NOT IN ('npc')
           ORDER BY
             CASE class_type
               WHEN 'base'      THEN 0
               WHEN 'hybrid'    THEN 1
               WHEN 'unchained' THEN 2
               WHEN 'occult'    THEN 3
               WHEN 'prestige'  THEN 4
               ELSE 5
             END, name"""
    )
    return [_enrich_class(r) for r in rows]


@router.get("/classes/{name}/archetypes")
async def get_class_archetypes(
    name: str,
    request: Request,
    source_ids: str | None = Query(default=None, description="Comma-separated source IDs to filter by"),
):
    db = request.app.state.db
    cls_row = db.get_class(name)
    if cls_row is None:
        raise HTTPException(status_code=404, detail=f"Class '{name}' not found")

    if source_ids:
        allowed = [int(s) for s in source_ids.split(",") if s.strip()]
        if allowed:
            placeholders = ",".join("?" for _ in allowed)
            archetypes = db._many(
                f"SELECT * FROM archetypes WHERE class_id = ? AND source_id IN ({placeholders}) ORDER BY name",
                (cls_row["id"], *allowed),
            )
        else:
            archetypes = db._many(
                "SELECT * FROM archetypes WHERE class_id = ? AND is_paizo_official = 1 ORDER BY name",
                (cls_row["id"],),
            )
    else:
        archetypes = db._many(
            "SELECT * FROM archetypes WHERE class_id = ? AND is_paizo_official = 1 ORDER BY name",
            (cls_row["id"],),
        )

    return [
        {
            "id": a["id"],
            "name": a["name"],
            "class_name": name,
            "description": a.get("description") or "",
            "url": a.get("url") or "",
        }
        for a in archetypes
    ]


@router.get("/classes/{name}/progression")
async def get_class_progression(name: str, request: Request):
    db = request.app.state.db
    cls_row = db.get_class(name)
    if cls_row is None:
        raise HTTPException(status_code=404, detail=f"Class '{name}' not found")
    progression = db.get_class_progression(cls_row["id"])
    return progression


@router.get("/classes/{name}/features")
async def get_class_features(
    name: str,
    request: Request,
    feature_type: str | None = Query(default=None, description="Filter by feature_type"),
    exact: bool = Query(default=False, description="Exact match on feature_type (no prefix)"),
):
    db = request.app.state.db
    cls_row = db.get_class(name)
    if cls_row is None:
        raise HTTPException(status_code=404, detail=f"Class '{name}' not found")
    features = db.get_class_features(cls_row["id"])
    if feature_type:
        ft_lower = feature_type.lower()
        if exact:
            features = [
                f for f in features
                if (f.get("feature_type") or "").lower() == ft_lower
            ]
        else:
            # Prefix match: "Arcanist Exploit" also returns "Arcanist Exploit - Greater" etc.
            features = [
                f for f in features
                if (f.get("feature_type") or "").lower().startswith(ft_lower)
            ]
    return features
