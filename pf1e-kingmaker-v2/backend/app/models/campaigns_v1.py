"""Campaign-domain contracts for DM foundation APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignCreateV1(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    owner_id: str = Field(min_length=1, max_length=120)
    description: str | None = None
    status: Literal["draft", "active", "paused", "archived"] = "draft"
    gm_id: str | None = None
    player_id: str | None = None


class CampaignV1(CampaignCreateV1):
    id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PartyMemberCreateV1(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    role: Literal["pc", "npc", "companion", "guest"] = "pc"
    character_id: str | None = None
    owner_id: str | None = None
    gm_id: str | None = None
    player_id: str | None = None


class PartyMemberV1(PartyMemberCreateV1):
    id: str
    party_id: str
    created_at: datetime = Field(default_factory=utc_now)


class PartyCreateV1(BaseModel):
    campaign_id: str
    name: str = Field(min_length=1, max_length=120)
    owner_id: str = Field(min_length=1, max_length=120)
    notes: str | None = None
    gm_id: str | None = None
    player_id: str | None = None
    members: list[PartyMemberCreateV1] = Field(default_factory=list)


class PartyV1(BaseModel):
    id: str
    campaign_id: str
    name: str
    owner_id: str
    notes: str | None = None
    gm_id: str | None = None
    player_id: str | None = None
    members: list[PartyMemberV1] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EncounterCreateV1(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    owner_id: str = Field(min_length=1, max_length=120)
    status: Literal["planned", "active", "resolved", "archived"] = "planned"
    notes: str | None = None
    gm_id: str | None = None
    player_id: str | None = None


class EncounterV1(EncounterCreateV1):
    id: str
    session_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SessionCreateV1(BaseModel):
    campaign_id: str
    name: str = Field(min_length=1, max_length=120)
    owner_id: str = Field(min_length=1, max_length=120)
    scheduled_for: str | None = None
    status: Literal["planned", "active", "closed", "archived"] = "planned"
    notes: str | None = None
    gm_id: str | None = None
    player_id: str | None = None


class SessionV1(BaseModel):
    id: str
    campaign_id: str
    name: str
    owner_id: str
    scheduled_for: str | None = None
    status: Literal["planned", "active", "closed", "archived"] = "planned"
    notes: str | None = None
    gm_id: str | None = None
    player_id: str | None = None
    encounters: list[EncounterV1] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RuleOverrideCreateV1(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    operation: Literal["add", "set"] = "add"
    value: int | float = 0
    source: str = Field(default="dm_override", min_length=1, max_length=120)
    owner_id: str | None = None
    character_id: str | None = None
    gm_id: str | None = None
    player_id: str | None = None


class RuleOverrideRecordV1(BaseModel):
    id: str
    scope: Literal["global", "campaign", "character"]
    campaign_id: str | None = None
    key: str
    operation: Literal["add", "set"]
    value: int | float
    source: str
    owner_id: str | None = None
    character_id: str | None = None
    gm_id: str | None = None
    player_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RuleOverrideResolutionV1(BaseModel):
    campaign_id: str
    character_id: str | None = None
    merge_order: Literal["global->campaign->character"] = "global->campaign->character"
    ordered_overrides: list[RuleOverrideRecordV1] = Field(default_factory=list)
    effective_values: dict[str, int | float] = Field(default_factory=dict)

