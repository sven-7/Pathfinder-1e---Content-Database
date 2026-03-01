"""Tests for Phase 15d equipment features: cost parsing, encumbrance, ACP, gold, gear API."""

import pytest

from scripts.classify_equipment import parse_cost_copper, clean_weight, classify_name
from src.character_creator.exporter import (
    _compute_derived, _get_carry_thresholds, ACP_SKILLS,
)


# ── Cost parsing ─────────────────────────────────────────────────────────

class TestCostParsing:
    def test_gp_simple(self):
        assert parse_cost_copper("10 gp") == 1000

    def test_gp_comma(self):
        assert parse_cost_copper("1,500 gp") == 150000

    def test_sp(self):
        assert parse_cost_copper("5 sp") == 50

    def test_cp(self):
        assert parse_cost_copper("1 cp") == 1

    def test_pp(self):
        assert parse_cost_copper("2 pp") == 2000

    def test_with_slash_qualifier(self):
        assert parse_cost_copper("10 gp/flask") == 1000

    def test_leading_plus(self):
        assert parse_cost_copper("+50 gp") == 5000

    def test_per_qualifier(self):
        assert parse_cost_copper("3 cp per mile") == 3

    def test_empty(self):
        assert parse_cost_copper("") is None
        assert parse_cost_copper(None) is None

    def test_html_entity(self):
        assert parse_cost_copper("&mdash;") is None


# ── Weight cleaning ──────────────────────────────────────────────────────

class TestWeightCleaning:
    def test_lbs_with_period(self):
        assert clean_weight("5 lbs.") == 5.0

    def test_lb_singular(self):
        assert clean_weight("1 lb.") == 1.0

    def test_footnote_stripped(self):
        assert clean_weight("5 lbs.1") == 5.0
        assert clean_weight("4 lbs.1") == 4.0

    def test_half_pound(self):
        assert clean_weight("1/2 lb.") == 0.5

    def test_mdash(self):
        assert clean_weight("&mdash;") is None
        assert clean_weight("—") is None

    def test_none(self):
        assert clean_weight(None) is None

    def test_numeric_string(self):
        assert clean_weight("10") == 10.0


# ── Classification rules ─────────────────────────────────────────────────

class TestClassification:
    def test_alchemical(self):
        assert classify_name("Alchemist's Fire", "20 gp") == "alchemical"
        assert classify_name("Acid", "10 gp") == "alchemical"

    def test_clothing(self):
        assert classify_name("Artisan's Outfit", "1 gp") == "clothing"
        assert classify_name("Cleric's Vestments", "5 gp") == "clothing"

    def test_tool(self):
        assert classify_name("Climber's Kit", "80 gp") == "tool"
        assert classify_name("Thieves' Tools", "30 gp") == "tool"

    def test_mount(self):
        assert classify_name("Horse, Light", "75 gp") == "mount"
        assert classify_name("Dog, Riding", "150 gp") == "mount"

    def test_vehicle(self):
        assert classify_name("Cart", "15 gp") == "vehicle"
        assert classify_name("Carriage", "100 gp") == "vehicle"

    def test_service(self):
        assert classify_name("Coach Cab", "3 cp per mile") == "service"

    def test_gear_default(self):
        assert classify_name("Backpack", "2 gp") == "gear"
        assert classify_name("Rope, Silk (50 ft.)", "10 gp") == "gear"

    def test_junk_no_cost(self):
        assert classify_name("Barding, Medium Creature", "") == "other"
        assert classify_name("Some Header", None) == "other"


# ── Carry capacity / encumbrance ─────────────────────────────────────────

class TestCarryCapacity:
    def test_str_10(self):
        light, med, heavy = _get_carry_thresholds(10)
        assert light == 33
        assert med == 66
        assert heavy == 100

    def test_str_16(self):
        light, med, heavy = _get_carry_thresholds(16)
        assert light == 76
        assert med == 153
        assert heavy == 230

    def test_str_0(self):
        assert _get_carry_thresholds(0) == (0, 0, 0)

    def test_str_1(self):
        assert _get_carry_thresholds(1) == (3, 6, 10)


# ── ACP on skills via exporter ───────────────────────────────────────────

class TestACPOnSkills:
    """Verify ACP from equipped armor reduces physical skill totals."""

    def test_acp_applied_to_climb(self, db):
        char = {
            "name": "TestACP",
            "race": "Human",
            "alignment": "N",
            "ability_scores": {"str": 14, "dex": 12, "con": 12, "int": 10, "wis": 10, "cha": 10},
            "class_levels": [{"class_name": "Fighter", "level": 1}],
            "feats": [],
            "traits": [],
            "skills": {"Climb": 1},
            "equipment": [],
            "equipped_armor": {
                "name": "Chain Shirt",
                "armor_bonus": 4,
                "max_dex": 4,
                "armor_check_penalty": -2,
                "arcane_spell_failure": 20,
            },
            "equipped_shield": None,
            "weapons": [],
        }
        derived = _compute_derived(char, db)
        # Climb: 1 rank + 2 STR + 3 trained + (-2 ACP) = 4
        assert derived["skill_totals"]["Climb"]["acp"] == -2
        assert derived["skill_totals"]["Climb"]["total"] == 4

    def test_acp_not_applied_to_spellcraft(self, db):
        char = {
            "name": "TestACP2",
            "race": "Human",
            "alignment": "N",
            "ability_scores": {"str": 10, "dex": 10, "con": 10, "int": 14, "wis": 10, "cha": 10},
            "class_levels": [{"class_name": "Wizard", "level": 1}],
            "feats": [],
            "traits": [],
            "skills": {"Spellcraft": 1},
            "equipment": [],
            "equipped_armor": {
                "name": "Chain Shirt",
                "armor_bonus": 4,
                "max_dex": 4,
                "armor_check_penalty": -2,
                "arcane_spell_failure": 20,
            },
            "equipped_shield": None,
            "weapons": [],
        }
        derived = _compute_derived(char, db)
        # Spellcraft: should not have ACP applied
        sc = derived["skill_totals"]["Spellcraft"]
        assert sc["acp"] == 0
        # 1 rank + 2 INT + 3 trained = 6
        assert sc["total"] == 6

    def test_combined_acp_armor_plus_shield(self, db):
        char = {
            "name": "TestCombined",
            "race": "Human",
            "alignment": "N",
            "ability_scores": {"str": 14, "dex": 12, "con": 12, "int": 10, "wis": 10, "cha": 10},
            "class_levels": [{"class_name": "Fighter", "level": 1}],
            "feats": [],
            "traits": [],
            "skills": {"Swim": 1},
            "equipment": [],
            "equipped_armor": {
                "name": "Full Plate",
                "armor_bonus": 9,
                "max_dex": 1,
                "armor_check_penalty": -6,
                "arcane_spell_failure": 35,
            },
            "equipped_shield": {
                "name": "Heavy Shield",
                "armor_bonus": 2,
                "max_dex": None,
                "armor_check_penalty": -2,
                "arcane_spell_failure": 15,
            },
            "weapons": [],
        }
        derived = _compute_derived(char, db)
        # Combined ACP = -6 + -2 = -8
        assert derived["armor_check_penalty"] == -8
        assert derived["arcane_spell_failure"] == 50
        # Swim: 1 rank + 2 STR + 3 trained + (-8 ACP) = -2
        assert derived["skill_totals"]["Swim"]["total"] == -2


# ── Two-handed weapon damage ─────────────────────────────────────────────

class TestWeaponDerived:
    def test_two_handed_str_bonus(self, db):
        char = {
            "name": "Greatsword User",
            "race": "Human",
            "alignment": "N",
            "ability_scores": {"str": 18, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 10},
            "class_levels": [{"class_name": "Fighter", "level": 1}],
            "feats": [],
            "traits": [],
            "skills": {},
            "equipment": [],
            "equipped_armor": None,
            "equipped_shield": None,
            "weapons": [{
                "name": "Greatsword",
                "weapon_type": "melee",
                "handedness": "Two-Handed",
                "damage_medium": "2d6",
                "critical": "19-20/x2",
                "damage_type": "S",
                "special": "",
                "range_increment": "",
            }],
        }
        derived = _compute_derived(char, db)
        wep = derived["weapons_derived"][0]
        # STR mod = +4, two-handed = floor(4 * 1.5) = 6
        assert "+6" in wep["damage"]
        assert wep["attack"] == "+5"  # BAB 1 + STR 4

    def test_ranged_no_str_damage(self, db):
        char = {
            "name": "Archer",
            "race": "Human",
            "alignment": "N",
            "ability_scores": {"str": 14, "dex": 16, "con": 12, "int": 10, "wis": 10, "cha": 10},
            "class_levels": [{"class_name": "Fighter", "level": 1}],
            "feats": [],
            "traits": [],
            "skills": {},
            "equipment": [],
            "equipped_armor": None,
            "equipped_shield": None,
            "weapons": [{
                "name": "Longbow",
                "weapon_type": "ranged",
                "handedness": "Two-Handed",
                "damage_medium": "1d8",
                "critical": "x3",
                "damage_type": "P",
                "special": "",
                "range_increment": "100 ft.",
            }],
        }
        derived = _compute_derived(char, db)
        wep = derived["weapons_derived"][0]
        # Ranged: DEX to ATK, no STR to damage (non-composite)
        assert wep["damage"] == "1d8"  # no modifier
        assert wep["attack"] == "+4"   # BAB 1 + DEX 3


# ── Encumbrance in derived ───────────────────────────────────────────────

class TestEncumbrance:
    def test_encumbrance_in_derived(self, db):
        char = {
            "name": "TestEnc",
            "race": "Human",
            "alignment": "N",
            "ability_scores": {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10},
            "class_levels": [{"class_name": "Fighter", "level": 1}],
            "feats": [], "traits": [], "skills": {},
            "equipment": [],
            "equipped_armor": None,
            "equipped_shield": None,
            "weapons": [],
            "gear_items": [{"name": "Backpack", "weight": 2.0, "qty": 1, "cost_copper": 200}],
            "starting_gold_cp": 17500,
        }
        derived = _compute_derived(char, db)
        assert derived["encumbrance"]["total_weight"] == 2.0
        assert derived["encumbrance"]["load"] == "Light"
        assert derived["gold_remaining_cp"] == 17300  # 175gp - 2gp = 173gp


# ── Gear data tests (content DB) ─────────────────────────────────────────

class TestGearData:
    def test_gear_populated(self, db):
        rows = db.get_gear()
        assert len(rows) >= 100, f"Expected >=100 gear items, got {len(rows)}"

    def test_gear_type_filter(self, db):
        alch = db.get_gear(equipment_type="alchemical")
        assert len(alch) >= 5, f"Expected >=5 alchemical items, got {len(alch)}"
        # All should be alchemical
        for r in alch:
            assert r["equipment_type"] == "alchemical"

    def test_gear_has_cost(self, db):
        rows = db.get_gear(equipment_type="gear")
        with_cost = [r for r in rows if r.get("cost_copper")]
        assert len(with_cost) >= 50, f"Expected >=50 gear items with cost, got {len(with_cost)}"

    def test_weapons_have_cost_copper(self, db):
        rows = db.get_weapons()
        with_cost = [r for r in rows if r.get("cost_copper")]
        assert len(with_cost) >= 40, f"Expected >=40 weapons with cost, got {len(with_cost)}"

    def test_armor_has_cost_copper(self, db):
        rows = db.get_armor()
        with_cost = [r for r in rows if r.get("cost_copper")]
        assert len(with_cost) >= 15, f"Expected >=15 armor with cost, got {len(with_cost)}"
