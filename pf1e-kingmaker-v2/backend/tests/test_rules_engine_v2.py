from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from app.models.contracts import AbilityScoresV2, CharacterV2, ClassLevelV2, EquipmentSelectionV2, FeatSelectionV2, TraitSelectionV2
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


def _multiclass_martial_caster() -> CharacterV2:
    return CharacterV2(
        name="Valeros",
        race="Human",
        alignment="Neutral Good",
        ability_scores=AbilityScoresV2(str=16, dex=14, con=12, int=16, wis=10, cha=8),
        class_levels=[
            ClassLevelV2(class_name="Fighter", level=5),
            ClassLevelV2(class_name="Wizard", level=4),
        ],
        feats=[
            FeatSelectionV2(name="Power Attack", level_gained=1, method="general"),
            FeatSelectionV2(name="Weapon Focus", level_gained=1, method="general"),
            FeatSelectionV2(name="Cleave", level_gained=3, method="general"),
            FeatSelectionV2(name="Great Cleave", level_gained=5, method="general"),
        ],
        traits=[],
        skills={"Stealth": 4, "Climb": 5, "Knowledge (arcana)": 4},
        equipment=[
            EquipmentSelectionV2(name="Longsword", kind="weapon", quantity=1),
            EquipmentSelectionV2(name="Shortbow", kind="weapon", quantity=1),
            EquipmentSelectionV2(name="Chain Shirt", kind="armor", quantity=1),
            EquipmentSelectionV2(name="Heavy Wooden Shield", kind="shield", quantity=1),
        ],
        conditions=[],
    )


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


def test_multiclass_progression_and_equipment_interactions_golden_stats():
    character = _multiclass_martial_caster()
    derived = derive_stats(character)

    assert derived.total_level == 9
    assert derived.bab == 7
    assert derived.fort == 6
    assert derived.ref == 4
    assert derived.will == 5
    assert derived.hp_max == 59
    assert derived.ac_total == 18
    assert derived.ac_touch == 12
    assert derived.ac_flat_footed == 16
    assert derived.cmb == 10
    assert derived.cmd == 22
    assert derived.initiative == 2
    assert derived.spell_slots == {}
    assert derived.skill_totals["Stealth"] == 2
    assert derived.skill_totals["Climb"] == 7
    assert derived.skill_totals["Knowledge (arcana)"] == 10

    attacks = {line.name: line for line in derived.attack_lines}
    assert attacks["Longsword"].attack_bonus == 9
    assert attacks["Longsword"].damage == "1d8+7"
    assert "Power Attack (-2/+4)" in attacks["Longsword"].notes
    assert attacks["Shortbow"].attack_bonus == 10
    assert attacks["Shortbow"].damage == "1d6+0"

    assert any(line.key == "ArmorCheckPenalty" and line.value == -4 for line in derived.breakdown)


def test_prerequisite_evaluator_flags_invalid_and_accepts_valid_chain():
    invalid = _base_kairon()
    invalid_results = {r.feat_name: r for r in evaluate_feat_prerequisites(invalid)}
    assert invalid_results["Rapid Shot"].valid is False
    assert "Point-Blank Shot" in invalid_results["Rapid Shot"].missing

    valid = _base_kairon()
    valid.feats.append(FeatSelectionV2(name="Point-Blank Shot", level_gained=1, method="general"))
    valid_results = {r.feat_name: r for r in evaluate_feat_prerequisites(valid)}
    assert valid_results["Rapid Shot"].valid is True


def test_prerequisite_evaluator_enforces_ordered_feat_chains():
    character = CharacterV2(
        name="Chain Test",
        race="Human",
        alignment="Neutral",
        ability_scores=AbilityScoresV2(str=14, dex=14, con=12, int=10, wis=10, cha=10),
        class_levels=[ClassLevelV2(class_name="Fighter", level=5)],
        feats=[
            FeatSelectionV2(name="Rapid Shot", level_gained=1, method="general"),
            FeatSelectionV2(name="Point-Blank Shot", level_gained=3, method="general"),
            FeatSelectionV2(name="Dodge", level_gained=1, method="general"),
            FeatSelectionV2(name="Spring Attack", level_gained=5, method="general"),
            FeatSelectionV2(name="Mobility", level_gained=5, method="general"),
        ],
        traits=[],
        skills={},
        equipment=[EquipmentSelectionV2(name="Shortbow", kind="weapon", quantity=1)],
        conditions=[],
    )

    results = {r.feat_name: r for r in evaluate_feat_prerequisites(character)}
    assert results["Rapid Shot"].valid is False
    assert "Point-Blank Shot" in results["Rapid Shot"].missing
    assert results["Spring Attack"].valid is False
    assert "Mobility" in results["Spring Attack"].missing
    assert results["Mobility"].valid is True

    valid_chain = character.model_copy(deep=True)
    valid_chain.feats = [
        FeatSelectionV2(name="Dodge", level_gained=1, method="general"),
        FeatSelectionV2(name="Mobility", level_gained=3, method="general"),
        FeatSelectionV2(name="Spring Attack", level_gained=5, method="general"),
    ]
    valid_chain_results = {r.feat_name: r for r in evaluate_feat_prerequisites(valid_chain)}
    assert valid_chain_results["Dodge"].valid is True
    assert valid_chain_results["Mobility"].valid is True
    assert valid_chain_results["Spring Attack"].valid is True


def test_rapid_shot_weapon_interaction_applies_ranged_penalty():
    character = CharacterV2(
        name="Archer",
        race="Human",
        alignment="Neutral",
        ability_scores=AbilityScoresV2(str=12, dex=16, con=12, int=10, wis=10, cha=10),
        class_levels=[ClassLevelV2(class_name="Ranger", level=6)],
        feats=[
            FeatSelectionV2(name="Point-Blank Shot", level_gained=1, method="general"),
            FeatSelectionV2(name="Rapid Shot", level_gained=3, method="general"),
            FeatSelectionV2(name="Weapon Focus", level_gained=1, method="general"),
        ],
        traits=[],
        skills={},
        equipment=[EquipmentSelectionV2(name="Shortbow", kind="weapon", quantity=1)],
        conditions=[],
    )

    derived = derive_stats(character)
    attack = derived.attack_lines[0]
    assert attack.name == "Shortbow"
    assert attack.attack_bonus == 8
    assert attack.damage == "1d6+0"
    assert "Rapid Shot (-2; extra ranged attack)" in attack.notes


def test_house_rule_overrides_apply_deterministically():
    character = _base_kairon()
    character.overrides = [
        {"key": "ac_total", "operation": "add", "value": 1, "source": "Campaign house rule"},
        {"key": "initiative", "operation": "set", "value": 8, "source": "Table ruling"},
    ]

    derived = derive_stats(character)
    assert derived.ac_total == 18
    assert derived.initiative == 8
    assert any(line.key == "Override:ac_total" for line in derived.breakdown)
    assert any(line.key == "Override:initiative" for line in derived.breakdown)
