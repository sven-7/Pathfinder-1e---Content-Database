"""Service layer for API V2 rules derivation endpoints."""

from __future__ import annotations

from app.models.contracts import CharacterV2, DeriveResponseV2
from app.rules.engine_v2 import derive_stats


class RulesServiceV2:
    """Rules derivation service wrapping deterministic engine evaluation."""

    def derive(self, character: CharacterV2) -> DeriveResponseV2:
        return DeriveResponseV2(character=character, derived=derive_stats(character))

