"""In-memory repository for DM foundation API scaffolding."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from app.models.dm_foundations import (
    CampaignCreateV2,
    CampaignV2,
    KingdomUpsertV2,
    KingdomV2,
    NPCCreateV2,
    NPCV2,
    PartyCreateV2,
    PartyV2,
)

_LOCK = Lock()

_CAMPAIGNS: dict[str, CampaignV2] = {}
_PARTIES_BY_CAMPAIGN: dict[str, dict[str, PartyV2]] = {}
_NPCS_BY_CAMPAIGN: dict[str, dict[str, NPCV2]] = {}
_KINGDOM_BY_CAMPAIGN: dict[str, KingdomV2] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def reset_state() -> None:
    with _LOCK:
        _CAMPAIGNS.clear()
        _PARTIES_BY_CAMPAIGN.clear()
        _NPCS_BY_CAMPAIGN.clear()
        _KINGDOM_BY_CAMPAIGN.clear()


def list_campaigns() -> list[CampaignV2]:
    with _LOCK:
        campaigns = sorted(_CAMPAIGNS.values(), key=lambda item: (item.created_at, item.name.lower()))
        return [campaign.model_copy(deep=True) for campaign in campaigns]


def get_campaign(campaign_id: str) -> CampaignV2 | None:
    with _LOCK:
        campaign = _CAMPAIGNS.get(campaign_id)
        return campaign.model_copy(deep=True) if campaign else None


def create_campaign(payload: CampaignCreateV2) -> CampaignV2:
    with _LOCK:
        now = _utc_now()
        campaign_id = str(uuid4())
        campaign = CampaignV2(id=campaign_id, created_at=now, updated_at=now, **payload.model_dump())
        _CAMPAIGNS[campaign_id] = campaign
        _PARTIES_BY_CAMPAIGN.setdefault(campaign_id, {})
        _NPCS_BY_CAMPAIGN.setdefault(campaign_id, {})
        return campaign.model_copy(deep=True)


def list_parties(campaign_id: str) -> list[PartyV2]:
    with _LOCK:
        parties = _PARTIES_BY_CAMPAIGN.get(campaign_id, {})
        ordered = sorted(parties.values(), key=lambda item: (item.created_at, item.name.lower()))
        return [party.model_copy(deep=True) for party in ordered]


def create_party(campaign_id: str, payload: PartyCreateV2) -> PartyV2:
    with _LOCK:
        if campaign_id not in _CAMPAIGNS:
            raise KeyError(campaign_id)
        now = _utc_now()
        party_id = str(uuid4())
        party = PartyV2(
            id=party_id,
            campaign_id=campaign_id,
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        campaign_parties = _PARTIES_BY_CAMPAIGN.setdefault(campaign_id, {})
        campaign_parties[party_id] = party
        return party.model_copy(deep=True)


def list_npcs(campaign_id: str) -> list[NPCV2]:
    with _LOCK:
        npcs = _NPCS_BY_CAMPAIGN.get(campaign_id, {})
        ordered = sorted(npcs.values(), key=lambda item: (item.created_at, item.name.lower()))
        return [npc.model_copy(deep=True) for npc in ordered]


def create_npc(campaign_id: str, payload: NPCCreateV2) -> NPCV2:
    with _LOCK:
        if campaign_id not in _CAMPAIGNS:
            raise KeyError(campaign_id)
        now = _utc_now()
        npc_id = str(uuid4())
        npc = NPCV2(
            id=npc_id,
            campaign_id=campaign_id,
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        campaign_npcs = _NPCS_BY_CAMPAIGN.setdefault(campaign_id, {})
        campaign_npcs[npc_id] = npc
        return npc.model_copy(deep=True)


def get_kingdom(campaign_id: str) -> KingdomV2 | None:
    with _LOCK:
        kingdom = _KINGDOM_BY_CAMPAIGN.get(campaign_id)
        return kingdom.model_copy(deep=True) if kingdom else None


def upsert_kingdom(campaign_id: str, payload: KingdomUpsertV2) -> KingdomV2:
    with _LOCK:
        if campaign_id not in _CAMPAIGNS:
            raise KeyError(campaign_id)

        now = _utc_now()
        existing = _KINGDOM_BY_CAMPAIGN.get(campaign_id)
        if existing:
            kingdom = existing.model_copy(update={**payload.model_dump(), "updated_at": now})
        else:
            kingdom = KingdomV2(
                id=str(uuid4()),
                campaign_id=campaign_id,
                created_at=now,
                updated_at=now,
                **payload.model_dump(),
            )

        _KINGDOM_BY_CAMPAIGN[campaign_id] = kingdom
        return kingdom.model_copy(deep=True)
