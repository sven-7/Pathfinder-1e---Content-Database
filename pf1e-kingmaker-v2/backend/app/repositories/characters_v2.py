"""SQLAlchemy repository for character V2 persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.contracts import CharacterV2
from app.persistence.models import CharacterRecord, CharacterSnapshotRecord


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CharacterRepositoryV2:
    """Database repository for persisted CharacterV2 payloads."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_character(self, payload: CharacterV2) -> CharacterV2:
        character_id = payload.id or str(uuid4())
        if self._session.get(CharacterRecord, character_id) is not None:
            raise ValueError(character_id)

        normalized = payload.model_copy(update={"id": character_id})
        now = _utc_now()
        payload_json = normalized.model_dump(mode="json")
        metadata_json = {"revision": 1, "action": "create"}

        row = CharacterRecord(
            id=character_id,
            owner_id=normalized.owner_id,
            campaign_id=normalized.campaign_id,
            name=normalized.name,
            payload=payload_json,
            payload_metadata=metadata_json,
            created_at=now,
            updated_at=now,
        )
        snapshot = CharacterSnapshotRecord(
            id=self._next_snapshot_id(),
            character_id=character_id,
            revision=1,
            payload=payload_json,
            payload_metadata=metadata_json,
            created_at=now,
        )
        self._session.add(row)
        self._session.add(snapshot)
        self._session.commit()
        self._session.refresh(row)
        return self._to_character(row)

    def get_character(self, character_id: str) -> CharacterV2 | None:
        row = self._session.get(CharacterRecord, character_id)
        if row is None:
            return None
        return self._to_character(row)

    def list_characters(
        self,
        *,
        campaign_id: str | None = None,
        owner_id: str | None = None,
    ) -> list[CharacterV2]:
        stmt = select(CharacterRecord)
        if campaign_id is not None:
            stmt = stmt.where(CharacterRecord.campaign_id == campaign_id)
        if owner_id is not None:
            stmt = stmt.where(CharacterRecord.owner_id == owner_id)
        stmt = stmt.order_by(CharacterRecord.created_at, CharacterRecord.id)

        rows = self._session.scalars(stmt).all()
        return [self._to_character(row) for row in rows]

    def update_character(self, character_id: str, payload: CharacterV2) -> CharacterV2:
        row = self._session.get(CharacterRecord, character_id)
        if row is None:
            raise KeyError(character_id)

        normalized = payload.model_copy(update={"id": character_id})
        now = _utc_now()
        payload_json = normalized.model_dump(mode="json")
        revision = self._next_revision(character_id)
        metadata_json = {"revision": revision, "action": "update"}

        row.owner_id = normalized.owner_id
        row.campaign_id = normalized.campaign_id
        row.name = normalized.name
        row.payload = payload_json
        row.payload_metadata = metadata_json
        row.updated_at = now

        self._session.add(
            CharacterSnapshotRecord(
                id=self._next_snapshot_id(),
                character_id=character_id,
                revision=revision,
                payload=payload_json,
                payload_metadata=metadata_json,
                created_at=now,
            )
        )

        self._session.commit()
        self._session.refresh(row)
        return self._to_character(row)

    def delete_character(self, character_id: str) -> None:
        row = self._session.get(CharacterRecord, character_id)
        if row is None:
            raise KeyError(character_id)
        self._session.delete(row)
        self._session.commit()

    def _next_revision(self, character_id: str) -> int:
        max_revision = self._session.scalar(
            select(func.max(CharacterSnapshotRecord.revision)).where(
                CharacterSnapshotRecord.character_id == character_id
            )
        )
        return int(max_revision or 0) + 1

    def _next_snapshot_id(self) -> int:
        max_id = self._session.scalar(select(func.max(CharacterSnapshotRecord.id)))
        return int(max_id or 0) + 1

    @staticmethod
    def _to_character(row: CharacterRecord) -> CharacterV2:
        payload = dict(row.payload or {})
        payload["id"] = row.id
        if row.owner_id is not None and payload.get("owner_id") is None:
            payload["owner_id"] = row.owner_id
        if row.campaign_id is not None and payload.get("campaign_id") is None:
            payload["campaign_id"] = row.campaign_id
        if row.name and payload.get("name") != row.name:
            payload["name"] = row.name
        return CharacterV2.model_validate(payload)
