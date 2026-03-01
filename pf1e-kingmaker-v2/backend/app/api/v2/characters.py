"""Character API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.contracts import CharacterV2
from app.rules.engine_v2 import evaluate_feat_prerequisites

router = APIRouter(prefix="/characters", tags=["characters-v2"])


@router.post("/validate")
def validate_character(character: CharacterV2):
    prereq_results = evaluate_feat_prerequisites(character)
    invalid = [r.model_dump() for r in prereq_results if not r.valid]
    return {
        "ok": len(invalid) == 0,
        "name": character.name,
        "total_levels": sum(c.level for c in character.class_levels),
        "feat_prereq_results": [r.model_dump() for r in prereq_results],
        "invalid_feats": invalid,
    }
