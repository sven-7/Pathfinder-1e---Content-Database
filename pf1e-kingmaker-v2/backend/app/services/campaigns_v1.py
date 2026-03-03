"""Service layer for campaign-domain V1 endpoints."""

from __future__ import annotations

from uuid import uuid4

from app.models.campaigns_v1 import (
    CampaignCreateV1,
    CampaignV1,
    EncounterCreateV1,
    EncounterV1,
    PartyCreateV1,
    PartyMemberCreateV1,
    PartyMemberV1,
    PartyV1,
    RuleOverrideCreateV1,
    RuleOverrideRecordV1,
    RuleOverrideResolutionV1,
    SessionCreateV1,
    SessionV1,
    utc_now,
)
from app.repositories.campaigns_v1 import CampaignRepositoryV1


class CampaignServiceV1:
    """Campaign domain service with deterministic override merge behavior."""

    def __init__(self, repository: CampaignRepositoryV1) -> None:
        self._repository = repository

    def list_campaigns(self, owner_id: str | None = None) -> list[CampaignV1]:
        return self._repository.list_campaigns(owner_id=owner_id)

    def create_campaign(self, payload: CampaignCreateV1) -> CampaignV1:
        return self._repository.create_campaign(payload)

    def get_campaign(self, campaign_id: str) -> CampaignV1 | None:
        return self._repository.get_campaign(campaign_id)

    def list_parties(self, campaign_id: str | None = None) -> list[PartyV1]:
        return self._repository.list_parties(campaign_id=campaign_id)

    def create_party(self, payload: PartyCreateV1) -> PartyV1:
        return self._repository.create_party(payload)

    def get_party(self, party_id: str) -> PartyV1 | None:
        return self._repository.get_party(party_id)

    def add_party_member(self, party_id: str, payload: PartyMemberCreateV1) -> PartyMemberV1:
        return self._repository.add_party_member(party_id, payload)

    def list_party_members(self, party_id: str) -> list[PartyMemberV1]:
        return self._repository.list_party_members(party_id)

    def list_sessions(self, campaign_id: str | None = None) -> list[SessionV1]:
        return self._repository.list_sessions(campaign_id=campaign_id)

    def create_session(self, payload: SessionCreateV1) -> SessionV1:
        return self._repository.create_session(payload)

    def get_session(self, session_id: str) -> SessionV1 | None:
        return self._repository.get_session(session_id)

    def create_encounter(self, session_id: str, payload: EncounterCreateV1) -> EncounterV1:
        return self._repository.create_encounter(session_id, payload)

    def list_encounters(self, session_id: str) -> list[EncounterV1]:
        return self._repository.list_encounters(session_id)

    def create_global_override(self, payload: RuleOverrideCreateV1) -> RuleOverrideRecordV1:
        if payload.character_id:
            raise ValueError("Global overrides cannot include a character_id.")
        record = RuleOverrideRecordV1(
            id=str(uuid4()),
            scope="global",
            campaign_id=None,
            created_at=utc_now(),
            **payload.model_dump(),
        )
        return self._repository.create_rule_override(record)

    def create_campaign_override(self, campaign_id: str, payload: RuleOverrideCreateV1) -> RuleOverrideRecordV1:
        scope = "character" if payload.character_id else "campaign"
        record = RuleOverrideRecordV1(
            id=str(uuid4()),
            scope=scope,
            campaign_id=campaign_id,
            created_at=utc_now(),
            **payload.model_dump(),
        )
        return self._repository.create_rule_override(record)

    def list_global_overrides(self) -> list[RuleOverrideRecordV1]:
        return self._repository.list_rule_overrides(scope="global")

    def list_campaign_overrides(self, campaign_id: str, character_id: str | None = None) -> list[RuleOverrideRecordV1]:
        rows = self._repository.list_rule_overrides(campaign_id=campaign_id)
        if character_id is None:
            return rows
        return [row for row in rows if row.character_id == character_id]

    def resolve_overrides(self, campaign_id: str, character_id: str | None = None) -> RuleOverrideResolutionV1:
        global_rows = self._repository.list_rule_overrides(scope="global")
        campaign_rows = self._repository.list_rule_overrides(scope="campaign", campaign_id=campaign_id)
        character_rows: list[RuleOverrideRecordV1] = []
        if character_id:
            character_rows = self._repository.list_rule_overrides(
                scope="character",
                campaign_id=campaign_id,
                character_id=character_id,
            )

        ordered = [*global_rows, *campaign_rows, *character_rows]
        effective: dict[str, int | float] = {}
        for row in ordered:
            if row.operation == "set":
                effective[row.key] = row.value
            else:
                effective[row.key] = (effective.get(row.key, 0) or 0) + row.value

        return RuleOverrideResolutionV1(
            campaign_id=campaign_id,
            character_id=character_id,
            ordered_overrides=ordered,
            effective_values=effective,
        )

