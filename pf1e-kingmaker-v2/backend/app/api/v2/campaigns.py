"""Campaign API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.models.campaigns_v1 import (
    CampaignCreateV1,
    CampaignV1,
    RuleOverrideCreateV1,
    RuleOverrideRecordV1,
    RuleOverrideResolutionV1,
)
from app.repositories.campaigns_v1 import get_campaign_repository
from app.services.campaigns_v1 import CampaignServiceV1

router = APIRouter(prefix="/campaigns", tags=["campaigns-v2"])


def get_campaign_service() -> CampaignServiceV1:
    return CampaignServiceV1(get_campaign_repository())


@router.get("", response_model=list[CampaignV1])
def list_campaigns(
    owner_id: str | None = Query(default=None),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> list[CampaignV1]:
    return service.list_campaigns(owner_id=owner_id)


@router.post("", response_model=CampaignV1, status_code=201)
def create_campaign(
    payload: CampaignCreateV1 = Body(...),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> CampaignV1:
    return service.create_campaign(payload)


@router.get("/rule-overrides/global", response_model=list[RuleOverrideRecordV1])
def list_global_rule_overrides(
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> list[RuleOverrideRecordV1]:
    return service.list_global_overrides()


@router.post("/rule-overrides/global", response_model=RuleOverrideRecordV1, status_code=201)
def create_global_rule_override(
    payload: RuleOverrideCreateV1 = Body(...),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> RuleOverrideRecordV1:
    try:
        return service.create_global_override(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{campaign_id}", response_model=CampaignV1)
def get_campaign(campaign_id: str, service: CampaignServiceV1 = Depends(get_campaign_service)) -> CampaignV1:
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' was not found.")
    return campaign


@router.get("/{campaign_id}/rule-overrides", response_model=list[RuleOverrideRecordV1])
def list_campaign_rule_overrides(
    campaign_id: str,
    character_id: str | None = Query(default=None),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> list[RuleOverrideRecordV1]:
    if service.get_campaign(campaign_id) is None:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' was not found.")
    return service.list_campaign_overrides(campaign_id=campaign_id, character_id=character_id)


@router.post("/{campaign_id}/rule-overrides", response_model=RuleOverrideRecordV1, status_code=201)
def create_campaign_rule_override(
    campaign_id: str,
    payload: RuleOverrideCreateV1 = Body(...),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> RuleOverrideRecordV1:
    if service.get_campaign(campaign_id) is None:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' was not found.")
    return service.create_campaign_override(campaign_id, payload)


@router.get("/{campaign_id}/rule-overrides/resolve", response_model=RuleOverrideResolutionV1)
def resolve_campaign_rule_overrides(
    campaign_id: str,
    character_id: str | None = Query(default=None),
    service: CampaignServiceV1 = Depends(get_campaign_service),
) -> RuleOverrideResolutionV1:
    if service.get_campaign(campaign_id) is None:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' was not found.")
    return service.resolve_overrides(campaign_id=campaign_id, character_id=character_id)
