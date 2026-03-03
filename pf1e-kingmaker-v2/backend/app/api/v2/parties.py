"""Party API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.models.campaigns_v1 import PartyCreateV1, PartyMemberCreateV1, PartyMemberV1, PartyV1
from app.repositories.campaigns_v1 import get_campaign_repository
from app.services.campaigns_v1 import CampaignServiceV1

router = APIRouter(prefix="/parties", tags=["parties-v2"])


def get_campaign_service() -> CampaignServiceV1:
    return CampaignServiceV1(get_campaign_repository())


@router.get("", response_model=list[PartyV1])
def list_parties(
    campaign_id: str | None = Query(default=None),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> list[PartyV1]:
    return service.list_parties(campaign_id=campaign_id)


@router.post("", response_model=PartyV1, status_code=201)
def create_party(
    payload: PartyCreateV1 = Body(...),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> PartyV1:
    try:
        return service.create_party(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Campaign '{payload.campaign_id}' was not found.") from exc


@router.get("/{party_id}", response_model=PartyV1)
def get_party(party_id: str, service: CampaignServiceV1 = Depends(get_campaign_service)) -> PartyV1:
    party = service.get_party(party_id)
    if party is None:
        raise HTTPException(status_code=404, detail=f"Party '{party_id}' was not found.")
    return party


@router.get("/{party_id}/members", response_model=list[PartyMemberV1])
def list_party_members(
    party_id: str,
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> list[PartyMemberV1]:
    try:
        return service.list_party_members(party_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Party '{party_id}' was not found.") from exc


@router.post("/{party_id}/members", response_model=PartyMemberV1, status_code=201)
def create_party_member(
    party_id: str,
    payload: PartyMemberCreateV1 = Body(...),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> PartyMemberV1:
    try:
        return service.add_party_member(party_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Party '{party_id}' was not found.") from exc
