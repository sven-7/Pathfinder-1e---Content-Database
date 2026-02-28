"""Shared fixtures for PF1e rules engine tests."""

import os
import pathlib
import pytest

from src.rules_engine.db import RulesDB
from src.rules_engine.character import Character, ClassLevel

DB_PATH = pathlib.Path(__file__).parent.parent / "db" / "pf1e.db"


@pytest.fixture(scope="session")
def db():
    """Content database — uses PG if CONTENT_DATABASE_URL is set, else SQLite."""
    content_dsn = os.getenv("CONTENT_DATABASE_URL")
    if content_dsn:
        # Strip +asyncpg suffix if someone copies the async DSN
        dsn = content_dsn.replace("+asyncpg", "")
        rdb = RulesDB(dsn)
    else:
        rdb = RulesDB(str(DB_PATH))
    yield rdb
    rdb.close()


# ── Kairon (Investigator, Tiefling) ──────────────────────────────────────

_KAIRON_SCORES = {"str": 10, "dex": 14, "con": 12, "int": 18, "wis": 14, "cha": 12}


@pytest.fixture
def kairon_l5():
    """Kairon — Tiefling Investigator L5."""
    return Character(
        name="Kairon",
        race="Tiefling",
        alignment="CG",
        ability_scores=dict(_KAIRON_SCORES),
        class_levels=[ClassLevel("Investigator", 5)],
        feats=["Extra Investigator Talent"],
        traits=["Reactionary"],
        skills={
            "Perception": 5,
            "Knowledge (Arcana)": 5,
            "Spellcraft": 5,
            "Disable Device": 5,
            "Diplomacy": 5,
        },
    )


@pytest.fixture
def kairon_l9():
    """Kairon — Tiefling Investigator L9."""
    return Character(
        name="Kairon",
        race="Tiefling",
        alignment="CG",
        ability_scores=dict(_KAIRON_SCORES),
        class_levels=[ClassLevel("Investigator", 9)],
        feats=["Extra Investigator Talent", "Iron Will"],
        traits=["Reactionary"],
        skills={
            "Perception": 9,
            "Knowledge (Arcana)": 9,
            "Spellcraft": 9,
            "Disable Device": 9,
            "Diplomacy": 9,
        },
    )


# ── Human Fighter L6 ──────────────────────────────────────────────────────

@pytest.fixture
def fighter_l6():
    """Human Fighter L6 — full BAB, iterative attacks."""
    return Character(
        name="Valeros",
        race="Human",
        alignment="NG",
        ability_scores={"str": 18, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8},
        class_levels=[ClassLevel("Fighter", 6)],
        feats=["Power Attack", "Weapon Focus (longsword)"],
        skills={"Climb": 6, "Swim": 6, "Intimidate": 6},
    )


# ── Multi-class Fighter 3 / Rogue 2 ─────────────────────────────────────

@pytest.fixture
def multiclass_fighter3_rogue2():
    """Multi-class: Fighter 3 / Rogue 2 — for save stacking tests."""
    return Character(
        name="Harsk",
        race="Dwarf",
        alignment="LN",
        ability_scores={"str": 16, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8},
        class_levels=[ClassLevel("Fighter", 3), ClassLevel("Rogue", 2)],
        feats=["Power Attack"],
        skills={"Climb": 3, "Stealth": 2, "Perception": 2},
    )


# ── Human Fighter L1 (for feat/skill budget integration tests) ───────────

@pytest.fixture
def fighter_l1():
    """Human Fighter L1 — 3 feats (L1 + Fighter bonus + Human bonus)."""
    return Character(
        name="TestFighter",
        race="Human",
        alignment="N",
        ability_scores={"str": 16, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8},
        class_levels=[ClassLevel("Fighter", 1)],
        feats=["Power Attack", "Weapon Focus (longsword)", "Toughness"],
        skills={"Climb": 1, "Swim": 1, "Intimidate": 1},
    )
