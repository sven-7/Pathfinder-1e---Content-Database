"""Rules derivation API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from app.models.contracts import CharacterV2, DeriveResponseV2
from app.services.rules_v2 import RulesServiceV2

router = APIRouter(prefix="/rules", tags=["rules-v2"])


def get_rules_service() -> RulesServiceV2:
    return RulesServiceV2()


@router.post(
    "/derive",
    response_model=DeriveResponseV2,
    summary="Derive deterministic PF1e stats and an explainable breakdown trace.",
)
def derive(
    character: CharacterV2 = Body(
        ...,
        openapi_examples={
            "kairon": {
                "summary": "Kairon level 9 sample payload",
                "value": CharacterV2.model_config.get("json_schema_extra", {}).get("example", {}),
            }
        },
    ),
    service: RulesServiceV2 = Depends(get_rules_service),
) -> DeriveResponseV2:
    return service.derive(character)
