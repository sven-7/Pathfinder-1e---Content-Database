"""Session API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.campaigns_v1 import EncounterCreateV1, EncounterV1, SessionCreateV1, SessionV1
from app.persistence.database import get_db_session
from app.repositories.campaigns_v1 import CampaignRepositoryV1
from app.services.campaigns_v1 import CampaignServiceV1

router = APIRouter(prefix="/sessions", tags=["sessions-v2"])


def get_campaign_service(db: Session = Depends(get_db_session)) -> CampaignServiceV1:
    return CampaignServiceV1(CampaignRepositoryV1(db))


@router.get("", response_model=list[SessionV1])
def list_sessions(
    campaign_id: str | None = Query(default=None),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> list[SessionV1]:
    return service.list_sessions(campaign_id=campaign_id)


@router.post("", response_model=SessionV1, status_code=201)
def create_session(
    payload: SessionCreateV1 = Body(...),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> SessionV1:
    try:
        return service.create_session(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Campaign '{payload.campaign_id}' was not found.") from exc


@router.get("/{session_id}", response_model=SessionV1)
def get_session(
    session_id: str,
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> SessionV1:
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' was not found.")
    return session


@router.get("/{session_id}/encounters", response_model=list[EncounterV1])
def list_session_encounters(
    session_id: str,
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> list[EncounterV1]:
    try:
        return service.list_encounters(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' was not found.") from exc


@router.post("/{session_id}/encounters", response_model=EncounterV1, status_code=201)
def create_session_encounter(
    session_id: str,
    payload: EncounterCreateV1 = Body(...),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> EncounterV1:
    try:
        return service.create_encounter(session_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' was not found.") from exc

