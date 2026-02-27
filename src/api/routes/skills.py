"""GET /api/skills — skill listing."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.rules_engine.skills import _ability_for_skill

router = APIRouter(tags=["skills"])

# PF1e skill list — trained-only and untrained flags
_TRAINED_ONLY = {
    "disable device", "fly", "handle animal", "knowledge",
    "linguistics", "profession", "sleight of hand", "spellcraft",
    "use magic device",
}


@router.get("/skills")
async def list_skills(request: Request):
    db = request.app.state.db
    rows = db.get_all_skills()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "ability": _ability_for_skill(r["name"]),
            "trained_only": any(r["name"].lower().startswith(t) for t in _TRAINED_ONLY),
            "armor_check_penalty": r.get("armor_check_penalty", False),
        }
        for r in rows
    ]


@router.get("/skills/class/{class_name}")
async def get_class_skills(class_name: str, request: Request):
    """Return class skills for a given class."""
    db = request.app.state.db
    cls_row = db.get_class(class_name)
    if cls_row is None:
        return []
    class_skills = db.get_class_skills(cls_row["id"])
    return [s["name"] for s in class_skills]
