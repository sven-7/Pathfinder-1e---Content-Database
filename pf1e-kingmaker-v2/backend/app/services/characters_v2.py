"""Service layer for API V2 character endpoints."""

from __future__ import annotations

from app.models.contracts import CharacterV2, CharacterValidationResponseV2
from app.rules.engine_v2 import evaluate_feat_prerequisites


class CharacterServiceV2:
    """Character domain service for validation and legality checks."""

    def validate_character(self, character: CharacterV2) -> CharacterValidationResponseV2:
        prereq_results = evaluate_feat_prerequisites(character)
        invalid = [r for r in prereq_results if not r.valid]
        return CharacterValidationResponseV2(
            ok=len(invalid) == 0,
            name=character.name,
            total_levels=sum(c.level for c in character.class_levels),
            feat_prereq_results=prereq_results,
            invalid_feats=invalid,
        )

