"""DM campaign foundation API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

import app.api.v2.dm_store as dm_store
from app.models.dm_foundations import (
    CampaignCreateV2,
    CampaignFoundationsSnapshotV2,
    CampaignV2,
    KingdomUpsertV2,
    KingdomV2,
    NPCCreateV2,
    NPCV2,
    PartyCreateV2,
    PartyV2,
)

router = APIRouter(prefix="/campaigns", tags=["dm-foundations-v2"])


def _require_campaign(campaign_id: str) -> CampaignV2:
    campaign = dm_store.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' was not found.")
    return campaign


@router.get("", response_model=list[CampaignV2])
def list_campaigns():
    return dm_store.list_campaigns()


@router.post("", response_model=CampaignV2, status_code=201)
def create_campaign(payload: CampaignCreateV2):
    return dm_store.create_campaign(payload)


@router.get("/{campaign_id}", response_model=CampaignV2)
def get_campaign(campaign_id: str):
    return _require_campaign(campaign_id)


@router.get("/{campaign_id}/foundations", response_model=CampaignFoundationsSnapshotV2)
def get_foundations_snapshot(campaign_id: str):
    campaign = _require_campaign(campaign_id)
    return CampaignFoundationsSnapshotV2(
        campaign=campaign,
        parties=dm_store.list_parties(campaign_id),
        npcs=dm_store.list_npcs(campaign_id),
        kingdom=dm_store.get_kingdom(campaign_id),
    )


@router.get("/{campaign_id}/parties", response_model=list[PartyV2])
def list_parties(campaign_id: str):
    _require_campaign(campaign_id)
    return dm_store.list_parties(campaign_id)


@router.post("/{campaign_id}/parties", response_model=PartyV2, status_code=201)
def create_party(campaign_id: str, payload: PartyCreateV2):
    _require_campaign(campaign_id)
    return dm_store.create_party(campaign_id, payload)


@router.get("/{campaign_id}/npcs", response_model=list[NPCV2])
def list_npcs(campaign_id: str):
    _require_campaign(campaign_id)
    return dm_store.list_npcs(campaign_id)


@router.post("/{campaign_id}/npcs", response_model=NPCV2, status_code=201)
def create_npc(campaign_id: str, payload: NPCCreateV2):
    _require_campaign(campaign_id)
    return dm_store.create_npc(campaign_id, payload)


@router.get("/{campaign_id}/kingdom", response_model=KingdomV2 | None)
def get_kingdom(campaign_id: str):
    _require_campaign(campaign_id)
    return dm_store.get_kingdom(campaign_id)


@router.put("/{campaign_id}/kingdom", response_model=KingdomV2)
def upsert_kingdom(campaign_id: str, payload: KingdomUpsertV2):
    _require_campaign(campaign_id)
    return dm_store.upsert_kingdom(campaign_id, payload)
