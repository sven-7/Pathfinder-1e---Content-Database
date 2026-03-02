"""In-memory repository for campaign domain V1 scaffolding."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
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
    RuleOverrideRecordV1,
    SessionCreateV1,
    SessionV1,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignRepositoryV1:
    def __init__(self) -> None:
        self._lock = Lock()
        self._campaigns: dict[str, CampaignV1] = {}
        self._parties: dict[str, PartyV1] = {}
        self._party_members_by_party: dict[str, dict[str, PartyMemberV1]] = {}
        self._sessions: dict[str, SessionV1] = {}
        self._encounters_by_session: dict[str, dict[str, EncounterV1]] = {}
        self._rule_overrides: dict[str, RuleOverrideRecordV1] = {}

    def reset(self) -> None:
        with self._lock:
            self._campaigns.clear()
            self._parties.clear()
            self._party_members_by_party.clear()
            self._sessions.clear()
            self._encounters_by_session.clear()
            self._rule_overrides.clear()

    def create_campaign(self, payload: CampaignCreateV1) -> CampaignV1:
        with self._lock:
            now = _utc_now()
            campaign = CampaignV1(
                id=str(uuid4()),
                created_at=now,
                updated_at=now,
                **payload.model_dump(),
            )
            self._campaigns[campaign.id] = campaign
            return campaign.model_copy(deep=True)

    def list_campaigns(self, owner_id: str | None = None) -> list[CampaignV1]:
        with self._lock:
            values = self._campaigns.values()
            if owner_id:
                values = [campaign for campaign in values if campaign.owner_id == owner_id]
            ordered = sorted(values, key=lambda item: (item.created_at, item.id))
            return [campaign.model_copy(deep=True) for campaign in ordered]

    def get_campaign(self, campaign_id: str) -> CampaignV1 | None:
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            return campaign.model_copy(deep=True) if campaign else None

    def create_party(self, payload: PartyCreateV1) -> PartyV1:
        with self._lock:
            if payload.campaign_id not in self._campaigns:
                raise KeyError(payload.campaign_id)

            now = _utc_now()
            party_id = str(uuid4())
            party = PartyV1(
                id=party_id,
                campaign_id=payload.campaign_id,
                name=payload.name,
                owner_id=payload.owner_id,
                notes=payload.notes,
                gm_id=payload.gm_id,
                player_id=payload.player_id,
                created_at=now,
                updated_at=now,
                members=[],
            )
            self._parties[party_id] = party
            self._party_members_by_party.setdefault(party_id, {})

            for member_payload in payload.members:
                self._add_party_member_locked(party_id, member_payload, now)

            return self._party_with_members_locked(party_id)

    def list_parties(self, campaign_id: str | None = None) -> list[PartyV1]:
        with self._lock:
            parties = self._parties.values()
            if campaign_id:
                parties = [party for party in parties if party.campaign_id == campaign_id]
            ordered = sorted(parties, key=lambda item: (item.created_at, item.id))
            return [self._party_with_members_locked(party.id) for party in ordered]

    def get_party(self, party_id: str) -> PartyV1 | None:
        with self._lock:
            if party_id not in self._parties:
                return None
            return self._party_with_members_locked(party_id)

    def add_party_member(self, party_id: str, payload: PartyMemberCreateV1) -> PartyMemberV1:
        with self._lock:
            if party_id not in self._parties:
                raise KeyError(party_id)
            now = _utc_now()
            member = self._add_party_member_locked(party_id, payload, now)
            return member.model_copy(deep=True)

    def list_party_members(self, party_id: str) -> list[PartyMemberV1]:
        with self._lock:
            if party_id not in self._parties:
                raise KeyError(party_id)
            members = self._party_members_by_party.get(party_id, {})
            ordered = sorted(members.values(), key=lambda item: (item.created_at, item.id))
            return [member.model_copy(deep=True) for member in ordered]

    def create_session(self, payload: SessionCreateV1) -> SessionV1:
        with self._lock:
            if payload.campaign_id not in self._campaigns:
                raise KeyError(payload.campaign_id)

            now = _utc_now()
            session_id = str(uuid4())
            session = SessionV1(
                id=session_id,
                campaign_id=payload.campaign_id,
                name=payload.name,
                owner_id=payload.owner_id,
                scheduled_for=payload.scheduled_for,
                status=payload.status,
                notes=payload.notes,
                gm_id=payload.gm_id,
                player_id=payload.player_id,
                encounters=[],
                created_at=now,
                updated_at=now,
            )
            self._sessions[session_id] = session
            self._encounters_by_session.setdefault(session_id, {})
            return session.model_copy(deep=True)

    def list_sessions(self, campaign_id: str | None = None) -> list[SessionV1]:
        with self._lock:
            sessions = self._sessions.values()
            if campaign_id:
                sessions = [session for session in sessions if session.campaign_id == campaign_id]
            ordered = sorted(sessions, key=lambda item: (item.created_at, item.id))
            return [self._session_with_encounters_locked(session.id) for session in ordered]

    def get_session(self, session_id: str) -> SessionV1 | None:
        with self._lock:
            if session_id not in self._sessions:
                return None
            return self._session_with_encounters_locked(session_id)

    def create_encounter(self, session_id: str, payload: EncounterCreateV1) -> EncounterV1:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(session_id)

            now = _utc_now()
            encounter = EncounterV1(
                id=str(uuid4()),
                session_id=session_id,
                created_at=now,
                updated_at=now,
                **payload.model_dump(),
            )
            by_session = self._encounters_by_session.setdefault(session_id, {})
            by_session[encounter.id] = encounter
            return encounter.model_copy(deep=True)

    def list_encounters(self, session_id: str) -> list[EncounterV1]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(session_id)
            encounters = self._encounters_by_session.get(session_id, {})
            ordered = sorted(encounters.values(), key=lambda item: (item.created_at, item.id))
            return [encounter.model_copy(deep=True) for encounter in ordered]

    def create_rule_override(self, payload: RuleOverrideRecordV1) -> RuleOverrideRecordV1:
        with self._lock:
            if payload.scope in {"campaign", "character"} and payload.campaign_id not in self._campaigns:
                raise KeyError(payload.campaign_id or "")
            record = payload.model_copy(deep=True)
            self._rule_overrides[record.id] = record
            return record.model_copy(deep=True)

    def list_rule_overrides(
        self,
        *,
        scope: str | None = None,
        campaign_id: str | None = None,
        character_id: str | None = None,
    ) -> list[RuleOverrideRecordV1]:
        with self._lock:
            rows = list(self._rule_overrides.values())
            if scope:
                rows = [row for row in rows if row.scope == scope]
            if campaign_id is not None:
                rows = [row for row in rows if row.campaign_id == campaign_id]
            if character_id is not None:
                rows = [row for row in rows if row.character_id == character_id]
            ordered = sorted(rows, key=lambda item: (item.created_at, item.id))
            return [row.model_copy(deep=True) for row in ordered]

    def _add_party_member_locked(
        self,
        party_id: str,
        payload: PartyMemberCreateV1,
        created_at: datetime,
    ) -> PartyMemberV1:
        member = PartyMemberV1(
            id=str(uuid4()),
            party_id=party_id,
            created_at=created_at,
            **payload.model_dump(),
        )
        members = self._party_members_by_party.setdefault(party_id, {})
        members[member.id] = member

        party = self._parties[party_id]
        self._parties[party_id] = party.model_copy(update={"updated_at": created_at})
        return member

    def _party_with_members_locked(self, party_id: str) -> PartyV1:
        party = self._parties[party_id]
        members = self._party_members_by_party.get(party_id, {})
        ordered_members = sorted(members.values(), key=lambda item: (item.created_at, item.id))
        return party.model_copy(update={"members": [member.model_copy(deep=True) for member in ordered_members]}, deep=True)

    def _session_with_encounters_locked(self, session_id: str) -> SessionV1:
        session = self._sessions[session_id]
        encounters = self._encounters_by_session.get(session_id, {})
        ordered = sorted(encounters.values(), key=lambda item: (item.created_at, item.id))
        return session.model_copy(update={"encounters": [enc.model_copy(deep=True) for enc in ordered]}, deep=True)


_REPOSITORY = CampaignRepositoryV1()


def get_campaign_repository() -> CampaignRepositoryV1:
    return _REPOSITORY
