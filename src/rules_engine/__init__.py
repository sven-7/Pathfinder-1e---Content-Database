"""PF1e Rules Engine — public API surface."""

from .db import RulesDB
from .character import Character, ClassLevel, ability_modifier
from .bonuses import Bonus, BonusStack, STACKABLE_TYPES
from .prerequisites import (
    parse_prerequisites,
    check_prerequisites,
    get_available_feats,
    PrereqResult,
    ConditionResult,
    ConditionType,
    Condition,
)
from .progression import (
    get_bab,
    get_save,
    get_hp,
    get_spell_slots,
    parse_class_progression_html,
    LevelRow,
)
from .skills import skill_total, get_class_skills, all_skill_totals
from .combat import ac, attack_bonus, cmb, cmd, initiative, ACBreakdown

__all__ = [
    # DB
    "RulesDB",
    # Character
    "Character",
    "ClassLevel",
    "ability_modifier",
    # Bonuses
    "Bonus",
    "BonusStack",
    "STACKABLE_TYPES",
    # Prerequisites
    "parse_prerequisites",
    "check_prerequisites",
    "get_available_feats",
    "PrereqResult",
    "ConditionResult",
    "ConditionType",
    "Condition",
    # Progression
    "get_bab",
    "get_save",
    "get_hp",
    "get_spell_slots",
    "parse_class_progression_html",
    "LevelRow",
    # Skills
    "skill_total",
    "get_class_skills",
    "all_skill_totals",
    # Combat
    "ac",
    "attack_bonus",
    "cmb",
    "cmd",
    "initiative",
    "ACBreakdown",
]
