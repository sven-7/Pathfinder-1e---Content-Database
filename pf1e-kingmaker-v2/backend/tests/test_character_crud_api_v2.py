from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from app.main import app
from app.persistence.database import get_db_session


def _kairon_payload(*, campaign_id: str | None = None, owner_id: str | None = "owner-stephen") -> dict:
    return {
        "owner_id": owner_id,
        "campaign_id": campaign_id,
        "name": "Kairon",
        "race": "Tiefling",
        "alignment": "Lawful Neutral",
        "ability_scores": {"str": 12, "dex": 18, "con": 12, "int": 17, "wis": 18, "cha": 14},
        "class_levels": [{"class_name": "Investigator", "level": 9}],
        "feats": [{"name": "Weapon Finesse", "level_gained": 1, "method": "general"}],
        "traits": [],
        "skills": {"Perception": 9},
        "equipment": [{"name": "Rapier", "kind": "weapon", "quantity": 1}],
        "conditions": [],
        "overrides": [],
    }


def test_characters_crud_contract(isolated_db_client) -> None:
    client = isolated_db_client

    campaign_resp = client.post(
        "/api/v2/campaigns",
        json={"name": "Character CRUD Campaign", "owner_id": "owner-stephen"},
    )
    assert campaign_resp.status_code == 201
    campaign_id = campaign_resp.json()["id"]

    create_resp = client.post("/api/v2/characters", json=_kairon_payload(campaign_id=campaign_id))
    assert create_resp.status_code == 201
    created = create_resp.json()
    character_id = created["id"]
    assert created["campaign_id"] == campaign_id
    assert created["owner_id"] == "owner-stephen"

    get_resp = client.get(f"/api/v2/characters/{character_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == character_id

    list_resp = client.get(f"/api/v2/characters?campaign_id={campaign_id}&owner_id=owner-stephen")
    assert list_resp.status_code == 200
    assert [row["id"] for row in list_resp.json()] == [character_id]

    update_payload = _kairon_payload(campaign_id=campaign_id)
    update_payload["name"] = "Kairon Updated"
    update_payload["skills"]["Knowledge (nature)"] = 5
    update_resp = client.put(f"/api/v2/characters/{character_id}", json=update_payload)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["id"] == character_id
    assert updated["name"] == "Kairon Updated"
    assert updated["skills"]["Knowledge (nature)"] == 5

    validate_resp = client.post("/api/v2/characters/validate", json=updated)
    assert validate_resp.status_code == 200
    assert validate_resp.json()["name"] == "Kairon Updated"

    derive_resp = client.post("/api/v2/rules/derive", json=updated)
    assert derive_resp.status_code == 200
    assert derive_resp.json()["character"]["id"] == character_id

    delete_resp = client.delete(f"/api/v2/characters/{character_id}")
    assert delete_resp.status_code == 204

    missing_resp = client.get(f"/api/v2/characters/{character_id}")
    assert missing_resp.status_code == 404


def test_character_records_persist_across_client_restart(isolated_db):
    from fastapi.testclient import TestClient

    session_local = isolated_db["session_local"]

    def _override_get_db_session():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        with TestClient(app) as client:
            create_resp = client.post("/api/v2/characters", json=_kairon_payload(owner_id="persist-owner"))
            assert create_resp.status_code == 201
            character_id = create_resp.json()["id"]

        # New TestClient instance simulates API process restart while using the same DB.
        with TestClient(app) as client_after_restart:
            get_resp = client_after_restart.get(f"/api/v2/characters/{character_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["owner_id"] == "persist-owner"
    finally:
        app.dependency_overrides.clear()

