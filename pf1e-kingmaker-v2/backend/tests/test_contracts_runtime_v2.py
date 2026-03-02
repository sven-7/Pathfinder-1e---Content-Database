from __future__ import annotations

import importlib

import pytest

pytest.importorskip("pydantic")

from app.models.contracts import CharacterV2


def _kairon_payload() -> dict:
    return {
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


def test_contracts_module_imports_smoke():
    module = importlib.import_module("app.models.contracts")
    assert hasattr(module, "AbilityScoresV2")
    assert hasattr(module, "CharacterV2")


def test_character_v2_round_trip_preserves_ability_score_alias_keys():
    payload = _kairon_payload()
    character = CharacterV2.model_validate(payload)

    dumped = character.model_dump(by_alias=True)
    assert dumped["ability_scores"] == payload["ability_scores"]
    assert set(dumped["ability_scores"]) == {"str", "dex", "con", "int", "wis", "cha"}

    reloaded = CharacterV2.model_validate(dumped)
    assert reloaded.ability_scores.intelligence == 17
    assert reloaded.ability_scores.dexterity == 18
