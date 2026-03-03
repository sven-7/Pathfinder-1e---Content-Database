"""Character API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.models.contracts import CharacterV2, CharacterValidationResponseV2
from app.persistence.database import get_db_session
from app.repositories.characters_v2 import CharacterRepositoryV2
from app.services.characters_v2 import CharacterServiceV2

router = APIRouter(prefix="/characters", tags=["characters-v2"])


def get_character_service(db: Session = Depends(get_db_session)) -> CharacterServiceV2:
    return CharacterServiceV2(CharacterRepositoryV2(db))


@router.post("/validate", response_model=CharacterValidationResponseV2)
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


@router.post("", response_model=CharacterV2, status_code=201)
def create_character(
    payload: CharacterV2 = Body(...),
    service: CharacterServiceV2 = Depends(get_character_service),
) -> CharacterV2:
    try:
        return service.create_character(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=f"Character '{str(exc)}' already exists.") from exc


@router.get("/{character_id}", response_model=CharacterV2)
def get_character(
    character_id: str,
    service: CharacterServiceV2 = Depends(get_character_service),
) -> CharacterV2:
    character = service.get_character(character_id)
    if character is None:
        raise HTTPException(status_code=404, detail=f"Character '{character_id}' was not found.")
    return character


@router.get("", response_model=list[CharacterV2])
def list_characters(
    campaign_id: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    service: CharacterServiceV2 = Depends(get_character_service),
) -> list[CharacterV2]:
    return service.list_characters(campaign_id=campaign_id, owner_id=owner_id)


@router.put("/{character_id}", response_model=CharacterV2)
def update_character(
    character_id: str,
    payload: CharacterV2 = Body(...),
    service: CharacterServiceV2 = Depends(get_character_service),
) -> CharacterV2:
    try:
        return service.update_character(character_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Character '{character_id}' was not found.") from exc


@router.delete("/{character_id}", status_code=204)
def delete_character(
    character_id: str,
    service: CharacterServiceV2 = Depends(get_character_service),
) -> Response:
    try:
        service.delete_character(character_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Character '{character_id}' was not found.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

