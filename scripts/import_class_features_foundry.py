#!/usr/bin/env python3
"""
Import class talent-pool options from Foundry NDJSON into class_features table.

Source: data/foundry/packs/pf-class-abilities.db (4,727 records)
Target: db/pf1e.db  class_features table

These records are selectable talent pool options:
  Rage Powers, Discoveries, Investigator Talents, Arcanist Exploits,
  Ki Powers, Bloodlines, Mysteries, Domains, Deeds, etc.

Run:  python scripts/import_class_features_foundry.py [--all]

By default, only inserts for classes that currently have 0 class_features rows.
Pass --all to insert for every class found in the Foundry data.
"""

from __future__ import annotations
import argparse
import html as html_module
import json
import pathlib
import re
import sqlite3

ROOT = pathlib.Path(__file__).parent.parent
FOUNDRY_PATH = ROOT / "data" / "foundry" / "packs" / "pf-class-abilities.db"
DB_PATH = ROOT / "db" / "pf1e.db"

# Foundry class name → DB class name
CLASS_NAME_MAP: dict[str, str] = {
    # Unchained variants
    "Barbarian (Unchained)": "Unchained Barbarian",
    "Monk (Unchained)": "Unchained Monk",
    "Rogue (Unchained)": "Unchained Rogue",
    "Summoner (Unchained)": "Unchained Summoner",
    # Direct matches (Foundry name == DB name)
    "Alchemist": "Alchemist",
    "Arcanist": "Arcanist",
    "Barbarian": "Barbarian",
    "Bard": "Bard",
    "Bloodrager": "Bloodrager",
    "Brawler": "Brawler",
    "Cavalier": "Cavalier",
    "Cleric": "Cleric",
    "Druid": "Druid",
    "Fighter": "Fighter",
    "Gunslinger": "Gunslinger",
    "Hunter": "Hunter",
    "Inquisitor": "Inquisitor",
    "Investigator": "Investigator",
    "Kineticist": "Kineticist",
    "Magus": "Magus",
    "Medium": "Medium",
    "Mesmerist": "Mesmerist",
    "Monk": "Monk",
    "Ninja": "Ninja",
    "Occultist": "Occultist",
    "Oracle": "Oracle",
    "Paladin": "Paladin",
    "Psychic": "Psychic",
    "Ranger": "Ranger",
    "Rogue": "Rogue",
    "Samurai": "Samurai",
    "Shaman": "Shaman",
    "Shifter": "Shifter",
    "Skald": "Skald",
    "Slayer": "Slayer",
    "Sorcerer": "Sorcerer",
    "Spiritualist": "Spiritualist",
    "Swashbuckler": "Swashbuckler",
    "Vigilante": "Vigilante",
    "Warpriest": "Warpriest",
    "Witch": "Witch",
    "Wizard": "Wizard",
}


def strip_html(html_str: str) -> str:
    """Strip HTML tags and decode entities, collapsing whitespace."""
    text = re.sub(r"<[^>]+>", " ", html_str)
    text = html_module.unescape(text)
    return " ".join(text.split())


def extract_level_from_feature_type(feature_type: str) -> int | None:
    """
    Extract level from feature type name.
    e.g. 'Swashbuckler 3rd Level Deed' → 3
         'Paladin 6th-Level Mercy'      → 6
    """
    m = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", feature_type, re.IGNORECASE)
    return int(m.group(1)) if m else None


def extract_level_from_description(desc_html: str) -> int | None:
    """
    Extract level from description text.
    e.g. 'At 3rd level, ...' → 3
         'At the 5th-level ...' → 5
    """
    desc = strip_html(desc_html)
    m = re.search(r"\bAt (?:the )?(\d+)(?:st|nd|rd|th)[- ]level", desc, re.IGNORECASE)
    return int(m.group(1)) if m else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Insert for all classes, not just those with 0 existing features",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build class name → id map
    cur.execute("SELECT id, name FROM classes")
    class_id_map: dict[str, int] = {row["name"]: row["id"] for row in cur.fetchall()}

    # Classes currently with 0 class_features rows
    cur.execute("SELECT class_id FROM class_features GROUP BY class_id HAVING COUNT(*) > 0")
    classes_with_features: set[int] = {row["class_id"] for row in cur.fetchall()}

    # Build existing (class_id, name) set to avoid duplicates
    cur.execute("SELECT class_id, name FROM class_features")
    existing: set[tuple[int, str]] = {(row["class_id"], row["name"]) for row in cur.fetchall()}

    # Read Foundry NDJSON
    if not FOUNDRY_PATH.exists():
        print(f"ERROR: Foundry data not found at {FOUNDRY_PATH}")
        return

    records: list[dict] = []
    with open(FOUNDRY_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    print(f"Loaded {len(records):,} Foundry records")
    print(f"Classes already with features: {len(classes_with_features)}")
    print()

    inserted = 0
    skipped_no_class = 0
    skipped_existing = 0
    skipped_already_has_features = 0

    for rec in records:
        sys_data = rec.get("system", {})

        # --- Class name ---
        classes_list = sys_data.get("associations", {}).get("classes", [])
        if not classes_list:
            skipped_no_class += 1
            continue

        foundry_class = classes_list[0][0]
        db_class = CLASS_NAME_MAP.get(foundry_class)
        if not db_class:
            skipped_no_class += 1
            continue

        class_id = class_id_map.get(db_class)
        if not class_id:
            skipped_no_class += 1
            continue

        # --- Skip if class already has features (unless --all) ---
        if not args.all and class_id in classes_with_features:
            skipped_already_has_features += 1
            continue

        # --- Feature name ---
        name = rec.get("name", "").strip()
        if not name:
            continue

        # --- Deduplicate ---
        if (class_id, name) in existing:
            skipped_existing += 1
            continue

        # --- Feature type ---
        tags = sys_data.get("tags", [])
        feature_type: str | None = None
        if tags and len(tags[0]) > 1 and tags[0][1]:
            feature_type = tags[0][1][0]

        # --- Level ---
        level: int | None = None
        if feature_type:
            level = extract_level_from_feature_type(feature_type)
        if level is None:
            desc_html = sys_data.get("description", {}).get("value", "")
            level = extract_level_from_description(desc_html)
        if level is None:
            level = 1  # default: available from level 1 (talent pool)

        # --- Description (stripped HTML) ---
        desc_html = sys_data.get("description", {}).get("value", "") or ""
        description = strip_html(desc_html) or None
        # Truncate very long descriptions
        if description and len(description) > 2000:
            description = description[:2000] + "…"

        # --- Insert ---
        cur.execute(
            """
            INSERT INTO class_features (class_id, name, level, feature_type, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (class_id, name, level, feature_type, description),
        )
        existing.add((class_id, name))
        inserted += 1

    conn.commit()
    conn.close()

    # --- Report ---
    print(f"Inserted:                     {inserted:,}")
    print(f"Skipped (duplicate):          {skipped_existing:,}")
    print(f"Skipped (class had features): {skipped_already_has_features:,}")
    print(f"Skipped (unknown class):      {skipped_no_class:,}")
    print()

    # Show results by class
    conn2 = sqlite3.connect(DB_PATH)
    conn2.row_factory = sqlite3.Row
    cur2 = conn2.cursor()
    cur2.execute(
        """
        SELECT c.name, COUNT(cf.id) as cnt
        FROM classes c
        LEFT JOIN class_features cf ON cf.class_id = c.id
        WHERE c.name NOT IN ('Aristocrat','Commoner','Expert','Warrior','NPC')
        GROUP BY c.id
        HAVING cnt > 0
        ORDER BY cnt DESC
        """
    )
    print("=== class_features counts (post-import) ===")
    for row in cur2.fetchall():
        print(f"  {row['cnt']:4d}  {row['name']}")
    conn2.close()


if __name__ == "__main__":
    main()
