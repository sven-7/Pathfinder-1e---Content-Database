"""Character API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from app.models.contracts import CharacterV2, CharacterValidationResponseV2
from app.services.characters_v2 import CharacterServiceV2

router = APIRouter(prefix="/characters", tags=["characters-v2"])


def get_character_service() -> CharacterServiceV2:
    return CharacterServiceV2()


@router.post(
    "/validate",
    response_model=CharacterValidationResponseV2,
    summary="Validate a character build against deterministic feat prerequisite checks.",
)
def validate_character(
    character: CharacterV2 = Body(
        ...,
        openapi_examples={
            "kairon": {
                "summary": "Kairon level 9 sample payload",
                "value": CharacterV2.model_config.get("json_schema_extra", {}).get("example", {}),
            }
        },
    ),
    service: CharacterServiceV2 = Depends(get_character_service),
) -> CharacterValidationResponseV2:
    return service.validate_character(character)
