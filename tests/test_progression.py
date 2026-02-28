"""Tests for src/rules_engine/progression.py — BAB, saves, HP, spell slots."""

import pytest
from src.rules_engine.character import ClassLevel
from src.rules_engine.progression import get_bab, get_save, get_hp, get_spell_slots


# ── BAB ──────────────────────────────────────────────────────────────────

class TestBAB:
    def test_three_quarter_bab_l5(self, kairon_l5, db):
        """Investigator (3/4 BAB) at L5 → 3."""
        assert get_bab(kairon_l5.class_levels, db) == 3

    def test_three_quarter_bab_l9(self, kairon_l9, db):
        """Investigator (3/4 BAB) at L9 → 6."""
        assert get_bab(kairon_l9.class_levels, db) == 6

    def test_full_bab_l6(self, fighter_l6, db):
        """Fighter (full BAB) at L6 → 6."""
        assert get_bab(fighter_l6.class_levels, db) == 6

    def test_half_bab_l5(self, db):
        """Wizard (half BAB) at L5 → 2."""
        cls = [ClassLevel("Wizard", 5)]
        assert get_bab(cls, db) == 2

    def test_multiclass_bab_stacking(self, multiclass_fighter3_rogue2, db):
        """Fighter 3 (BAB 3) + Rogue 2 (BAB 1) = 4."""
        assert get_bab(multiclass_fighter3_rogue2.class_levels, db) == 4


# ── Saves ────────────────────────────────────────────────────────────────

class TestSaves:
    def test_good_save_l5(self, db):
        """Investigator good saves (Ref, Will) at L5 → 4."""
        cls = [ClassLevel("Investigator", 5)]
        assert get_save(cls, "ref", db) == 4
        assert get_save(cls, "will", db) == 4

    def test_good_save_l9(self, db):
        """Investigator good saves (Ref, Will) at L9 → 6."""
        cls = [ClassLevel("Investigator", 9)]
        assert get_save(cls, "ref", db) == 6
        assert get_save(cls, "will", db) == 6

    def test_poor_save_l5(self, db):
        """Investigator poor save (Fort) at L5 → 1."""
        cls = [ClassLevel("Investigator", 5)]
        assert get_save(cls, "fort", db) == 1

    def test_poor_save_l9(self, db):
        """Investigator poor save (Fort) at L9 → 3."""
        cls = [ClassLevel("Investigator", 9)]
        assert get_save(cls, "fort", db) == 3

    def test_multiclass_save_stacking(self, multiclass_fighter3_rogue2, db):
        """Fighter 3 Fort good (3) + Rogue 2 Fort poor (0) = 3."""
        cls = multiclass_fighter3_rogue2.class_levels
        assert get_save(cls, "fort", db) == 3


# ── HP ───────────────────────────────────────────────────────────────────

class TestHP:
    def test_hp_max_first_l5(self, db):
        """Investigator L5, d8, CON+1: 8+1 + 4*(5+1) = 33."""
        cls = [ClassLevel("Investigator", 5)]
        assert get_hp(cls, con_mod=1, favored_class_hp=0, db=db) == 33

    def test_hp_max_first_l9(self, db):
        """Investigator L9, d8, CON+1: 8+1 + 8*(5+1) = 57."""
        cls = [ClassLevel("Investigator", 9)]
        assert get_hp(cls, con_mod=1, favored_class_hp=0, db=db) == 57

    def test_hp_with_favored_class(self, db):
        """Investigator L5 with 5 HP from favored class → 33+5=38."""
        cls = [ClassLevel("Investigator", 5)]
        assert get_hp(cls, con_mod=1, favored_class_hp=5, db=db) == 38

    def test_hp_fighter_l6(self, db):
        """Fighter L6, d10, CON+2: 10+2 + 5*(6+2) = 52."""
        cls = [ClassLevel("Fighter", 6)]
        assert get_hp(cls, con_mod=2, favored_class_hp=0, db=db) == 52

    def test_hp_minimum_one_per_level(self, db):
        """HP can never be less than total character level."""
        cls = [ClassLevel("Wizard", 3)]
        # d6 Wizard with CON penalty -5: would compute negative but floor is 3
        result = get_hp(cls, con_mod=-5, favored_class_hp=0, db=db)
        assert result >= 3


# ── Spell Slots ──────────────────────────────────────────────────────────

class TestSpellSlots:
    def test_investigator_l5_slots(self, db):
        """Investigator L5 should have extract slots for levels 1 and 2."""
        slots = get_spell_slots("Investigator", 5, db)
        assert 1 in slots, "Should have 1st-level extract slots"
        assert 2 in slots, "Should have 2nd-level extract slots"
        assert slots[1] >= 4, f"Expected ≥4 L1 slots, got {slots[1]}"
        assert slots[2] >= 2, f"Expected ≥2 L2 slots, got {slots[2]}"

    def test_fighter_no_spells(self, db):
        """Fighter should have no spell slots."""
        slots = get_spell_slots("Fighter", 6, db)
        assert slots == {}

    def test_wizard_l5_has_cantrips(self, db):
        """Wizard L5 should have cantrip (level 0) slots."""
        slots = get_spell_slots("Wizard", 5, db)
        assert 0 in slots, "Wizard should have cantrip slots"
