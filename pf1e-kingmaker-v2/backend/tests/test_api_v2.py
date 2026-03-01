from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_derive_kairon_slice_baseline():
    client = TestClient(app)

    payload = {
        "name": "Kairon",
        "race": "Tiefling",
        "alignment": "Lawful Neutral",
        "ability_scores": {
            "str": 12,
            "dex": 18,
            "con": 12,
            "int": 17,
            "wis": 18,
            "cha": 14,
        },
        "class_levels": [{"class_name": "Investigator", "level": 9}],
        "feats": [
            {"name": "Weapon Finesse", "level_gained": 1, "method": "general"},
            {"name": "Weapon Focus", "level_gained": 3, "method": "general"},
            {"name": "Rapid Shot", "level_gained": 5, "method": "general"},
        ],
        "traits": [
            {
                "name": "Reactionary",
                "category": "Combat",
                "effects": [{"key": "initiative", "delta": 2, "bonus_type": "trait", "source": "Reactionary"}],
            }
        ],
        "skills": {"Perception": 9},
        "equipment": [
            {"name": "Rapier", "kind": "weapon", "quantity": 1},
            {"name": "Studded Leather", "kind": "armor", "quantity": 1},
        ],
        "conditions": [],
    }

    response = client.post("/api/v2/rules/derive", json=payload)
    assert response.status_code == 200

    derived = response.json()["derived"]
    assert derived["total_level"] == 9
    assert derived["bab"] == 6
    assert derived["fort"] == 4
    assert derived["ref"] == 10
    assert derived["will"] == 10
    assert derived["hp_max"] == 57
    assert derived["ac_total"] == 17
    assert derived["ac_touch"] == 14
    assert derived["ac_flat_footed"] == 13
    assert derived["cmb"] == 7
    assert derived["cmd"] == 21
    assert derived["initiative"] == 6
    assert derived["spell_slots"] == {"1": 5, "2": 4, "3": 3}
    assert derived["skill_totals"]["Perception"] == 16
    assert derived["attack_lines"][0]["name"] == "Rapier"
    assert derived["attack_lines"][0]["attack_bonus"] == 11

    feat_results = {item["feat_name"]: item for item in derived["feat_prereq_results"]}
    assert feat_results["Weapon Finesse"]["valid"] is True
    assert feat_results["Weapon Focus"]["valid"] is True
    assert feat_results["Rapid Shot"]["valid"] is False
    assert "Point-Blank Shot" in feat_results["Rapid Shot"]["missing"]


def test_character_validate_reports_invalid_feat_chain():
    client = TestClient(app)

    payload = {
        "name": "Kairon",
        "race": "Tiefling",
        "ability_scores": {"str": 12, "dex": 18, "con": 12, "int": 17, "wis": 18, "cha": 14},
        "class_levels": [{"class_name": "Investigator", "level": 9}],
        "feats": [
            {"name": "Rapid Shot", "level_gained": 5, "method": "general"},
        ],
        "traits": [],
        "skills": {},
        "equipment": [{"name": "Rapier", "kind": "weapon", "quantity": 1}],
        "conditions": [],
    }

    response = client.post("/api/v2/characters/validate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["invalid_feats"][0]["feat_name"] == "Rapid Shot"
    assert "Point-Blank Shot" in body["invalid_feats"][0]["missing"]
