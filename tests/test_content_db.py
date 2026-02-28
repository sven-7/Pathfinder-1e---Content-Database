"""Validation tests for content database (SQLite or PostgreSQL).

These tests verify the content data is present and queryable, regardless
of which backend the db fixture connects to.
"""

import pytest


class TestContentCounts:
    """Verify expected row counts for key content tables."""

    def test_class_count(self, db):
        rows = db.get_all_classes()
        assert len(rows) >= 60, f"Expected >=60 classes, got {len(rows)}"

    def test_feat_count(self, db):
        rows = db.get_all_feats()
        assert len(rows) >= 3900, f"Expected >=3900 feats, got {len(rows)}"

    def test_skill_count(self, db):
        rows = db.get_all_skills()
        assert len(rows) == 26, f"Expected 26 skills, got {len(rows)}"

    def test_weapons_populated(self, db):
        rows = db.get_weapons()
        assert len(rows) >= 70, f"Expected >=70 weapons, got {len(rows)}"

    def test_armor_populated(self, db):
        rows = db.get_armor()
        assert len(rows) >= 25, f"Expected >=25 armor, got {len(rows)}"


class TestContentLookups:
    """Verify specific content items are retrievable."""

    def test_fighter_exists(self, db):
        cls = db.get_class("Fighter")
        assert cls is not None
        assert cls["name"] == "Fighter"
        assert cls["hit_die"] == "d10"

    def test_class_progression_populated(self, db):
        cls = db.get_class("Fighter")
        assert cls is not None
        prog = db.get_class_progression(cls["id"])
        assert len(prog) == 20, f"Expected 20 progression rows for Fighter, got {len(prog)}"

    def test_spell_class_levels(self, db):
        spells = db.get_spells_for_class("wizard", 1)
        assert len(spells) > 0, "Expected wizard level 1 spells"

    def test_search_returns_results(self, db):
        results = db.search("fireball")
        assert len(results) >= 1, "Expected search('fireball') to return >=1 result"
