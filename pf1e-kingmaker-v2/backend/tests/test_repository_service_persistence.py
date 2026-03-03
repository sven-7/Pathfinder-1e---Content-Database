from __future__ import annotations

from sqlalchemy import select

from app.models.campaigns_v1 import CampaignCreateV1
from app.models.contracts import AbilityScoresV2, CharacterV2, ClassLevelV2
from app.persistence.models import CharacterSnapshotRecord
from app.repositories.campaigns_v1 import CampaignRepositoryV1
from app.repositories.characters_v2 import CharacterRepositoryV2
from app.services.campaigns_v1 import CampaignServiceV1
from app.services.characters_v2 import CharacterServiceV2


def _character_payload(name: str = "Snapshot Hero") -> CharacterV2:
    return CharacterV2(
        name=name,
        race="Human",
        alignment="Neutral",
        ability_scores=AbilityScoresV2(str=12, dex=12, con=12, int=12, wis=12, cha=12),
        class_levels=[ClassLevelV2(class_name="Fighter", level=1)],
        feats=[],
        traits=[],
        skills={},
        equipment=[],
        conditions=[],
        overrides=[],
    )


def test_campaign_persists_across_repository_instances(isolated_db) -> None:
    session_local = isolated_db["session_local"]

    with session_local() as session_a:
        service_a = CampaignServiceV1(CampaignRepositoryV1(session_a))
        created = service_a.create_campaign(CampaignCreateV1(name="Persistent Campaign", owner_id="owner-a"))
        campaign_id = created.id

    with session_local() as session_b:
        service_b = CampaignServiceV1(CampaignRepositoryV1(session_b))
        fetched = service_b.get_campaign(campaign_id)
        assert fetched is not None
        assert fetched.name == "Persistent Campaign"
        assert fetched.owner_id == "owner-a"


def test_character_service_records_snapshot_history_on_update(isolated_db_session) -> None:
    repository = CharacterRepositoryV2(isolated_db_session)
    service = CharacterServiceV2(repository)

    created = service.create_character(_character_payload())
    updated_payload = created.model_copy(update={"name": "Snapshot Hero Updated"})
    updated = service.update_character(created.id or "", updated_payload)

    assert updated.id == created.id
    assert updated.name == "Snapshot Hero Updated"

    revisions = isolated_db_session.scalars(
        select(CharacterSnapshotRecord.revision)
        .where(CharacterSnapshotRecord.character_id == created.id)
        .order_by(CharacterSnapshotRecord.revision)
    ).all()
    assert revisions == [1, 2]

