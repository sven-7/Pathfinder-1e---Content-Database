"""
populate_class_skills.py — Populate the class_skills table from three sources:

  1. CoreForge 'Archetype Definitions' sheet col 14 → CRB + APG base classes
  2. Foundry pf-prestige-classes.db → prestige class classSkills dicts
  3. Hardcoded data → ACG/OA/Unchained/UI/UW/NPC classes not in CoreForge

Run:
    python scripts/populate_class_skills.py [--dry-run]
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "pf1e.db"
COREFORGE_PATH = ROOT / "example_content" / "Pathfinder-sCoreForge-7.4.0.1.xlsb"
FOUNDRY_PRESTIGE = ROOT / "data" / "foundry-archetypes" / "packs" / "pf-prestige-classes.db"

# ── Skill name → DB skill_id mapping ─────────────────────────────────────── #
# The DB has 26 skills.  All Knowledge (x) sub-skills map to id=14.
# "Craft", "Crafts" → 5; "Perform*", "Performs" → 17; "Profession*" → 18.

SKILL_NAME_MAP: dict[str, int] = {
    "acrobatics": 1,
    "appraise": 2,
    "bluff": 3,
    "climb": 4,
    "craft": 5,
    "crafts": 5,
    "diplomacy": 6,
    "disable device": 7,
    "disguise": 8,
    "escape artist": 9,
    "fly": 10,
    "handle animal": 11,
    "heal": 12,
    "intimidate": 13,
    "knowledge": 14,          # any Knowledge (x) sub-skill
    "linguistics": 15,
    "perception": 16,
    "perform": 17,
    "performs": 17,
    "profession": 18,
    "ride": 19,
    "sense motive": 20,
    "sleight of hand": 21,
    "spellcraft": 22,
    "stealth": 23,
    "survival": 24,
    "swim": 25,
    "use magic device": 26,
}

# Foundry abbreviation → skill_id
FOUNDRY_ABBR_MAP: dict[str, int] = {
    "acr": 1, "apr": 2, "blf": 3, "clm": 4, "crf": 5,
    "dip": 6, "dev": 7, "dis": 8, "esc": 9, "fly": 10,
    "han": 11, "hea": 12, "int": 13,
    # All Knowledge sub-keys → 14
    "kar": 14, "kdu": 14, "ken": 14, "kge": 14, "khi": 14,
    "klo": 14, "kna": 14, "kno": 14, "kpl": 14, "kre": 14,
    "lin": 15, "per": 16, "prf": 17, "pro": 18, "rid": 19,
    "sen": 20, "slt": 21, "spl": 22, "ste": 23, "sur": 24,
    "swm": 25, "umd": 26,
    # "art" (Artistry) and "lor" (Lore) are not standard PF1e skills → skip
}


def parse_coreforge_skill_str(s: str) -> set[int]:
    """Parse a CoreForge comma-separated skill string into a set of skill_ids."""
    if not s:
        return set()
    ids: set[int] = set()
    for token in s.split(","):
        token = token.strip()
        if not token:
            continue
        lower = token.lower()
        # Normalise: strip sub-skill in parens for Knowledge / Perform / Craft
        base = re.split(r"\s*\(", lower)[0].strip()
        sid = SKILL_NAME_MAP.get(lower) or SKILL_NAME_MAP.get(base)
        if sid:
            ids.add(sid)
        else:
            print(f"  [warn] unknown skill token: '{token}'", file=sys.stderr)
    return ids


# ── Hardcoded class skills for classes NOT in CoreForge ───────────────────── #
# Sources: d20pfsrd.com / Paizo SRDs for each class
# Format: class name (matching DB) → list of DB skill_ids

_S = SKILL_NAME_MAP  # shorthand

HARDCODED: dict[str, set[int]] = {
    # ── ACG Hybrid classes (Advanced Class Guide 2014) ────────────────────
    "Arcanist": {
        _S["appraise"], _S["craft"], _S["fly"],
        _S["knowledge"], _S["profession"], _S["spellcraft"], _S["use magic device"],
    },
    "Bloodrager": {
        _S["acrobatics"], _S["climb"], _S["craft"], _S["handle animal"],
        _S["intimidate"], _S["knowledge"], _S["perception"], _S["ride"],
        _S["survival"], _S["swim"], _S["use magic device"],
    },
    "Brawler": {
        _S["acrobatics"], _S["climb"], _S["craft"], _S["escape artist"],
        _S["handle animal"], _S["intimidate"], _S["knowledge"], _S["perception"],
        _S["profession"], _S["ride"], _S["sense motive"], _S["swim"],
    },
    "Hunter": {
        _S["acrobatics"], _S["bluff"], _S["climb"], _S["craft"],
        _S["handle animal"], _S["heal"], _S["intimidate"], _S["knowledge"],
        _S["perception"], _S["profession"], _S["ride"], _S["spellcraft"],
        _S["stealth"], _S["survival"], _S["swim"],
    },
    "Investigator": {
        _S["appraise"], _S["bluff"], _S["craft"], _S["diplomacy"],
        _S["disable device"], _S["disguise"], _S["escape artist"], _S["heal"],
        _S["intimidate"], _S["knowledge"], _S["linguistics"], _S["perception"],
        _S["perform"], _S["profession"], _S["sense motive"], _S["sleight of hand"],
        _S["spellcraft"], _S["stealth"], _S["use magic device"],
    },
    "Shaman": {
        _S["bluff"], _S["craft"], _S["diplomacy"], _S["fly"],
        _S["handle animal"], _S["heal"], _S["knowledge"], _S["linguistics"],
        _S["perception"], _S["profession"], _S["ride"], _S["sense motive"],
        _S["spellcraft"], _S["survival"],
    },
    "Skald": {
        _S["acrobatics"], _S["bluff"], _S["climb"], _S["craft"],
        _S["diplomacy"], _S["escape artist"], _S["intimidate"], _S["knowledge"],
        _S["linguistics"], _S["perception"], _S["perform"], _S["profession"],
        _S["ride"], _S["sense motive"], _S["spellcraft"], _S["swim"],
        _S["use magic device"],
    },
    "Slayer": {
        _S["acrobatics"], _S["bluff"], _S["climb"], _S["craft"],
        _S["disguise"], _S["handle animal"], _S["heal"], _S["intimidate"],
        _S["knowledge"], _S["perception"], _S["profession"], _S["ride"],
        _S["sense motive"], _S["stealth"], _S["survival"], _S["swim"],
    },
    "Swashbuckler": {
        _S["acrobatics"], _S["bluff"], _S["climb"], _S["craft"],
        _S["diplomacy"], _S["escape artist"], _S["intimidate"], _S["knowledge"],
        _S["perception"], _S["perform"], _S["profession"], _S["ride"],
        _S["sense motive"], _S["sleight of hand"], _S["survival"], _S["swim"],
    },
    "Warpriest": {
        _S["climb"], _S["craft"], _S["diplomacy"], _S["handle animal"],
        _S["heal"], _S["intimidate"], _S["knowledge"], _S["linguistics"],
        _S["profession"], _S["ride"], _S["sense motive"], _S["spellcraft"],
        _S["survival"], _S["swim"],
    },
    # ── Occult Adventures classes (2015) ─────────────────────────────────
    "Kineticist": {
        _S["acrobatics"], _S["craft"], _S["heal"], _S["intimidate"],
        _S["knowledge"], _S["perception"], _S["stealth"], _S["survival"],
        _S["use magic device"],
    },
    "Medium": {
        _S["bluff"], _S["craft"], _S["diplomacy"], _S["fly"],
        _S["heal"], _S["intimidate"], _S["knowledge"], _S["linguistics"],
        _S["perception"], _S["profession"], _S["sense motive"],
        _S["spellcraft"], _S["use magic device"],
    },
    "Mesmerist": {
        _S["bluff"], _S["craft"], _S["diplomacy"], _S["disguise"],
        _S["escape artist"], _S["intimidate"], _S["knowledge"], _S["linguistics"],
        _S["perception"], _S["profession"], _S["sense motive"],
        _S["sleight of hand"], _S["spellcraft"], _S["stealth"],
        _S["use magic device"],
    },
    "Occultist": {
        _S["appraise"], _S["craft"], _S["diplomacy"], _S["disable device"],
        _S["fly"], _S["heal"], _S["knowledge"], _S["linguistics"],
        _S["perception"], _S["profession"], _S["sense motive"],
        _S["spellcraft"], _S["use magic device"],
    },
    "Psychic": {
        _S["bluff"], _S["craft"], _S["diplomacy"], _S["fly"],
        _S["intimidate"], _S["knowledge"], _S["linguistics"],
        _S["perception"], _S["profession"], _S["sense motive"], _S["spellcraft"],
    },
    "Spiritualist": {
        _S["bluff"], _S["craft"], _S["fly"], _S["heal"],
        _S["intimidate"], _S["knowledge"], _S["linguistics"],
        _S["perception"], _S["profession"], _S["sense motive"],
        _S["spellcraft"], _S["use magic device"],
    },
    # ── Pathfinder Unchained (2015) ───────────────────────────────────────
    "Unchained Barbarian": {
        _S["acrobatics"], _S["climb"], _S["craft"], _S["handle animal"],
        _S["intimidate"], _S["knowledge"], _S["perception"], _S["ride"],
        _S["survival"], _S["swim"],
    },
    "Unchained Monk": {
        _S["acrobatics"], _S["climb"], _S["craft"], _S["escape artist"],
        _S["intimidate"], _S["knowledge"], _S["perception"], _S["perform"],
        _S["profession"], _S["ride"], _S["sense motive"], _S["stealth"],
        _S["swim"],
    },
    "Unchained Rogue": {
        _S["acrobatics"], _S["appraise"], _S["bluff"], _S["climb"],
        _S["craft"], _S["diplomacy"], _S["disable device"], _S["disguise"],
        _S["escape artist"], _S["intimidate"], _S["knowledge"], _S["linguistics"],
        _S["perception"], _S["perform"], _S["profession"], _S["sense motive"],
        _S["sleight of hand"], _S["stealth"], _S["swim"], _S["use magic device"],
    },
    "Unchained Summoner": {
        _S["craft"], _S["fly"], _S["handle animal"], _S["knowledge"],
        _S["linguistics"], _S["profession"], _S["ride"], _S["spellcraft"],
        _S["use magic device"],
    },
    # ── Ultimate Intrigue (2016) ──────────────────────────────────────────
    "Vigilante": {
        _S["acrobatics"], _S["bluff"], _S["climb"], _S["craft"],
        _S["diplomacy"], _S["disable device"], _S["disguise"], _S["escape artist"],
        _S["intimidate"], _S["knowledge"], _S["linguistics"], _S["perception"],
        _S["perform"], _S["profession"], _S["ride"], _S["sense motive"],
        _S["sleight of hand"], _S["spellcraft"], _S["stealth"], _S["swim"],
        _S["use magic device"],
    },
    # ── Wilderness Origins (2017) — Shifter ───────────────────────────────
    "Shifter": {
        _S["acrobatics"], _S["climb"], _S["fly"], _S["handle animal"],
        _S["knowledge"], _S["perception"], _S["ride"], _S["stealth"],
        _S["survival"], _S["swim"],
    },
    # ── Adventurer's Guide (2017) — Omdura ───────────────────────────────
    "Omdura": {
        _S["climb"], _S["craft"], _S["diplomacy"], _S["handle animal"],
        _S["heal"], _S["knowledge"], _S["profession"], _S["ride"],
        _S["sense motive"], _S["spellcraft"], _S["swim"],
    },
    # ── NPC classes (Gamemastery Guide / Core Rulebook) ───────────────────
    "Adept": {
        _S["craft"], _S["heal"], _S["knowledge"], _S["profession"],
        _S["spellcraft"], _S["survival"],
    },
    "Aristocrat": {
        _S["bluff"], _S["diplomacy"], _S["disguise"], _S["handle animal"],
        _S["intimidate"], _S["knowledge"], _S["linguistics"], _S["perception"],
        _S["perform"], _S["profession"], _S["ride"], _S["sense motive"],
        _S["swim"],
    },
    "Commoner": {
        _S["climb"], _S["craft"], _S["fly"], _S["handle animal"],
        _S["perception"], _S["profession"], _S["ride"], _S["swim"],
    },
    # Expert: all skills (player-chosen) — represent with all 26 skills
    "Expert": set(range(1, 27)),
    "Warrior": {
        _S["climb"], _S["craft"], _S["handle animal"], _S["intimidate"],
        _S["profession"], _S["ride"], _S["survival"], _S["swim"],
    },
}



def load_coreforge() -> dict[str, set[int]]:
    """Extract base-class skill sets from CoreForge Archetype Definitions sheet."""
    try:
        from pyxlsb import open_workbook
    except ImportError:
        print("[warn] pyxlsb not installed — skipping CoreForge source", file=sys.stderr)
        return {}

    result: dict[str, set[int]] = {}
    name_fixes = {"Anti-Paladin": "Antipaladin"}

    with open_workbook(str(COREFORGE_PATH)) as wb:
        with wb.get_sheet("Archetype Definitions") as ws:
            rows = list(ws.rows())

    for row in rows[2:]:
        vals = [c.v for c in row]
        base_class = vals[1]
        archetype = vals[2]
        skills_str = vals[14]
        if base_class and archetype == base_class and skills_str:
            db_name = name_fixes.get(base_class, base_class)
            result[db_name] = parse_coreforge_skill_str(str(skills_str))

    print(f"[coreforge] loaded {len(result)} base classes")
    return result


def load_foundry_prestige() -> dict[str, set[int]]:
    """Load prestige class skill sets from Foundry pf-prestige-classes.db."""
    if not FOUNDRY_PRESTIGE.exists():
        print(f"[warn] {FOUNDRY_PRESTIGE} not found — skipping", file=sys.stderr)
        return {}

    result: dict[str, set[int]] = {}
    with open(FOUNDRY_PRESTIGE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = obj.get("name", "")
            cs = obj.get("system", {}).get("classSkills", {})
            if not cs:
                continue
            ids: set[int] = set()
            for abbr, val in cs.items():
                if val:
                    sid = FOUNDRY_ABBR_MAP.get(abbr)
                    if sid:
                        ids.add(sid)
            if ids:
                result[name] = ids

    print(f"[foundry] loaded {len(result)} prestige classes")
    return result


def populate(dry_run: bool = False) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Load DB class name → id mapping
    cur.execute("SELECT id, name FROM classes")
    class_map: dict[str, int] = {r["name"]: r["id"] for r in cur.fetchall()}

    # ── Gather all class→skill_ids from each source ───────────────────── #
    coreforge = load_coreforge()
    foundry = load_foundry_prestige()

    # Merge: coreforge first (authoritative for CRB/APG), then foundry (prestige),
    # then hardcoded (fills everything else).
    merged: dict[str, set[int]] = {}
    for name, ids in coreforge.items():
        merged[name] = ids
    for name, ids in foundry.items():
        if name not in merged:
            merged[name] = ids
        else:
            # Cross-reference: log difference
            diff = ids.symmetric_difference(merged[name])
            if diff:
                print(f"  [xref] '{name}' CoreForge/Foundry differ on skill_ids: {diff}")
    for name, ids in HARDCODED.items():
        if name not in merged:
            merged[name] = ids

    # ── Map class names to DB IDs and insert ──────────────────────────── #
    inserted = 0
    skipped_no_class = 0
    skipped_no_skills = 0

    rows_to_insert: list[tuple[int, int]] = []
    for class_name, skill_ids in merged.items():
        class_id = class_map.get(class_name)
        if class_id is None:
            print(f"  [skip] '{class_name}' not found in classes table")
            skipped_no_class += 1
            continue
        if not skill_ids:
            skipped_no_skills += 1
            continue
        for sid in skill_ids:
            rows_to_insert.append((class_id, sid))

    print(f"\nTotal (class, skill) pairs to insert: {len(rows_to_insert)}")
    print(f"Classes matched:        {len(merged) - skipped_no_class - skipped_no_skills}")
    print(f"Classes not in DB:      {skipped_no_class}")

    if dry_run:
        print("\n[dry-run] No changes written.")
        # Print summary by class
        for class_name, skill_ids in sorted(merged.items()):
            cid = class_map.get(class_name, "?")
            print(f"  {class_name} (id={cid}): {len(skill_ids)} class skills")
        conn.close()
        return

    # Clear existing data first
    cur.execute("DELETE FROM class_skills")
    print(f"\nCleared existing class_skills rows.")

    cur.executemany(
        "INSERT OR IGNORE INTO class_skills (class_id, skill_id) VALUES (?, ?)",
        rows_to_insert,
    )
    inserted = cur.rowcount
    conn.commit()

    print(f"Inserted {cur.execute('SELECT COUNT(*) FROM class_skills').fetchone()[0]} rows into class_skills.")

    # Verify a few classes
    print("\nVerification samples:")
    for sample_class in ["Fighter", "Rogue", "Wizard", "Arcanist", "Kineticist", "Vigilante"]:
        cid = class_map.get(sample_class)
        if cid:
            cur.execute("""
                SELECT s.name FROM class_skills cs
                JOIN skills s ON s.id = cs.skill_id
                WHERE cs.class_id = ?
                ORDER BY s.name
            """, (cid,))
            names = [r[0] for r in cur.fetchall()]
            print(f"  {sample_class}: {', '.join(names)}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be inserted without modifying the DB")
    args = parser.parse_args()
    populate(dry_run=args.dry_run)
