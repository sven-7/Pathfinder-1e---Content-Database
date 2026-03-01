"""Character API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.contracts import CharacterV2

router = APIRouter(prefix="/characters", tags=["characters-v2"])


@router.post("/validate")
def validate_character(character: CharacterV2):
    return {
        "ok": True,
        "name": character.name,
        "total_levels": sum(c.level for c in character.class_levels),
    }
