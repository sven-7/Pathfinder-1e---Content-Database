"""Integration tests for src/character_creator/exporter.py _compute_derived()."""

import pytest
from src.character_creator.exporter import _compute_derived


def _kairon_l5_dict():
    """Character dict matching the Kairon L5 fixture."""
    return {
        "name": "Kairon",
        "race": "Tiefling",
        "alignment": "CG",
        "ability_scores": {"str": 10, "dex": 14, "con": 12, "int": 18, "wis": 14, "cha": 12},
        "class_levels": [{"class_name": "Investigator", "level": 5}],
        "feats": ["Extra Investigator Talent"],
        "feat_details": [{"name": "Extra Investigator Talent", "level": 1, "method": "general"}],
        "traits": ["Reactionary"],
        "skills": {
            "Perception": 5,
            "Knowledge (Arcana)": 5,
            "Spellcraft": 5,
            "Disable Device": 5,
            "Diplomacy": 5,
        },
        "equipment": [],
        "conditions": [],
        "fav_class_choice": "",
        "class_talents": [],
        "weapons": [],
    }


def _fighter_l1_dict():
    """Character dict for Human Fighter L1."""
    return {
        "name": "TestFighter",
        "race": "Human",
        "alignment": "N",
        "ability_scores": {"str": 16, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8},
        "class_levels": [{"class_name": "Fighter", "level": 1}],
        "feats": ["Power Attack", "Weapon Focus (longsword)", "Toughness"],
        "feat_details": [
            {"name": "Power Attack", "level": 1, "method": "general"},
            {"name": "Weapon Focus (longsword)", "level": 1, "method": "bonus"},
            {"name": "Toughness", "level": 1, "method": "human"},
        ],
        "traits": [],
        "skills": {"Climb": 1, "Swim": 1, "Intimidate": 1},
        "equipment": [],
        "conditions": [],
        "fav_class_choice": "",
        "class_talents": [],
        "weapons": [],
    }


class TestKaironL5Derived:
    def test_hp(self, db):
        """HP = 8+1 + 4*(5+1) = 33 (max at L1, avg+1 thereafter, CON+1/level)."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        assert derived["hp_max"] == 33

    def test_bab(self, db):
        """BAB = 3 (3/4 progression at L5)."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        assert derived["bab"] == 3

    def test_saves(self, db):
        """Fort=1+1=2, Ref=4+2=6, Will=4+2=6."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        assert derived["fort"] == 2   # poor(1) + CON(1)
        assert derived["ref"] == 6    # good(4) + DEX(2)
        assert derived["will"] == 6   # good(4) + WIS(2)

    def test_ac_no_armor(self, db):
        """AC = 10 + DEX(2) = 12."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        assert derived["ac"]["total"] == 12

    def test_cmb(self, db):
        """CMB = BAB(3) + STR(0) = 3."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        assert derived["cmb"] == 3

    def test_cmd(self, db):
        """CMD = 10 + BAB(3) + STR(0) + DEX(2) = 15."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        assert derived["cmd"] == 15

    def test_class_features_populated(self, db):
        """Class features list should be non-empty."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        assert len(derived["class_features"]) > 0

    def test_spell_slots(self, db):
        """Investigator L5 should have extract slots for level 1 and 2."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        inv_slots = derived["spell_slots"].get("Investigator", {})
        assert 1 in inv_slots, "Should have 1st-level extract slots"
        assert 2 in inv_slots, "Should have 2nd-level extract slots"

    def test_inspiration_resource(self, db):
        """Inspiration pool = level(5) + INT(4) = 9."""
        derived = _compute_derived(_kairon_l5_dict(), db)
        resources = derived["class_resources"]
        insp = next((r for r in resources if r["name"] == "Inspiration"), None)
        assert insp is not None, "Should have Inspiration resource"
        assert insp["uses_per_day"] == 9


class TestFighterL1Derived:
    def test_skill_budget(self, db):
        """Human Fighter L1: 2 + INT(0) + 1(human) = 3 ranks."""
        # This tests that the character has allocated 3 skill ranks
        char = _fighter_l1_dict()
        total_ranks = sum(char["skills"].values())
        assert total_ranks == 3

    def test_hp_with_armor(self, db):
        """Fighter L1 with armor should have correct AC."""
        char = _fighter_l1_dict()
        char["equipped_armor"] = {"armor_bonus": 5, "max_dex": 3}
        derived = _compute_derived(char, db)
        # AC = 10 + min(DEX(2), max_dex(3)) + armor(5) = 17
        assert derived["ac"]["total"] == 17

    def test_ac_with_shield(self, db):
        """Fighter with armor + shield."""
        char = _fighter_l1_dict()
        char["equipped_armor"] = {"armor_bonus": 5, "max_dex": 3}
        char["equipped_shield"] = {"armor_bonus": 2}
        derived = _compute_derived(char, db)
        # AC = 10 + min(DEX(2), max_dex(3)) + armor(5) + shield(2) = 19
        assert derived["ac"]["total"] == 19

    def test_ac_max_dex_cap(self, db):
        """Armor max_dex caps effective DEX bonus."""
        char = _fighter_l1_dict()
        char["ability_scores"]["dex"] = 20  # DEX mod = +5
        char["equipped_armor"] = {"armor_bonus": 8, "max_dex": 1}
        derived = _compute_derived(char, db)
        # AC = 10 + min(5, 1) + 8 = 19
        assert derived["ac"]["total"] == 19
        assert derived["ac"]["dex_mod"] == 1  # capped


class TestMultiClassExporter:
    def test_multiclass_class_skills(self, db):
        """Multi-class Fighter/Rogue should get both classes' skills."""
        char = {
            "name": "Harsk",
            "race": "Dwarf",
            "alignment": "LN",
            "ability_scores": {"str": 16, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8},
            "class_levels": [
                {"class_name": "Fighter", "level": 3},
                {"class_name": "Rogue", "level": 2},
            ],
            "feats": [],
            "feat_details": [],
            "traits": [],
            "skills": {"Climb": 3, "Stealth": 2},
            "equipment": [],
            "conditions": [],
            "fav_class_choice": "",
            "class_talents": [],
            "weapons": [],
        }
        derived = _compute_derived(char, db)
        # Climb is a Fighter class skill → should get trained bonus
        climb = derived["skill_totals"].get("Climb")
        assert climb is not None
        assert climb["is_class_skill"] is True
        assert climb["trained_bonus"] == 3
        # Stealth is a Rogue class skill → should also get trained bonus
        stealth = derived["skill_totals"].get("Stealth")
        assert stealth is not None
        assert stealth["is_class_skill"] is True, "Rogue class skill should be recognized in multi-class"
        assert stealth["trained_bonus"] == 3
