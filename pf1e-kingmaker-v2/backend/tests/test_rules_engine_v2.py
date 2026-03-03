from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from app.models.contracts import (
    AbilityScoresV2,
    CharacterV2,
    ClassLevelV2,
    EquipmentSelectionV2,
    FeatSelectionV2,
    RuleOverrideV2,
    TraitSelectionV2,
)
from app.rules.engine_v2 import derive_stats, evaluate_feat_prerequisites


def _base_kairon() -> CharacterV2:
    return CharacterV2(
        name="Kairon",
        race="Tiefling",
        alignment="Lawful Neutral",
        ability_scores=AbilityScoresV2(str=12, dex=18, con=12, int=17, wis=18, cha=14),
        class_levels=[ClassLevelV2(class_name="Investigator", level=9)],
        feats=[
            FeatSelectionV2(name="Weapon Finesse", level_gained=1, method="general"),
            FeatSelectionV2(name="Weapon Focus", level_gained=3, method="general"),
            FeatSelectionV2(name="Rapid Shot", level_gained=5, method="general"),
        ],
        traits=[
            TraitSelectionV2(
                name="Reactionary",
                category="Combat",
                effects=[{"key": "initiative", "delta": 2, "bonus_type": "trait", "source": "Reactionary"}],
            )
        ],
        skills={"Perception": 9},
        equipment=[
            EquipmentSelectionV2(name="Rapier", kind="weapon", quantity=1),
            EquipmentSelectionV2(name="Studded Leather", kind="armor", quantity=1),
        ],
        conditions=[],
    )


def _breakdown_key_values(character: CharacterV2) -> dict[str, list[int | float]]:
    derived = derive_stats(character)
    out: dict[str, list[int | float]] = {}
    for line in derived.breakdown:
        out.setdefault(line.key, []).append(line.value)
    return out


def test_kairon_level_9_golden_stats():
    character = _base_kairon()
    derived = derive_stats(character)

    assert derived.total_level == 9
    assert derived.bab == 6
    assert derived.fort == 4
    assert derived.ref == 10
    assert derived.will == 10
    assert derived.hp_max == 57
    assert derived.ac_total == 17
    assert derived.ac_touch == 14
    assert derived.ac_flat_footed == 13
    assert derived.cmb == 7
    assert derived.cmd == 21
    assert derived.initiative == 6
    assert derived.spell_slots == {"1": 5, "2": 4, "3": 3}

    rapier = next(a for a in derived.attack_lines if a.name == "Rapier")
    assert rapier.attack_bonus == 11
    assert rapier.damage == "1d6+1"
    assert "iterative +11/+6" in rapier.notes

    breakdown_by_key = _breakdown_key_values(character)
    assert breakdown_by_key["BAB:class:Investigator"] == [6]
    assert breakdown_by_key["BAB:total"] == [6]
    assert breakdown_by_key["Fort:base"] == [3]
    assert breakdown_by_key["Fort:ability"] == [1]
    assert breakdown_by_key["Fort:total"] == [4]
    assert breakdown_by_key["Ref:total"] == [10]
    assert breakdown_by_key["Will:total"] == [10]
    assert breakdown_by_key["HP:hit_die"] == [48]
    assert breakdown_by_key["HP:con"] == [9]
    assert breakdown_by_key["HP:total"] == [57]
    assert breakdown_by_key["AC:armor"] == [3]
    assert breakdown_by_key["AC:dex"] == [4]
    assert breakdown_by_key["AC:total"] == [17]
    assert breakdown_by_key["AC:touch"] == [14]
    assert breakdown_by_key["AC:flat_footed"] == [13]
    assert breakdown_by_key["CMB:total"] == [7]
    assert breakdown_by_key["CMD:total"] == [21]
    assert breakdown_by_key["Initiative:misc"] == [2]
    assert breakdown_by_key["Initiative:total"] == [6]
    assert breakdown_by_key["Skill:Perception:ranks"] == [9]
    assert breakdown_by_key["Skill:Perception:ability"] == [4]
    assert breakdown_by_key["Skill:Perception:class"] == [3]
    assert breakdown_by_key["Skill:Perception:total"] == [16]
    assert breakdown_by_key["Attack:Rapier:total"] == [11]
    assert breakdown_by_key["Attack:Rapier:damage_bonus"] == [1]
    assert breakdown_by_key["FeatPrereq:Rapid Shot"] == [0]
    assert breakdown_by_key["Result:ac_total"] == [17]
    assert breakdown_by_key["Result:initiative"] == [6]


def test_prerequisite_evaluator_flags_invalid_and_accepts_valid_chain():
    invalid = _base_kairon()
    invalid_results = {r.feat_name: r for r in evaluate_feat_prerequisites(invalid)}
    assert invalid_results["Rapid Shot"].valid is False
    assert "Point-Blank Shot" in invalid_results["Rapid Shot"].missing

    valid = _base_kairon()
    valid.feats.append(FeatSelectionV2(name="Point-Blank Shot", level_gained=1, method="general"))
    valid_results = {r.feat_name: r for r in evaluate_feat_prerequisites(valid)}
    assert valid_results["Rapid Shot"].valid is True


def test_prerequisite_chain_requires_prereq_before_dependent_feat():
    character = _base_kairon()
    character.feats = [
        FeatSelectionV2(name="Rapid Shot", level_gained=1, method="general"),
        FeatSelectionV2(name="Point-Blank Shot", level_gained=3, method="general"),
    ]
    results = {r.feat_name: r for r in evaluate_feat_prerequisites(character)}

    assert results["Rapid Shot"].valid is False
    assert "Point-Blank Shot" in results["Rapid Shot"].missing
    assert results["Point-Blank Shot"].valid is True


def test_house_rule_overrides_apply_deterministically():
    character = _base_kairon()
    character.overrides = [
        RuleOverrideV2(key="ac_total", operation="add", value=1, source="Campaign house rule"),
        RuleOverrideV2(key="initiative", operation="set", value=8, source="Table ruling"),
    ]

    derived = derive_stats(character)
    assert derived.ac_total == 18
    assert derived.initiative == 8
    assert any(line.key == "Override:ac_total" and line.value == 1 for line in derived.breakdown)
    assert any(line.key == "Override:initiative" and line.value == 8 for line in derived.breakdown)
    assert any(line.key == "Result:ac_total" and line.value == 18 for line in derived.breakdown)
    assert any(line.key == "Result:initiative" and line.value == 8 for line in derived.breakdown)
