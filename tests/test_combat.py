"""Tests for src/rules_engine/combat.py — AC, CMB, CMD, initiative, attacks."""

import pytest
from src.rules_engine.character import Character, ClassLevel
from src.rules_engine.combat import ac, attack_bonus, cmb, cmd, initiative


class TestAC:
    def test_ac_no_armor(self, kairon_l5, db):
        """AC with no armor, DEX+2 → 12."""
        result = ac(kairon_l5, db)
        assert result.total == 12

    def test_ac_touch(self, kairon_l5, db):
        """Touch AC = 10 + DEX mod (no armor)."""
        result = ac(kairon_l5, db)
        assert result.touch == 12

    def test_ac_flat_footed(self, kairon_l5, db):
        """Flat-footed AC = 10 (no armor, no DEX)."""
        result = ac(kairon_l5, db)
        assert result.flat_footed == 10


class TestCMB:
    def test_cmb_investigator_l5(self, kairon_l5, db):
        """CMB = BAB(3) + STR(0) = 3."""
        assert cmb(kairon_l5, db) == 3

    def test_cmb_fighter_l6(self, fighter_l6, db):
        """CMB = BAB(6) + STR(4) = 10."""
        assert cmb(fighter_l6, db) == 10


class TestCMD:
    def test_cmd_investigator_l5(self, kairon_l5, db):
        """CMD = 10 + BAB(3) + STR(0) + DEX(2) = 15."""
        assert cmd(kairon_l5, db) == 15

    def test_cmd_fighter_l6(self, fighter_l6, db):
        """CMD = 10 + BAB(6) + STR(4) + DEX(2) = 22."""
        assert cmd(fighter_l6, db) == 22


class TestInitiative:
    def test_initiative_dex_mod(self, kairon_l5, db):
        """Initiative = DEX mod (+2)."""
        assert initiative(kairon_l5, db) == 2


class TestAttackBonus:
    def test_melee_attack(self, kairon_l5, db):
        """Melee attack = BAB(3) + STR(0) = 3."""
        assert attack_bonus(kairon_l5, "melee", db) == 3

    def test_ranged_attack(self, kairon_l5, db):
        """Ranged attack = BAB(3) + DEX(2) = 5."""
        assert attack_bonus(kairon_l5, "ranged", db) == 5

    def test_fighter_melee(self, fighter_l6, db):
        """Fighter L6 melee = BAB(6) + STR(4) = 10."""
        assert attack_bonus(fighter_l6, "melee", db) == 10

    def test_iterative_attacks_formula(self, fighter_l6, db):
        """Fighter L6 (BAB 6) gets 2 iterative attacks: +6/+1."""
        bab = fighter_l6.bab(db)
        assert bab == 6
        num_attacks = 1 + max(0, (bab - 1) // 5)
        assert num_attacks == 2
