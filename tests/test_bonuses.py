"""Tests for src/rules_engine/bonuses.py — PF1e stacking rules."""

import pytest
from src.rules_engine.bonuses import Bonus, BonusStack


class TestBonusStacking:
    def test_same_type_no_stack(self):
        """Same-type bonuses (non-stackable) → highest wins."""
        stack = BonusStack()
        stack.add(Bonus(2, "armor", "Chainmail"))
        stack.add(Bonus(3, "armor", "Breastplate"))
        assert stack.total() == 3

    def test_dodge_stacks(self):
        """Dodge bonuses stack with each other."""
        stack = BonusStack()
        stack.add(Bonus(1, "dodge", "Fighting Defensively"))
        stack.add(Bonus(1, "dodge", "Dodge feat"))
        assert stack.total() == 2

    def test_untyped_stacks(self):
        """Untyped bonuses stack."""
        stack = BonusStack()
        stack.add(Bonus(2, "untyped", "Source A"))
        stack.add(Bonus(1, "untyped", "Source B"))
        assert stack.total() == 3

    def test_penalty_stacks(self):
        """Penalties stack (all apply)."""
        stack = BonusStack()
        stack.add(Bonus(-2, "penalty", "Power Attack"))
        stack.add(Bonus(-1, "penalty", "Fighting Defensively"))
        assert stack.total() == -3

    def test_circumstance_stacks(self):
        """Circumstance bonuses stack."""
        stack = BonusStack()
        stack.add(Bonus(2, "circumstance", "Higher ground"))
        stack.add(Bonus(1, "circumstance", "Flanking"))
        assert stack.total() == 3

    def test_mixed_types(self):
        """Mixed bonus types: +2 armor + +1 dodge + +3 natural armor = 6."""
        stack = BonusStack()
        stack.add(Bonus(2, "armor", "Chainmail"))
        stack.add(Bonus(1, "dodge", "Dodge feat"))
        stack.add(Bonus(3, "natural armor", "Amulet"))
        assert stack.total() == 6

    def test_enhancement_no_stack(self):
        """Enhancement bonuses don't stack → highest wins."""
        stack = BonusStack()
        stack.add(Bonus(1, "enhancement", "+1 sword"))
        stack.add(Bonus(3, "enhancement", "+3 sword"))
        assert stack.total() == 3

    def test_empty_stack(self):
        """Empty stack totals 0."""
        stack = BonusStack()
        assert stack.total() == 0

    def test_breakdown_returns_sources(self):
        """Breakdown returns correct effective values and source info."""
        stack = BonusStack()
        stack.add(Bonus(2, "armor", "Chainmail"))
        stack.add(Bonus(5, "armor", "Full Plate"))
        stack.add(Bonus(1, "dodge", "Dodge"))
        breakdown = stack.breakdown()
        assert len(breakdown) == 2  # 2 types: armor, dodge
        armor_entry = next(e for e in breakdown if e["type"] == "armor")
        assert armor_entry["effective_value"] == 5  # highest
        dodge_entry = next(e for e in breakdown if e["type"] == "dodge")
        assert dodge_entry["effective_value"] == 1
