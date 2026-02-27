"""Character dataclass — central state container for the rules engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .db import RulesDB

# Ability score short names (lowercase)
ABILITIES = ("str", "dex", "con", "int", "wis", "cha")


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


@dataclass
class ClassLevel:
    class_name: str
    level: int
    archetype_name: str | None = None

    def to_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "level": self.level,
            "archetype_name": self.archetype_name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ClassLevel":
        return cls(
            class_name=d["class_name"],
            level=d["level"],
            archetype_name=d.get("archetype_name"),
        )


@dataclass
class Character:
    name: str
    race: str
    alignment: str
    ability_scores: dict[str, int]      # {"str": 16, "dex": 14, ...}
    class_levels: list[ClassLevel]
    feats: list[str] = field(default_factory=list)
    traits: list[str] = field(default_factory=list)
    skills: dict[str, int] = field(default_factory=dict)   # {skill_name: ranks}
    equipment: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Basic derived properties (no DB needed)                             #
    # ------------------------------------------------------------------ #

    @property
    def total_level(self) -> int:
        return sum(cl.level for cl in self.class_levels)

    @property
    def ability_modifiers(self) -> dict[str, int]:
        return {ab: ability_modifier(score) for ab, score in self.ability_scores.items()}

    def ability_mod(self, ability: str) -> int:
        return ability_modifier(self.ability_scores.get(ability.lower(), 10))

    # ------------------------------------------------------------------ #
    # Derived stats requiring a DB (imported lazily to avoid cycles)      #
    # ------------------------------------------------------------------ #

    def bab(self, db: "RulesDB") -> int:
        from .progression import get_bab
        return get_bab(self.class_levels, db)

    def fort_save(self, db: "RulesDB") -> int:
        from .progression import get_save
        return get_save(self.class_levels, "fort", db) + self.ability_mod("con")

    def ref_save(self, db: "RulesDB") -> int:
        from .progression import get_save
        return get_save(self.class_levels, "ref", db) + self.ability_mod("dex")

    def will_save(self, db: "RulesDB") -> int:
        from .progression import get_save
        return get_save(self.class_levels, "will", db) + self.ability_mod("wis")

    def hp(self, db: "RulesDB", favored_class_hp: int = 0) -> int:
        from .progression import get_hp
        return get_hp(self.class_levels, self.ability_mod("con"), favored_class_hp, db)

    def initiative(self, db: "RulesDB") -> int:
        from .combat import initiative
        return initiative(self, db)

    def ac(self, db: "RulesDB"):
        from .combat import ac
        return ac(self, db)

    def cmb(self, db: "RulesDB") -> int:
        from .combat import cmb
        return cmb(self, db)

    def cmd(self, db: "RulesDB") -> int:
        from .combat import cmd
        return cmd(self, db)

    # ------------------------------------------------------------------ #
    # Serialisation                                                        #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "race": self.race,
            "alignment": self.alignment,
            "ability_scores": dict(self.ability_scores),
            "class_levels": [cl.to_dict() for cl in self.class_levels],
            "feats": list(self.feats),
            "traits": list(self.traits),
            "skills": dict(self.skills),
            "equipment": list(self.equipment),
            "conditions": list(self.conditions),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Character":
        return cls(
            name=d["name"],
            race=d["race"],
            alignment=d["alignment"],
            ability_scores=d["ability_scores"],
            class_levels=[ClassLevel.from_dict(cl) for cl in d.get("class_levels", [])],
            feats=d.get("feats", []),
            traits=d.get("traits", []),
            skills=d.get("skills", {}),
            equipment=d.get("equipment", []),
            conditions=d.get("conditions", []),
        )
