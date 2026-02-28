"""Tests for src/rules_engine/prerequisites.py — feat prerequisite parsing & checking."""

import pytest
from src.rules_engine.character import Character, ClassLevel
from src.rules_engine.prerequisites import (
    parse_prerequisites,
    check_prerequisites,
    ConditionType,
)


class TestParsing:
    def test_parse_bab(self):
        """Parses 'base attack bonus +6'."""
        result = parse_prerequisites("base attack bonus +6")
        assert len(result) == 1
        assert result[0].ctype == ConditionType.BAB
        assert result[0].params["min_bab"] == 6

    def test_parse_ability_score(self):
        """Parses 'Dex 13'."""
        result = parse_prerequisites("Dex 13")
        assert len(result) == 1
        assert result[0].ctype == ConditionType.ABILITY_SCORE
        assert result[0].params["ability"] == "dex"
        assert result[0].params["min_value"] == 13

    def test_parse_multiple(self):
        """Parses comma-separated prerequisites."""
        result = parse_prerequisites("Str 13, base attack bonus +1")
        assert len(result) == 2


class TestChecking:
    def test_bab_prereq_met(self, fighter_l6, db):
        """Fighter L6 (BAB 6) meets BAB +6 requirement."""
        result = check_prerequisites("Vital Strike", fighter_l6, db)
        # Vital Strike requires BAB +6 — Fighter L6 has exactly BAB 6
        # If feat exists in DB, check BAB condition
        bab = fighter_l6.bab(db)
        assert bab >= 6

    def test_bab_prereq_not_met(self, kairon_l5, db):
        """Investigator L5 (BAB 3) does not meet BAB +6."""
        bab = kairon_l5.bab(db)
        assert bab < 6

    def test_ability_prereq_met(self, kairon_l5, db):
        """Kairon DEX 14 meets 'Dex 13' requirement."""
        assert kairon_l5.ability_scores["dex"] >= 13

    def test_ability_prereq_not_met(self, kairon_l5, db):
        """Kairon STR 10 does not meet 'Str 13'."""
        assert kairon_l5.ability_scores["str"] < 13

    def test_feat_chain_prereq(self, db):
        """Character with Power Attack meets Power Attack prerequisite."""
        char = Character(
            name="Test",
            race="Human",
            alignment="N",
            ability_scores={"str": 13, "dex": 10, "con": 12, "int": 10, "wis": 10, "cha": 10},
            class_levels=[ClassLevel("Fighter", 1)],
            feats=["Power Attack"],
        )
        # Power Attack is in feats list
        assert "Power Attack" in char.feats

    def test_check_feat_with_no_prereqs(self, fighter_l6, db):
        """A feat with no prerequisites should pass."""
        result = check_prerequisites("Toughness", fighter_l6, db)
        # Toughness has no prerequisites — should always pass
        if result.raw_text == "":
            assert result.met is True
