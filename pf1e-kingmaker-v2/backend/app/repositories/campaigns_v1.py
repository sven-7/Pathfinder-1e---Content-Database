"""SQLAlchemy repository for campaign domain V1 APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

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
from app.persistence.models import (
    CampaignRecord,
    EncounterRecord,
    PartyMemberRecord,
    PartyRecord,
    RuleOverrideRecord,
    SessionRecord,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignRepositoryV1:
    """DB-backed repository for campaign domain entities."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def reset(self) -> None:
        self._session.execute(delete(RuleOverrideRecord))
        self._session.execute(delete(EncounterRecord))
        self._session.execute(delete(SessionRecord))
        self._session.execute(delete(PartyMemberRecord))
        self._session.execute(delete(PartyRecord))
        self._session.execute(delete(CampaignRecord))
        self._session.commit()

    def create_campaign(self, payload: CampaignCreateV1) -> CampaignV1:
        now = _utc_now()
        row = CampaignRecord(
            id=str(uuid4()),
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_campaign(row)

    def list_campaigns(self, owner_id: str | None = None) -> list[CampaignV1]:
        stmt = select(CampaignRecord)
        if owner_id is not None:
            stmt = stmt.where(CampaignRecord.owner_id == owner_id)
        stmt = stmt.order_by(CampaignRecord.created_at, CampaignRecord.id)
        rows = self._session.scalars(stmt).all()
        return [self._to_campaign(row) for row in rows]

    def get_campaign(self, campaign_id: str) -> CampaignV1 | None:
        row = self._session.get(CampaignRecord, campaign_id)
        if row is None:
            return None
        return self._to_campaign(row)

    def create_party(self, payload: PartyCreateV1) -> PartyV1:
        campaign = self._session.get(CampaignRecord, payload.campaign_id)
        if campaign is None:
            raise KeyError(payload.campaign_id)

        now = _utc_now()
        party = PartyRecord(
            id=str(uuid4()),
            campaign_id=payload.campaign_id,
            name=payload.name,
            owner_id=payload.owner_id,
            notes=payload.notes,
            gm_id=payload.gm_id,
            player_id=payload.player_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(party)

        for member in payload.members:
            self._session.add(
                PartyMemberRecord(
                    id=str(uuid4()),
                    party_id=party.id,
                    display_name=member.display_name,
                    role=member.role,
                    character_id=member.character_id,
                    owner_id=member.owner_id,
                    gm_id=member.gm_id,
                    player_id=member.player_id,
                    created_at=now,
                )
            )

        self._session.commit()
        return self._get_party_required(party.id)

    def list_parties(self, campaign_id: str | None = None) -> list[PartyV1]:
        stmt = select(PartyRecord).options(selectinload(PartyRecord.members))
        if campaign_id is not None:
            stmt = stmt.where(PartyRecord.campaign_id == campaign_id)
        stmt = stmt.order_by(PartyRecord.created_at, PartyRecord.id)
        rows = self._session.scalars(stmt).all()
        return [self._to_party(row) for row in rows]

    def get_party(self, party_id: str) -> PartyV1 | None:
        row = self._session.scalar(
            select(PartyRecord).options(selectinload(PartyRecord.members)).where(PartyRecord.id == party_id)
        )
        if row is None:
            return None
        return self._to_party(row)

    def add_party_member(self, party_id: str, payload: PartyMemberCreateV1) -> PartyMemberV1:
        party = self._session.get(PartyRecord, party_id)
        if party is None:
            raise KeyError(party_id)

        now = _utc_now()
        member = PartyMemberRecord(
            id=str(uuid4()),
            party_id=party_id,
            display_name=payload.display_name,
            role=payload.role,
            character_id=payload.character_id,
            owner_id=payload.owner_id,
            gm_id=payload.gm_id,
            player_id=payload.player_id,
            created_at=now,
        )
        party.updated_at = now
        self._session.add(member)
        self._session.commit()
        self._session.refresh(member)
        return self._to_party_member(member)

    def list_party_members(self, party_id: str) -> list[PartyMemberV1]:
        party = self._session.get(PartyRecord, party_id)
        if party is None:
            raise KeyError(party_id)

        rows = self._session.scalars(
            select(PartyMemberRecord)
            .where(PartyMemberRecord.party_id == party_id)
            .order_by(PartyMemberRecord.created_at, PartyMemberRecord.id)
        ).all()
        return [self._to_party_member(row) for row in rows]

    def create_session(self, payload: SessionCreateV1) -> SessionV1:
        campaign = self._session.get(CampaignRecord, payload.campaign_id)
        if campaign is None:
            raise KeyError(payload.campaign_id)

        now = _utc_now()
        row = SessionRecord(
            id=str(uuid4()),
            campaign_id=payload.campaign_id,
            name=payload.name,
            owner_id=payload.owner_id,
            scheduled_for=payload.scheduled_for,
            status=payload.status,
            notes=payload.notes,
            gm_id=payload.gm_id,
            player_id=payload.player_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.commit()
        return self._get_session_required(row.id)

    def list_sessions(self, campaign_id: str | None = None) -> list[SessionV1]:
        stmt = select(SessionRecord).options(selectinload(SessionRecord.encounters))
        if campaign_id is not None:
            stmt = stmt.where(SessionRecord.campaign_id == campaign_id)
        stmt = stmt.order_by(SessionRecord.created_at, SessionRecord.id)
        rows = self._session.scalars(stmt).all()
        return [self._to_session(row) for row in rows]

    def get_session(self, session_id: str) -> SessionV1 | None:
        row = self._session.scalar(
            select(SessionRecord).options(selectinload(SessionRecord.encounters)).where(SessionRecord.id == session_id)
        )
        if row is None:
            return None
        return self._to_session(row)

    def create_encounter(self, session_id: str, payload: EncounterCreateV1) -> EncounterV1:
        session_row = self._session.get(SessionRecord, session_id)
        if session_row is None:
            raise KeyError(session_id)

        now = _utc_now()
        row = EncounterRecord(
            id=str(uuid4()),
            session_id=session_id,
            name=payload.name,
            owner_id=payload.owner_id,
            status=payload.status,
            notes=payload.notes,
            gm_id=payload.gm_id,
            player_id=payload.player_id,
            created_at=now,
            updated_at=now,
        )
        session_row.updated_at = now
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_encounter(row)

    def list_encounters(self, session_id: str) -> list[EncounterV1]:
        session_row = self._session.get(SessionRecord, session_id)
        if session_row is None:
            raise KeyError(session_id)

        rows = self._session.scalars(
            select(EncounterRecord)
            .where(EncounterRecord.session_id == session_id)
            .order_by(EncounterRecord.created_at, EncounterRecord.id)
        ).all()
        return [self._to_encounter(row) for row in rows]

    def create_rule_override(self, payload: RuleOverrideRecordV1) -> RuleOverrideRecordV1:
        if payload.scope in {"campaign", "character"}:
            if payload.campaign_id is None:
                raise KeyError("")
            campaign = self._session.get(CampaignRecord, payload.campaign_id)
            if campaign is None:
                raise KeyError(payload.campaign_id)

        row = RuleOverrideRecord(
            id=payload.id,
            scope=payload.scope,
            campaign_id=payload.campaign_id,
            key=payload.key,
            operation=payload.operation,
            value=float(payload.value),
            source=payload.source,
            owner_id=payload.owner_id,
            character_id=payload.character_id,
            gm_id=payload.gm_id,
            player_id=payload.player_id,
            created_at=payload.created_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_rule_override(row)

    def list_rule_overrides(
        self,
        *,
        scope: str | None = None,
        campaign_id: str | None = None,
        character_id: str | None = None,
    ) -> list[RuleOverrideRecordV1]:
        stmt = select(RuleOverrideRecord)
        if scope is not None:
            stmt = stmt.where(RuleOverrideRecord.scope == scope)
        if campaign_id is not None:
            stmt = stmt.where(RuleOverrideRecord.campaign_id == campaign_id)
        if character_id is not None:
            stmt = stmt.where(RuleOverrideRecord.character_id == character_id)
        stmt = stmt.order_by(RuleOverrideRecord.created_at, RuleOverrideRecord.id)
        rows = self._session.scalars(stmt).all()
        return [self._to_rule_override(row) for row in rows]

    def _get_party_required(self, party_id: str) -> PartyV1:
        row = self._session.scalar(
            select(PartyRecord).options(selectinload(PartyRecord.members)).where(PartyRecord.id == party_id)
        )
        if row is None:
            raise KeyError(party_id)
        return self._to_party(row)

    def _get_session_required(self, session_id: str) -> SessionV1:
        row = self._session.scalar(
            select(SessionRecord).options(selectinload(SessionRecord.encounters)).where(SessionRecord.id == session_id)
        )
        if row is None:
            raise KeyError(session_id)
        return self._to_session(row)

    @staticmethod
    def _to_campaign(row: CampaignRecord) -> CampaignV1:
        return CampaignV1(
            id=row.id,
            name=row.name,
            owner_id=row.owner_id,
            description=row.description,
            status=row.status,
            gm_id=row.gm_id,
            player_id=row.player_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_party(self, row: PartyRecord) -> PartyV1:
        members = sorted(row.members, key=lambda item: (item.created_at, item.id))
        return PartyV1(
            id=row.id,
            campaign_id=row.campaign_id,
            name=row.name,
            owner_id=row.owner_id,
            notes=row.notes,
            gm_id=row.gm_id,
            player_id=row.player_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            members=[self._to_party_member(member) for member in members],
        )

    @staticmethod
    def _to_party_member(row: PartyMemberRecord) -> PartyMemberV1:
        return PartyMemberV1(
            id=row.id,
            party_id=row.party_id,
            display_name=row.display_name,
            role=row.role,
            character_id=row.character_id,
            owner_id=row.owner_id,
            gm_id=row.gm_id,
            player_id=row.player_id,
            created_at=row.created_at,
        )

    def _to_session(self, row: SessionRecord) -> SessionV1:
        encounters = sorted(row.encounters, key=lambda item: (item.created_at, item.id))
        return SessionV1(
            id=row.id,
            campaign_id=row.campaign_id,
            name=row.name,
            owner_id=row.owner_id,
            scheduled_for=row.scheduled_for,
            status=row.status,
            notes=row.notes,
            gm_id=row.gm_id,
            player_id=row.player_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            encounters=[self._to_encounter(encounter) for encounter in encounters],
        )

    @staticmethod
    def _to_encounter(row: EncounterRecord) -> EncounterV1:
        return EncounterV1(
            id=row.id,
            session_id=row.session_id,
            name=row.name,
            owner_id=row.owner_id,
            status=row.status,
            notes=row.notes,
            gm_id=row.gm_id,
            player_id=row.player_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_rule_override(row: RuleOverrideRecord) -> RuleOverrideRecordV1:
        return RuleOverrideRecordV1(
            id=row.id,
            scope=row.scope,
            campaign_id=row.campaign_id,
            key=row.key,
            operation=row.operation,
            value=row.value,
            source=row.source,
            owner_id=row.owner_id,
            character_id=row.character_id,
            gm_id=row.gm_id,
            player_id=row.player_id,
            created_at=row.created_at,
        )

