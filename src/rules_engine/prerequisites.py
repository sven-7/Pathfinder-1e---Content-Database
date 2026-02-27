"""Prerequisite parser and checker for PF1e feats."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .character import Character
    from .db import RulesDB


class ConditionType(Enum):
    ABILITY_SCORE = "ability_score"   # "Str 13"
    BAB           = "bab"             # "base attack bonus +6"
    FEAT          = "feat"            # "Power Attack"
    CLASS_FEATURE = "class_feature"   # "channel energy class feature"
    CASTER_LEVEL  = "caster_level"    # "Caster level 5th"
    SKILL_RANKS   = "skill_ranks"     # "Knowledge (religion) 5 ranks"
    CLASS_LEVEL   = "class_level"     # "Fighter level 4th"
    RACE          = "race"            # "Human"
    CHAR_LEVEL    = "char_level"      # "character level 10th"
    SPECIAL       = "special"         # free-text we can't parse


@dataclass
class Condition:
    ctype: ConditionType
    raw: str
    params: dict = field(default_factory=dict)


@dataclass
class ConditionGroup:
    """A group of conditions joined by OR (any one must be met)."""
    conditions: list[Condition]
    any: bool = True    # True = OR logic, False = AND logic


@dataclass
class ConditionResult:
    condition: Condition
    met: bool
    reason: str = ""


@dataclass
class PrereqResult:
    met: bool
    conditions: list[ConditionResult] = field(default_factory=list)
    raw_text: str = ""


# ------------------------------------------------------------------ #
# Ordinal helper                                                       #
# ------------------------------------------------------------------ #

_ORD_RE = re.compile(r"(\d+)(?:st|nd|rd|th)", re.IGNORECASE)


def _parse_ordinal(text: str) -> int | None:
    m = _ORD_RE.search(text)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------ #
# Known feat names (populated lazily from DB)                         #
# ------------------------------------------------------------------ #

_KNOWN_ABILITIES = {"str", "dex", "con", "int", "wis", "cha"}
_ABILITY_FULL = {
    "strength": "str", "dexterity": "dex", "constitution": "con",
    "intelligence": "int", "wisdom": "wis", "charisma": "cha",
}

# ------------------------------------------------------------------ #
# Regex patterns                                                       #
# ------------------------------------------------------------------ #

_BAB_RE = re.compile(r"base attack bonus \+(\d+)", re.IGNORECASE)
_ABILITY_RE = re.compile(
    r"\b(Str|Dex|Con|Int|Wis|Cha)\s+(\d+)\b", re.IGNORECASE
)
_CLASS_FEATURE_RE = re.compile(
    r"(.+?)\s+class feature", re.IGNORECASE
)
_CASTER_LEVEL_RE = re.compile(
    r"[Cc]aster level\s+(\d+)(?:st|nd|rd|th)", re.IGNORECASE
)
_SKILL_RE = re.compile(
    r"([A-Z][a-zA-Z\s]+(?:\([^)]+\))?)\s+(\d+)\s+ranks?", re.IGNORECASE
)
_CLASS_LEVEL_RE = re.compile(
    r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s+level\s+(\d+)(?:st|nd|rd|th)", re.IGNORECASE
)
_CHAR_LEVEL_RE = re.compile(
    r"character level\s+(\d+)(?:st|nd|rd|th)", re.IGNORECASE
)


def _parse_single_condition(token: str) -> Condition:
    token = token.strip().rstrip(".")

    # BAB
    m = _BAB_RE.search(token)
    if m:
        return Condition(ConditionType.BAB, token, {"min_bab": int(m.group(1))})

    # Character level
    m = _CHAR_LEVEL_RE.search(token)
    if m:
        return Condition(ConditionType.CHAR_LEVEL, token, {"min_level": int(m.group(1))})

    # Class level  (must come before ability — avoids "Fighter level" matching ability)
    m = _CLASS_LEVEL_RE.search(token)
    if m:
        class_name = m.group(1).strip()
        # Exclude false positives like "caster level" (already handled above)
        if class_name.lower() not in ("caster",):
            return Condition(
                ConditionType.CLASS_LEVEL, token,
                {"class_name": class_name, "min_level": int(m.group(2))},
            )

    # Ability score
    m = _ABILITY_RE.search(token)
    if m:
        return Condition(
            ConditionType.ABILITY_SCORE, token,
            {"ability": m.group(1).lower(), "min_value": int(m.group(2))},
        )

    # Class feature
    m = _CLASS_FEATURE_RE.search(token)
    if m:
        return Condition(
            ConditionType.CLASS_FEATURE, token,
            {"feature_name": m.group(1).strip().lower()},
        )

    # Caster level
    m = _CASTER_LEVEL_RE.search(token)
    if m:
        return Condition(ConditionType.CASTER_LEVEL, token, {"min_level": int(m.group(1))})

    # Skill ranks
    m = _SKILL_RE.search(token)
    if m:
        skill = m.group(1).strip()
        return Condition(
            ConditionType.SKILL_RANKS, token,
            {"skill": skill, "min_ranks": int(m.group(2))},
        )

    # Feat or race name: short word/phrase with no digits and no keyword markers.
    # Handles both "Power Attack" (capitalised) and "aasimar" (lowercase race names).
    # The checker resolves ambiguity by checking both the feats and races tables.
    stripped = token.strip()
    _skip_words = {"level", "feat", "class feature", "bonus", "rank", "proficiency"}
    if (
        stripped
        and not any(c.isdigit() for c in stripped)
        and not any(w in stripped.lower() for w in _skip_words)
        and len(stripped.split()) <= 4
    ):
        return Condition(ConditionType.FEAT, token, {"feat_name": stripped})

    return Condition(ConditionType.SPECIAL, token, {})


def parse_prerequisites(raw_text: str) -> list[Condition | ConditionGroup]:
    """Parse raw prerequisite text into a list of Condition/ConditionGroup objects."""
    if not raw_text:
        return []

    results: list[Condition | ConditionGroup] = []

    # Split on commas (primary separator), then handle OR within each chunk
    for chunk in raw_text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue

        # Check for OR
        or_parts = re.split(r"\bor\b", chunk, flags=re.IGNORECASE)
        if len(or_parts) > 1:
            conditions = [_parse_single_condition(p) for p in or_parts]
            results.append(ConditionGroup(conditions=conditions, any=True))
        else:
            results.append(_parse_single_condition(chunk))

    return results


# ------------------------------------------------------------------ #
# Prerequisite checker                                                 #
# ------------------------------------------------------------------ #

def _check_condition(cond: Condition, char: "Character", db: "RulesDB") -> ConditionResult:
    ct = cond.ctype
    p = cond.params

    if ct == ConditionType.ABILITY_SCORE:
        ability = p["ability"]
        needed = p["min_value"]
        have = char.ability_scores.get(ability, 10)
        met = have >= needed
        return ConditionResult(cond, met, f"{ability.upper()} {have} (need {needed})")

    if ct == ConditionType.BAB:
        needed = p["min_bab"]
        have = char.bab(db)
        met = have >= needed
        return ConditionResult(cond, met, f"BAB +{have} (need +{needed})")

    if ct == ConditionType.FEAT:
        feat_name = p["feat_name"]
        met = feat_name in char.feats
        # Also check races table as fallback
        if not met:
            race_row = db.get_race(feat_name)
            if race_row:
                met = char.race.lower() == feat_name.lower()
        return ConditionResult(cond, met, f"feat '{feat_name}' {'found' if met else 'missing'}")

    if ct == ConditionType.CLASS_FEATURE:
        feature_name = p["feature_name"].lower()
        # Check class features from DB for all of the character's classes
        met = False
        for cl in char.class_levels:
            class_row = db.get_class(cl.class_name)
            if not class_row:
                continue
            features = db.get_class_features(class_row["id"])
            for f in features:
                if feature_name in f["name"].lower() and f["level"] <= cl.level:
                    met = True
                    break
            if met:
                break
        return ConditionResult(cond, met, f"class feature '{feature_name}' {'present' if met else 'absent'}")

    if ct == ConditionType.CASTER_LEVEL:
        needed = p["min_level"]
        # Sum levels in spellcasting classes
        caster_level = 0
        for cl in char.class_levels:
            class_row = db.get_class(cl.class_name)
            if class_row and class_row.get("spellcasting_type"):
                caster_level += cl.level
        met = caster_level >= needed
        return ConditionResult(cond, met, f"caster level {caster_level} (need {needed})")

    if ct == ConditionType.SKILL_RANKS:
        skill = p["skill"]
        needed = p["min_ranks"]
        have = char.skills.get(skill, 0)
        # Also try case-insensitive lookup
        if have == 0:
            for k, v in char.skills.items():
                if k.lower() == skill.lower():
                    have = v
                    break
        met = have >= needed
        return ConditionResult(cond, met, f"{skill} {have} ranks (need {needed})")

    if ct == ConditionType.CLASS_LEVEL:
        class_name = p["class_name"]
        needed = p["min_level"]
        have = sum(cl.level for cl in char.class_levels if cl.class_name.lower() == class_name.lower())
        met = have >= needed
        return ConditionResult(cond, met, f"{class_name} level {have} (need {needed})")

    if ct == ConditionType.CHAR_LEVEL:
        needed = p["min_level"]
        have = char.total_level
        met = have >= needed
        return ConditionResult(cond, met, f"character level {have} (need {needed})")

    if ct == ConditionType.RACE:
        race_name = p.get("race_name", cond.raw)
        met = char.race.lower() == race_name.lower()
        return ConditionResult(cond, met, f"race '{char.race}' (need '{race_name}')")

    # SPECIAL — cannot check, assume not met
    return ConditionResult(cond, False, f"unhandled condition: '{cond.raw}'")


def check_prerequisites(feat_name: str, char: "Character", db: "RulesDB") -> PrereqResult:
    """Check whether a character meets the prerequisites for a named feat."""
    feat_row = db.get_feat(feat_name)
    if feat_row is None:
        return PrereqResult(met=False, raw_text="", conditions=[
            ConditionResult(
                Condition(ConditionType.SPECIAL, "feat not found", {}),
                False, f"feat '{feat_name}' not found in DB",
            )
        ])

    raw_text = feat_row.get("prerequisites") or ""
    if not raw_text:
        return PrereqResult(met=True, raw_text="", conditions=[])

    parsed = parse_prerequisites(raw_text)
    results: list[ConditionResult] = []
    all_met = True

    for item in parsed:
        if isinstance(item, ConditionGroup):
            group_results = [_check_condition(c, char, db) for c in item.conditions]
            group_met = any(r.met for r in group_results) if item.any else all(r.met for r in group_results)
            results.extend(group_results)
            if not group_met:
                all_met = False
        else:
            cr = _check_condition(item, char, db)
            results.append(cr)
            if not cr.met:
                all_met = False

    return PrereqResult(met=all_met, conditions=results, raw_text=raw_text)


def get_available_feats(char: "Character", db: "RulesDB") -> list[str]:
    """Return feat names whose prerequisites the character currently meets."""
    available = []
    for feat in db.get_all_feats():
        name = feat["name"]
        if name in char.feats:
            continue
        result = check_prerequisites(name, char, db)
        if result.met:
            available.append(name)
    return available
