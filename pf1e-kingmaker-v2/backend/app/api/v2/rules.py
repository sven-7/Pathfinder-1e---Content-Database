"""Rules derivation API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.contracts import CharacterV2, DeriveResponseV2
from app.rules.engine_v2 import derive_stats

router = APIRouter(prefix="/rules", tags=["rules-v2"])

@router.post("/derive", response_model=DeriveResponseV2)
def derive(character: CharacterV2) -> DeriveResponseV2:
    return DeriveResponseV2(character=character, derived=derive_stats(character))
