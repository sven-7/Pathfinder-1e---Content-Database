"""Tests for src/rules_engine/skills.py — skill budget, class skills, totals."""

import pytest
from src.rules_engine.character import Character, ClassLevel
from src.rules_engine.skills import get_class_skills, skill_total, max_ranks


class TestSkillBudget:
    def test_investigator_l5_budget(self, kairon_l5):
        """Investigator: 6 + INT(4) = 10 ranks/level × 5 = 50 total."""
        ranks_per_level = 6 + kairon_l5.ability_mod("int")  # 6 + 4 = 10
        total_budget = ranks_per_level * kairon_l5.total_level
        assert total_budget == 50

    def test_human_fighter_l6_budget(self, fighter_l6):
        """Human Fighter: 2 + INT(0) + 1(human) = 3/level × 6 = 18."""
        base_ranks = 2  # Fighter base
        int_mod = fighter_l6.ability_mod("int")  # 0
        human_bonus = 1  # Human
        ranks_per_level = base_ranks + int_mod + human_bonus
        total_budget = ranks_per_level * fighter_l6.total_level
        assert total_budget == 18


class TestMaxRanks:
    def test_max_ranks_equals_level(self, kairon_l5):
        """Max ranks in a skill = character level."""
        assert max_ranks(kairon_l5) == 5

    def test_max_ranks_multiclass(self, multiclass_fighter3_rogue2):
        """Multi-class: max ranks = total character level (5)."""
        assert max_ranks(multiclass_fighter3_rogue2) == 5


class TestClassSkills:
    def test_investigator_class_skills(self, kairon_l5, db):
        """Investigator should have Perception as a class skill."""
        cs = get_class_skills(kairon_l5, db)
        assert "perception" in cs

    def test_multiclass_class_skills_union(self, multiclass_fighter3_rogue2, db):
        """Multi-class gets union of both classes' skills."""
        cs = get_class_skills(multiclass_fighter3_rogue2, db)
        # Fighter has Climb, Rogue has Stealth
        assert "climb" in cs, "Fighter class skill should be present"
        assert "stealth" in cs, "Rogue class skill should be present"


class TestSkillTotal:
    def test_class_skill_bonus(self, kairon_l5, db):
        """Perception: 5 ranks + WIS(2) + 3 (class skill) = 10."""
        total = skill_total("Perception", kairon_l5, db)
        assert total == 10

    def test_non_class_skill_no_bonus(self, fighter_l6, db):
        """Non-class skill gets no +3 trained bonus."""
        # Give fighter a skill that's NOT a Fighter class skill
        char = Character(
            name="Test",
            race="Human",
            alignment="N",
            ability_scores={"str": 18, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8},
            class_levels=[ClassLevel("Fighter", 6)],
            skills={"Spellcraft": 3},  # Spellcraft is NOT a Fighter class skill
        )
        total = skill_total("Spellcraft", char, db)
        # 3 ranks + INT(0) + 0 (no class skill bonus) = 3
        assert total == 3

    def test_zero_ranks_no_trained_bonus(self, kairon_l5, db):
        """A class skill with 0 ranks gets no +3 bonus."""
        total = skill_total("Bluff", kairon_l5, db)
        # 0 ranks + CHA(1) + 0 = 1
        assert total == 1
