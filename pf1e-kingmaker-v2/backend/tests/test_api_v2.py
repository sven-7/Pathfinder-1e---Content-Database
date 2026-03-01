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
        "equipment": [],
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
