"""DM-facing campaign foundation contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignBaseV2(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    gm_user_id: str | None = None
    status: Literal["draft", "active", "archived"] = "draft"
    in_world_date: str | None = None


class CampaignCreateV2(CampaignBaseV2):
    pass


class CampaignV2(CampaignBaseV2):
    id: str
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class PartyBaseV2(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    notes: str | None = None
    marching_order: list[str] = Field(default_factory=list)


class PartyCreateV2(PartyBaseV2):
    member_character_ids: list[str] = Field(default_factory=list)


class PartyV2(PartyBaseV2):
    id: str
    campaign_id: str
    member_character_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class NPCBaseV2(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: Literal["ally", "enemy", "neutral", "merchant", "quest_giver", "faction"] = "neutral"
    location: str | None = None
    disposition: Literal["friendly", "neutral", "hostile", "unknown"] = "unknown"
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class NPCCreateV2(NPCBaseV2):
    pass


class NPCV2(NPCBaseV2):
    id: str
    campaign_id: str
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class KingdomBaseV2(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    alignment: str | None = None
    government: str | None = None
    treasury_bp: int = Field(default=0, ge=0)
    unrest: int = Field(default=0, ge=0)
    consumption: int = Field(default=0, ge=0)
    notes: str | None = None


class KingdomUpsertV2(KingdomBaseV2):
    pass


class KingdomV2(KingdomBaseV2):
    id: str
    campaign_id: str
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class CampaignFoundationsSnapshotV2(BaseModel):
    campaign: CampaignV2
    parties: list[PartyV2] = Field(default_factory=list)
    npcs: list[NPCV2] = Field(default_factory=list)
    kingdom: KingdomV2 | None = None
