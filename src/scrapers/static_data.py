#!/usr/bin/env python3
"""
static_data.py — Static reference data for Pathfinder 1e.

Small, fixed datasets that don't need scraping. These are assembled from
the core rules and don't change between printings.

Includes:
  - Languages (complete list from Linguistics skill page)
  - Skills (all 35 skills with key ability)
"""

import json
from pathlib import Path
from .base import PARSED_DIR, save_json, ensure_dirs


# ============================================================
# LANGUAGES
# ============================================================

LANGUAGES = [
    # --- Common Languages ---
    {"name": "Common", "rarity": "Common", "script": "Common",
     "spoken_by": "Humans, halflings, half-elves, half-orcs"},
    {"name": "Dwarven", "rarity": "Common", "script": "Dwarven",
     "spoken_by": "Dwarves"},
    {"name": "Elven", "rarity": "Common", "script": "Elven",
     "spoken_by": "Elves, half-elves"},
    {"name": "Giant", "rarity": "Common", "script": "Dwarven",
     "spoken_by": "Ogres, giants"},
    {"name": "Gnome", "rarity": "Common", "script": "Dwarven",
     "spoken_by": "Gnomes"},
    {"name": "Goblin", "rarity": "Common", "script": "Dwarven",
     "spoken_by": "Goblins, hobgoblins, bugbears"},
    {"name": "Halfling", "rarity": "Common", "script": "Common",
     "spoken_by": "Halflings"},
    {"name": "Orc", "rarity": "Common", "script": "Dwarven",
     "spoken_by": "Orcs, half-orcs"},

    # --- Uncommon Languages ---
    {"name": "Abyssal", "rarity": "Uncommon", "script": "Infernal",
     "spoken_by": "Demons, chaotic evil outsiders"},
    {"name": "Aklo", "rarity": "Uncommon", "script": "—",
     "spoken_by": "Derro, inhuman or otherworldly monsters, evil fey"},
    {"name": "Aquan", "rarity": "Uncommon", "script": "Elven",
     "spoken_by": "Water-based creatures"},
    {"name": "Auran", "rarity": "Uncommon", "script": "Draconic",
     "spoken_by": "Air-based creatures"},
    {"name": "Celestial", "rarity": "Uncommon", "script": "Celestial",
     "spoken_by": "Angels, good outsiders"},
    {"name": "Draconic", "rarity": "Uncommon", "script": "Draconic",
     "spoken_by": "Kobolds, troglodytes, lizardfolk, dragons"},
    {"name": "Druidic", "rarity": "Secret", "script": "Druidic",
     "spoken_by": "Druids (only)"},
    {"name": "Gnoll", "rarity": "Uncommon", "script": "Common",
     "spoken_by": "Gnolls"},
    {"name": "Ignan", "rarity": "Uncommon", "script": "Draconic",
     "spoken_by": "Fire-based creatures"},
    {"name": "Infernal", "rarity": "Uncommon", "script": "Infernal",
     "spoken_by": "Devils, lawful evil outsiders"},
    {"name": "Necril", "rarity": "Uncommon", "script": "—",
     "spoken_by": "Ghouls, intelligent undead"},
    {"name": "Shadowtongue", "rarity": "Uncommon", "script": "—",
     "spoken_by": "Fetchlings, creatures of the Shadow Plane"},
    {"name": "Sylvan", "rarity": "Uncommon", "script": "Elven",
     "spoken_by": "Fey creatures, centaurs, plant creatures"},
    {"name": "Terran", "rarity": "Uncommon", "script": "Dwarven",
     "spoken_by": "Earth-based creatures"},
    {"name": "Undercommon", "rarity": "Uncommon", "script": "Elven",
     "spoken_by": "Drow, duergar, morlocks"},

    # --- Rare/Regional Languages ---
    {"name": "Boggard", "rarity": "Rare", "script": "—",
     "spoken_by": "Boggards"},
    {"name": "Catfolk", "rarity": "Rare", "script": "Common",
     "spoken_by": "Catfolk"},
    {"name": "Cyclops", "rarity": "Rare", "script": "Giant",
     "spoken_by": "Cyclopes"},
    {"name": "Dark Folk", "rarity": "Rare", "script": "—",
     "spoken_by": "Dark creepers, dark stalkers"},
    {"name": "D'ziriak", "rarity": "Rare", "script": "—",
     "spoken_by": "D'ziriak"},
    {"name": "Grippli", "rarity": "Rare", "script": "Common",
     "spoken_by": "Grippli"},
    {"name": "Protean", "rarity": "Rare", "script": "—",
     "spoken_by": "Proteans, chaotic outsiders"},
    {"name": "Samsaran", "rarity": "Rare", "script": "Samsaran",
     "spoken_by": "Samsarans"},
    {"name": "Sphinx", "rarity": "Rare", "script": "—",
     "spoken_by": "Sphinxes"},
    {"name": "Strix", "rarity": "Rare", "script": "Infernal",
     "spoken_by": "Strix"},
    {"name": "Tengu", "rarity": "Rare", "script": "Common",
     "spoken_by": "Tengu"},
    {"name": "Vanaran", "rarity": "Rare", "script": "Common",
     "spoken_by": "Vanaras"},
    {"name": "Vegepygmy", "rarity": "Rare", "script": "—",
     "spoken_by": "Vegepygmies (non-verbal, rhythmic tapping)"},
    {"name": "Vishkanya", "rarity": "Rare", "script": "Common",
     "spoken_by": "Vishkanya"},
    {"name": "Wayang", "rarity": "Rare", "script": "Common",
     "spoken_by": "Wayangs"},
]


# ============================================================
# SKILLS
# ============================================================

SKILLS = [
    {"name": "Acrobatics", "ability": "Dex", "trained_only": False, "armor_check_penalty": True},
    {"name": "Appraise", "ability": "Int", "trained_only": False, "armor_check_penalty": False},
    {"name": "Bluff", "ability": "Cha", "trained_only": False, "armor_check_penalty": False},
    {"name": "Climb", "ability": "Str", "trained_only": False, "armor_check_penalty": True},
    {"name": "Craft", "ability": "Int", "trained_only": False, "armor_check_penalty": False},
    {"name": "Diplomacy", "ability": "Cha", "trained_only": False, "armor_check_penalty": False},
    {"name": "Disable Device", "ability": "Dex", "trained_only": True, "armor_check_penalty": True},
    {"name": "Disguise", "ability": "Cha", "trained_only": False, "armor_check_penalty": False},
    {"name": "Escape Artist", "ability": "Dex", "trained_only": False, "armor_check_penalty": True},
    {"name": "Fly", "ability": "Dex", "trained_only": False, "armor_check_penalty": True},
    {"name": "Handle Animal", "ability": "Cha", "trained_only": True, "armor_check_penalty": False},
    {"name": "Heal", "ability": "Wis", "trained_only": False, "armor_check_penalty": False},
    {"name": "Intimidate", "ability": "Cha", "trained_only": False, "armor_check_penalty": False},
    {"name": "Knowledge (arcana)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (dungeoneering)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (engineering)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (geography)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (history)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (local)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (nature)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (nobility)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (planes)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Knowledge (religion)", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Linguistics", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Perception", "ability": "Wis", "trained_only": False, "armor_check_penalty": False},
    {"name": "Perform", "ability": "Cha", "trained_only": False, "armor_check_penalty": False},
    {"name": "Profession", "ability": "Wis", "trained_only": True, "armor_check_penalty": False},
    {"name": "Ride", "ability": "Dex", "trained_only": False, "armor_check_penalty": True},
    {"name": "Sense Motive", "ability": "Wis", "trained_only": False, "armor_check_penalty": False},
    {"name": "Sleight of Hand", "ability": "Dex", "trained_only": True, "armor_check_penalty": True},
    {"name": "Spellcraft", "ability": "Int", "trained_only": True, "armor_check_penalty": False},
    {"name": "Stealth", "ability": "Dex", "trained_only": False, "armor_check_penalty": True},
    {"name": "Survival", "ability": "Wis", "trained_only": False, "armor_check_penalty": False},
    {"name": "Swim", "ability": "Str", "trained_only": False, "armor_check_penalty": True},
    {"name": "Use Magic Device", "ability": "Cha", "trained_only": True, "armor_check_penalty": False},
]


# ============================================================
# EXPORT
# ============================================================

def export_static_data():
    """Write static reference data to parsed/ directory as JSON."""
    ensure_dirs()

    languages_path = PARSED_DIR / "languages.json"
    save_json(LANGUAGES, languages_path)
    print(f"  ✓ {len(LANGUAGES)} languages → {languages_path.name}")

    skills_path = PARSED_DIR / "skills.json"
    save_json(SKILLS, skills_path)
    print(f"  ✓ {len(SKILLS)} skills → {skills_path.name}")

    return {
        "languages": len(LANGUAGES),
        "skills": len(SKILLS),
    }


if __name__ == "__main__":
    print("Exporting static reference data...")
    counts = export_static_data()
    print(f"\nDone: {counts}")
