from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import app.api.v2.dm_store as dm_store
from app.main import app


@pytest.fixture(autouse=True)
def _reset_dm_scaffold_store():
    dm_store.reset_state()
    yield
    dm_store.reset_state()


def test_dm_foundation_scaffolding_campaign_party_npc_kingdom_flow():
    client = TestClient(app)

    campaign_response = client.post(
        "/api/v2/campaigns",
        json={
            "name": "Stolen Lands",
            "description": "Kingmaker campaign baseline.",
            "status": "active",
        },
    )
    assert campaign_response.status_code == 201
    campaign = campaign_response.json()
    campaign_id = campaign["id"]
    assert campaign["name"] == "Stolen Lands"
    assert campaign["status"] == "active"

    list_campaigns = client.get("/api/v2/campaigns")
    assert list_campaigns.status_code == 200
    assert [row["id"] for row in list_campaigns.json()] == [campaign_id]

    party_response = client.post(
        f"/api/v2/campaigns/{campaign_id}/parties",
        json={
            "name": "Heroes of Restov",
            "member_character_ids": ["char-kairon", "char-valerie"],
            "marching_order": ["char-valerie", "char-kairon"],
        },
    )
    assert party_response.status_code == 201
    party = party_response.json()
    assert party["campaign_id"] == campaign_id
    assert party["member_character_ids"] == ["char-kairon", "char-valerie"]

    npc_response = client.post(
        f"/api/v2/campaigns/{campaign_id}/npcs",
        json={
            "name": "Svetlana Leveton",
            "role": "ally",
            "disposition": "friendly",
            "location": "Oleg's Trading Post",
            "tags": ["merchant", "quest_hook"],
        },
    )
    assert npc_response.status_code == 201
    npc = npc_response.json()
    assert npc["campaign_id"] == campaign_id
    assert npc["role"] == "ally"

    kingdom_before = client.get(f"/api/v2/campaigns/{campaign_id}/kingdom")
    assert kingdom_before.status_code == 200
    assert kingdom_before.json() is None

    kingdom_response = client.put(
        f"/api/v2/campaigns/{campaign_id}/kingdom",
        json={
            "name": "Greenbelt Charter",
            "alignment": "Neutral Good",
            "government": "Council",
            "treasury_bp": 50,
            "unrest": 0,
            "consumption": 2,
        },
    )
    assert kingdom_response.status_code == 200
    kingdom = kingdom_response.json()
    assert kingdom["campaign_id"] == campaign_id
    assert kingdom["treasury_bp"] == 50

    foundations = client.get(f"/api/v2/campaigns/{campaign_id}/foundations")
    assert foundations.status_code == 200
    payload = foundations.json()
    assert payload["campaign"]["id"] == campaign_id
    assert len(payload["parties"]) == 1
    assert len(payload["npcs"]) == 1
    assert payload["kingdom"]["name"] == "Greenbelt Charter"


def test_dm_foundation_endpoints_require_existing_campaign():
    client = TestClient(app)
    missing_id = "missing-campaign"

    response = client.get(f"/api/v2/campaigns/{missing_id}")
    assert response.status_code == 404

    response = client.post(
        f"/api/v2/campaigns/{missing_id}/parties",
        json={"name": "Unknown Party"},
    )
    assert response.status_code == 404

    response = client.get(f"/api/v2/campaigns/{missing_id}/foundations")
    assert response.status_code == 404
