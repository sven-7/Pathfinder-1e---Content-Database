"""CharacterBuilder — stateful wizard validator for character creation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.character_creator.ability_scores import ABILITIES, validate_point_buy

if TYPE_CHECKING:
    from src.rules_engine.db import RulesDB

# ────────────────────────────────────────────────────────────────────────────
# Hardcoded class data (DB fields not yet populated for all classes)
# ────────────────────────────────────────────────────────────────────────────

CLASS_HIT_DIE: dict[str, str] = {
    "Barbarian": "d12", "Unchained Barbarian": "d12",
    "Bard": "d8",
    "Cleric": "d8",
    "Druid": "d8",
    "Fighter": "d10",
    "Monk": "d8", "Unchained Monk": "d10",
    "Paladin": "d10", "Antipaladin": "d10",
    "Ranger": "d10",
    "Rogue": "d8", "Unchained Rogue": "d8",
    "Sorcerer": "d6",
    "Wizard": "d6",
    # APG
    "Alchemist": "d8",
    "Cavalier": "d10",
    "Gunslinger": "d10",
    "Inquisitor": "d8",
    "Magus": "d8",
    "Oracle": "d8",
    "Summoner": "d8", "Unchained Summoner": "d8",
    "Witch": "d6",
    # ACG
    "Arcanist": "d6",
    "Bloodrager": "d10",
    "Brawler": "d10",
    "Hunter": "d8",
    "Investigator": "d8",
    "Shaman": "d8",
    "Skald": "d8",
    "Slayer": "d10",
    "Swashbuckler": "d10",
    "Warpriest": "d8",
    # OA
    "Kineticist": "d8",
    "Medium": "d8",
    "Mesmerist": "d8",
    "Occultist": "d8",
    "Psychic": "d6",
    "Spiritualist": "d8",
    # Misc
    "Ninja": "d8",
    "Samurai": "d10",
    "Vigilante": "d8",
    "Shifter": "d10",
    "Omdura": "d8",
}

CLASS_SKILL_RANKS: dict[str, int] = {
    "Barbarian": 4, "Unchained Barbarian": 4,
    "Bard": 6,
    "Cleric": 2,
    "Druid": 4,
    "Fighter": 2,
    "Monk": 4, "Unchained Monk": 4,
    "Paladin": 2, "Antipaladin": 2,
    "Ranger": 6,
    "Rogue": 8, "Unchained Rogue": 8,
    "Sorcerer": 2,
    "Wizard": 2,
    "Alchemist": 4,
    "Cavalier": 4,
    "Gunslinger": 4,
    "Inquisitor": 6,
    "Magus": 2,
    "Oracle": 4,
    "Summoner": 2, "Unchained Summoner": 2,
    "Witch": 2,
    "Arcanist": 2,
    "Bloodrager": 4,
    "Brawler": 4,
    "Hunter": 6,
    "Investigator": 6,
    "Shaman": 4,
    "Skald": 4,
    "Slayer": 6,
    "Swashbuckler": 4,
    "Warpriest": 2,
    "Kineticist": 4,
    "Medium": 4,
    "Mesmerist": 6,
    "Occultist": 4,
    "Psychic": 2,
    "Spiritualist": 4,
    "Ninja": 8,
    "Samurai": 4,
    "Vigilante": 6,
    "Shifter": 4,
    "Omdura": 2,
}

HIT_DIE_AVG: dict[str, int] = {"d6": 4, "d8": 5, "d10": 6, "d12": 7}

# PF1e alignment choices
ALIGNMENTS = [
    "Lawful Good", "Neutral Good", "Chaotic Good",
    "Lawful Neutral", "True Neutral", "Chaotic Neutral",
    "Lawful Evil", "Neutral Evil", "Chaotic Evil",
]


class CharacterBuilder:
    """Validates character state at each wizard step."""

    def __init__(self, db: "RulesDB"):
        self.db = db
        self._data: dict = {
            "name": "",
            "player_name": "",
            "alignment": "True Neutral",
            "race": None,
            "race_row": None,
            "flexible_bonus": None,  # for Human/Half-Elf/Half-Orc
            "ability_scores": {a: 10 for a in ABILITIES},
            "class_name": None,
            "archetype": None,
            "feats": [],
            "traits": [],
            "skill_ranks": {},
            "hp_max": 0,
            "hp_current": 0,
            "notes": "",
        }

    # ── Step 1: Identity + Race ──────────────────────────────────────── #

    def set_identity(self, name: str, player_name: str, alignment: str) -> None:
        self._data["name"] = name.strip()
        self._data["player_name"] = player_name.strip()
        self._data["alignment"] = alignment

    def set_race(self, race_name: str) -> dict:
        row = self.db.get_race(race_name)
        if row is None:
            raise ValueError(f"Unknown race: {race_name!r}")
        self._data["race"] = race_name
        self._data["race_row"] = row
        return row

    # ── Step 2: Ability Scores ───────────────────────────────────────── #

    def set_ability_scores(self, scores: dict[str, int], flexible_bonus: str | None = None) -> None:
        for ab in ABILITIES:
            self._data["ability_scores"][ab] = int(scores.get(ab, 10))
        self._data["flexible_bonus"] = flexible_bonus

    # ── Step 3: Class + Archetype ────────────────────────────────────── #

    def set_class(self, class_name: str, archetype: str | None = None) -> dict:
        row = self.db.get_class(class_name)
        if row is None:
            raise ValueError(f"Unknown class: {class_name!r}")
        self._data["class_name"] = class_name
        self._data["archetype"] = archetype
        return row

    # ── Step 4: Feats ────────────────────────────────────────────────── #

    def add_feat(self, feat_name: str) -> None:
        if feat_name not in self._data["feats"]:
            self._data["feats"].append(feat_name)

    def remove_feat(self, feat_name: str) -> None:
        self._data["feats"] = [f for f in self._data["feats"] if f != feat_name]

    def feat_budget(self) -> int:
        """Base feat budget at level 1 (1 standard + class bonuses)."""
        budget = 1
        class_name = self._data.get("class_name", "")
        if class_name == "Fighter":
            budget += 1  # bonus combat feat at 1st
        race = self._data.get("race", "")
        if race in ("Human", "Half-Elf"):
            budget += 1  # bonus feat at 1st
        return budget

    # ── Step 4: Traits ───────────────────────────────────────────────── #

    def add_trait(self, trait_name: str) -> None:
        if len(self._data["traits"]) >= 2:
            raise ValueError("Maximum 2 traits allowed")
        if trait_name not in self._data["traits"]:
            self._data["traits"].append(trait_name)

    def remove_trait(self, trait_name: str) -> None:
        self._data["traits"] = [t for t in self._data["traits"] if t != trait_name]

    # ── Step 5: Skills ───────────────────────────────────────────────── #

    def skill_budget(self) -> int:
        """Skill ranks available at level 1."""
        class_name = self._data.get("class_name", "")
        ranks_per_level = CLASS_SKILL_RANKS.get(class_name, 2)
        int_mod = (self._data["ability_scores"].get("int", 10) - 10) // 2
        total = max(1, ranks_per_level + int_mod)
        # Human bonus skill rank
        if self._data.get("race") == "Human":
            total += 1
        return total

    def set_skill_ranks(self, ranks: dict[str, int]) -> None:
        self._data["skill_ranks"] = {k: max(0, int(v)) for k, v in ranks.items() if v > 0}

    # ── HP calculation ───────────────────────────────────────────────── #

    def compute_hp(self, method: str = "max_first") -> int:
        """Compute HP. Builder creates L1 characters so this is single-level.

        method: 'max_first' / 'max' → max die; 'average' → avg die.
        """
        class_name = self._data.get("class_name", "Fighter")
        hit_die = CLASS_HIT_DIE.get(class_name, "d8")
        die_max = int(hit_die[1:])
        die_avg = HIT_DIE_AVG.get(hit_die, die_max // 2 + 1)
        con_mod = (self._data["ability_scores"].get("con", 10) - 10) // 2
        if method == "average":
            base = die_avg
        else:
            base = die_max
        hp = max(1, base + con_mod)
        self._data["hp_max"] = hp
        self._data["hp_current"] = hp
        return hp

    # ── Validation ───────────────────────────────────────────────────── #

    def validate(self) -> list[str]:
        issues: list[str] = []
        if not self._data["name"]:
            issues.append("Character name is required.")
        if not self._data["race"]:
            issues.append("Race selection is required.")
        if not self._data["class_name"]:
            issues.append("Class selection is required.")
        return issues

    # ── Build final character dict ────────────────────────────────────── #

    def build_dict(self) -> dict:
        """Return complete character dict suitable for JSON storage."""
        import uuid
        self.compute_hp()
        return {
            "id": str(uuid.uuid4()),
            "name": self._data["name"],
            "player_name": self._data["player_name"],
            "alignment": self._data["alignment"],
            "race": self._data["race"] or "",
            "ability_scores": dict(self._data["ability_scores"]),
            "class_levels": [
                {
                    "class_name": self._data["class_name"],
                    "level": 1,
                    "archetype_name": self._data["archetype"],
                }
            ] if self._data["class_name"] else [],
            "feats": list(self._data["feats"]),
            "traits": list(self._data["traits"]),
            "skills": dict(self._data["skill_ranks"]),
            "equipment": [],
            "conditions": [],
            "hp_max": self._data["hp_max"],
            "hp_current": self._data["hp_current"],
            "notes": self._data.get("notes", ""),
        }
