"""Skill rank tracking and total calculation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .character import Character
    from .db import RulesDB


_CLASS_SKILL_BONUS = 3   # PF1e trained class-skill bonus


def get_class_skills(char: "Character", db: "RulesDB") -> set[str]:
    """Return union of class skills across all class levels (lowercase names)."""
    class_skills: set[str] = set()
    for cl in char.class_levels:
        class_row = db.get_class(cl.class_name)
        if class_row is None:
            continue
        for skill_row in db.get_class_skills(class_row["id"]):
            class_skills.add(skill_row["name"].lower())
    return class_skills


def max_ranks(char: "Character") -> int:
    """Maximum ranks allowed in any single skill (= character level)."""
    return char.total_level


def _ability_for_skill(skill_name: str) -> str:
    """Return the governing ability for a skill (lowercase 3-letter key)."""
    skill_lower = skill_name.lower()
    # PF1e skill → ability mapping
    _MAP = {
        "acrobatics": "dex",
        "appraise": "int",
        "bluff": "cha",
        "climb": "str",
        "craft": "int",
        "diplomacy": "cha",
        "disable device": "dex",
        "disguise": "cha",
        "escape artist": "dex",
        "fly": "dex",
        "handle animal": "cha",
        "heal": "wis",
        "intimidate": "cha",
        "knowledge": "int",
        "linguistics": "int",
        "perception": "wis",
        "perform": "cha",
        "profession": "wis",
        "ride": "dex",
        "sense motive": "wis",
        "sleight of hand": "dex",
        "spellcraft": "int",
        "stealth": "dex",
        "survival": "wis",
        "swim": "str",
        "use magic device": "cha",
    }
    for key, ability in _MAP.items():
        if skill_lower.startswith(key):
            return ability
    return "int"   # fallback


def skill_total(skill_name: str, char: "Character", db: "RulesDB") -> int:
    """Compute skill check total = ranks + ability mod + class skill bonus + misc."""
    ranks = 0
    for k, v in char.skills.items():
        if k.lower() == skill_name.lower():
            ranks = v
            break

    ability = _ability_for_skill(skill_name)
    ability_mod = char.ability_mod(ability)

    trained_bonus = 0
    if ranks > 0:
        cs = get_class_skills(char, db)
        if skill_name.lower() in cs:
            trained_bonus = _CLASS_SKILL_BONUS

    return ranks + ability_mod + trained_bonus


def all_skill_totals(char: "Character", db: "RulesDB") -> dict[str, int]:
    """Return a dict of {skill_name: total} for every skill the character has ranks in."""
    return {skill: skill_total(skill, char, db) for skill in char.skills}
