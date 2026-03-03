from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")


def test_campaign_party_session_foundations_flow(isolated_db_client) -> None:
    client = isolated_db_client

    campaign_resp = client.post(
        "/api/v2/campaigns",
        json={
            "name": "Stolen Lands",
            "owner_id": "owner-stephen",
            "status": "active",
            "gm_id": "gm-stephen",
        },
    )
    assert campaign_resp.status_code == 201
    campaign = campaign_resp.json()
    campaign_id = campaign["id"]

    list_campaigns = client.get("/api/v2/campaigns")
    assert list_campaigns.status_code == 200
    assert [row["id"] for row in list_campaigns.json()] == [campaign_id]

    party_resp = client.post(
        "/api/v2/parties",
        json={
            "campaign_id": campaign_id,
            "name": "Heroes of Restov",
            "owner_id": "owner-stephen",
            "members": [
                {"display_name": "Kairon", "role": "pc", "character_id": "char-kairon", "player_id": "player-a"},
                {"display_name": "Linzi", "role": "pc", "character_id": "char-linzi", "player_id": "player-b"},
            ],
        },
    )
    assert party_resp.status_code == 201
    party = party_resp.json()
    party_id = party["id"]
    assert party["campaign_id"] == campaign_id
    assert len(party["members"]) == 2

    party_list = client.get(f"/api/v2/parties?campaign_id={campaign_id}")
    assert party_list.status_code == 200
    assert len(party_list.json()) == 1
    assert party_list.json()[0]["id"] == party_id

    session_resp = client.post(
        "/api/v2/sessions",
        json={
            "campaign_id": campaign_id,
            "name": "Session 1: Trading Post",
            "owner_id": "owner-stephen",
            "status": "planned",
        },
    )
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]

    encounter_resp = client.post(
        f"/api/v2/sessions/{session_id}/encounters",
        json={
            "name": "Bandit Ambush",
            "owner_id": "owner-stephen",
            "status": "planned",
        },
    )
    assert encounter_resp.status_code == 201
    encounter_id = encounter_resp.json()["id"]

    session_get = client.get(f"/api/v2/sessions/{session_id}")
    assert session_get.status_code == 200
    payload = session_get.json()
    assert payload["id"] == session_id
    assert payload["encounters"][0]["id"] == encounter_id


def test_rule_override_resolution_api_order(isolated_db_client) -> None:
    client = isolated_db_client

    campaign_resp = client.post(
        "/api/v2/campaigns",
        json={"name": "Override Test", "owner_id": "owner-stephen"},
    )
    assert campaign_resp.status_code == 201
    campaign_id = campaign_resp.json()["id"]

    global_resp = client.post(
        "/api/v2/campaigns/rule-overrides/global",
        json={"key": "ac_total", "operation": "add", "value": 1, "source": "global-house-rule"},
    )
    assert global_resp.status_code == 201
    assert global_resp.json()["scope"] == "global"

    campaign_override_resp = client.post(
        f"/api/v2/campaigns/{campaign_id}/rule-overrides",
        json={"key": "ac_total", "operation": "set", "value": 16, "source": "campaign-setting"},
    )
    assert campaign_override_resp.status_code == 201
    assert campaign_override_resp.json()["scope"] == "campaign"

    character_override_resp = client.post(
        f"/api/v2/campaigns/{campaign_id}/rule-overrides",
        json={
            "key": "ac_total",
            "operation": "add",
            "value": 2,
            "source": "character-bonus",
            "character_id": "char-kairon",
        },
    )
    assert character_override_resp.status_code == 201
    assert character_override_resp.json()["scope"] == "character"

    campaign_resolved = client.get(f"/api/v2/campaigns/{campaign_id}/rule-overrides/resolve")
    assert campaign_resolved.status_code == 200
    campaign_payload = campaign_resolved.json()
    assert campaign_payload["effective_values"]["ac_total"] == 16
    assert campaign_payload["merge_order"] == "global->campaign->character"
    assert [row["scope"] for row in campaign_payload["ordered_overrides"]] == ["global", "campaign"]

    character_resolved = client.get(
        f"/api/v2/campaigns/{campaign_id}/rule-overrides/resolve?character_id=char-kairon"
    )
    assert character_resolved.status_code == 200
    character_payload = character_resolved.json()
    assert character_payload["effective_values"]["ac_total"] == 18
    assert [row["scope"] for row in character_payload["ordered_overrides"]] == ["global", "campaign", "character"]

