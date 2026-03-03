"""Service layer for API V2 character endpoints."""

from __future__ import annotations

from app.models.contracts import CharacterV2, CharacterValidationResponseV2
from app.repositories.characters_v2 import CharacterRepositoryV2
from app.rules.engine_v2 import evaluate_feat_prerequisites


class CharacterServiceV2:
    """Character domain service for CRUD and validation operations."""

    def __init__(self, repository: CharacterRepositoryV2) -> None:
        self._repository = repository

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

    def create_character(self, payload: CharacterV2) -> CharacterV2:
        return self._repository.create_character(payload)

    def get_character(self, character_id: str) -> CharacterV2 | None:
        return self._repository.get_character(character_id)

    def list_characters(self, *, campaign_id: str | None = None, owner_id: str | None = None) -> list[CharacterV2]:
        return self._repository.list_characters(campaign_id=campaign_id, owner_id=owner_id)

    def update_character(self, character_id: str, payload: CharacterV2) -> CharacterV2:
        return self._repository.update_character(character_id, payload)

    def delete_character(self, character_id: str) -> None:
        self._repository.delete_character(character_id)

