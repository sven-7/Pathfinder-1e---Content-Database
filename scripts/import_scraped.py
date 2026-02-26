#!/usr/bin/env python3
"""
import_scraped.py — Import scraped d20pfsrd data into the SQLite database.

Reads parsed JSON files from data/d20pfsrd/parsed/ and inserts records
into the existing pf1e.db schema. Designed to run AFTER import_psrd.py
to fill gaps, or standalone to build the database entirely from scrapes.

Usage:
  python scripts/import_scraped.py                     # Import all parsed data
  python scripts/import_scraped.py --type spells       # Import only spells
  python scripts/import_scraped.py --replace            # Drop existing + reimport
  python scripts/import_scraped.py --merge              # Merge (skip duplicates, default)
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSED_DIR = ROOT / "data" / "d20pfsrd" / "parsed"
DB_PATH = ROOT / "db" / "pf1e.db"
SCHEMA_PATH = ROOT / "schema" / "pf1e_schema.sql"


def load_parsed(content_type: str) -> list[dict]:
    """Load parsed JSON for a content type."""
    path = PARSED_DIR / f"{content_type}.json"
    if not path.exists():
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def ensure_source(conn, source_name: str = "d20pfsrd.com") -> int:
    """Get or create a source record for d20pfsrd scraped data."""
    cursor = conn.execute("SELECT id FROM sources WHERE name = ?", (source_name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    conn.execute("""
        INSERT INTO sources (name, abbreviation, publisher, import_date)
        VALUES (?, ?, ?, datetime('now'))
    """, (source_name, "d20pfsrd", "Paizo (via d20pfsrd.com)"))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def guess_book_source(url: str, source_text: str) -> str:
    """Try to determine the original book from URL or source attribution.

    Returns a human-readable source name like "Advanced Class Guide".
    """
    # Check source text first
    if source_text:
        return source_text

    # Infer from URL patterns
    url_lower = url.lower()
    if '/hybrid-classes/' in url_lower:
        return "Advanced Class Guide"
    elif '/occult-classes/' in url_lower:
        return "Occult Adventures"
    elif '/unchained-classes/' in url_lower:
        return "Pathfinder Unchained"
    elif '/core-classes/' in url_lower:
        return "Core Rulebook"
    elif '/base-classes/' in url_lower:
        # Could be APG, UM, UC, etc. — can't tell from URL alone
        return ""

    return ""


def import_spells(conn, spells: list[dict], source_id: int, merge: bool = True) -> dict:
    """Import spell records into the database.

    Returns: {"inserted": N, "skipped": N, "updated": N}
    """
    stats = {"inserted": 0, "skipped": 0, "updated": 0}

    for spell in spells:
        name = spell.get("name", "").strip()
        if not name:
            continue

        # Check for existing record
        existing = conn.execute(
            "SELECT id FROM spells WHERE name = ?", (name,)
        ).fetchone()

        if existing and merge:
            # In merge mode, update if new data has more info
            spell_id = existing[0]
            # Check if existing record has class levels
            existing_levels = conn.execute(
                "SELECT COUNT(*) FROM spell_class_levels WHERE spell_id = ?",
                (spell_id,)
            ).fetchone()[0]

            new_levels = spell.get("class_levels", [])

            # Update class levels if we have more than existing
            if len(new_levels) > existing_levels:
                conn.execute("DELETE FROM spell_class_levels WHERE spell_id = ?", (spell_id,))
                for cl in new_levels:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO spell_class_levels (spell_id, class_name, level) VALUES (?, ?, ?)",
                            (spell_id, cl["class"].lower(), int(cl["level"]))
                        )
                    except (ValueError, TypeError, KeyError):
                        pass
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
            continue

        if existing and not merge:
            stats["skipped"] += 1
            continue

        # Insert new spell
        conn.execute("""
            INSERT OR IGNORE INTO spells
            (name, source_id, school, subschool, descriptors,
             casting_time, components, range, area, effect, target,
             duration, saving_throw, spell_resistance, description, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, source_id,
            spell.get("school", ""),
            spell.get("subschool", ""),
            spell.get("descriptors", ""),
            spell.get("casting_time", ""),
            spell.get("components", ""),
            spell.get("range", ""),
            spell.get("area", ""),
            spell.get("effect", ""),
            spell.get("target", ""),
            spell.get("duration", ""),
            spell.get("saving_throw", ""),
            spell.get("spell_resistance", ""),
            spell.get("description", ""),
            spell.get("url", ""),
        ))

        # Get spell ID
        spell_id_row = conn.execute(
            "SELECT id FROM spells WHERE name = ? AND source_id = ?", (name, source_id)
        ).fetchone()

        if spell_id_row:
            spell_id = spell_id_row[0]
            for cl in spell.get("class_levels", []):
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO spell_class_levels (spell_id, class_name, level) VALUES (?, ?, ?)",
                        (spell_id, cl["class"].lower(), int(cl["level"]))
                    )
                except (ValueError, TypeError, KeyError):
                    pass

        stats["inserted"] += 1

    conn.commit()
    return stats


def import_feats(conn, feats: list[dict], source_id: int, merge: bool = True) -> dict:
    """Import feat records into the database."""
    stats = {"inserted": 0, "skipped": 0}

    for feat in feats:
        name = feat.get("name", "").strip()
        if not name:
            continue

        existing = conn.execute("SELECT id FROM feats WHERE name = ?", (name,)).fetchone()
        if existing:
            stats["skipped"] += 1
            continue

        conn.execute("""
            INSERT OR IGNORE INTO feats
            (name, source_id, feat_type, prerequisites, prerequisite_feats,
             benefit, normal, special, description, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, source_id,
            feat.get("feat_type", "general"),
            feat.get("prerequisites", ""),
            feat.get("prerequisite_feats", ""),
            feat.get("benefit", ""),
            feat.get("normal", ""),
            feat.get("special", ""),
            feat.get("description", ""),
            feat.get("url", ""),
        ))
        stats["inserted"] += 1

    conn.commit()
    return stats


def import_classes(conn, classes: list[dict], source_id: int, merge: bool = True) -> dict:
    """Import class records with features and progression."""
    stats = {"inserted": 0, "skipped": 0, "features": 0, "progression": 0}

    for cls in classes:
        name = cls.get("name", "").strip()
        if not name:
            continue

        existing = conn.execute("SELECT id FROM classes WHERE name = ?", (name,)).fetchone()

        if existing and merge:
            class_id = existing[0]
            # Update metadata if we have better data
            conn.execute("""
                UPDATE classes SET
                    class_type = COALESCE(NULLIF(?, ''), class_type),
                    hit_die = COALESCE(NULLIF(?, ''), hit_die),
                    skill_ranks_per_level = COALESCE(?, skill_ranks_per_level),
                    bab_progression = COALESCE(NULLIF(?, ''), bab_progression),
                    fort_progression = COALESCE(NULLIF(?, ''), fort_progression),
                    ref_progression = COALESCE(NULLIF(?, ''), ref_progression),
                    will_progression = COALESCE(NULLIF(?, ''), will_progression),
                    spellcasting_type = COALESCE(NULLIF(?, ''), spellcasting_type),
                    spellcasting_style = COALESCE(NULLIF(?, ''), spellcasting_style),
                    max_spell_level = COALESCE(?, max_spell_level),
                    url = COALESCE(NULLIF(?, ''), url)
                WHERE id = ?
            """, (
                cls.get("class_type", ""),
                cls.get("hit_die", ""),
                cls.get("skill_ranks_per_level"),
                cls.get("bab_progression", ""),
                cls.get("fort_progression", ""),
                cls.get("ref_progression", ""),
                cls.get("will_progression", ""),
                cls.get("spellcasting_type"),
                cls.get("spellcasting_style"),
                cls.get("max_spell_level"),
                cls.get("url", ""),
                class_id,
            ))
        elif existing:
            stats["skipped"] += 1
            continue
        else:
            # Insert new class
            conn.execute("""
                INSERT INTO classes
                (name, source_id, class_type, hit_die, skill_ranks_per_level,
                 bab_progression, fort_progression, ref_progression, will_progression,
                 spellcasting_type, spellcasting_style, max_spell_level,
                 alignment_restriction, description, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, source_id,
                cls.get("class_type", "base"),
                cls.get("hit_die", ""),
                cls.get("skill_ranks_per_level"),
                cls.get("bab_progression", ""),
                cls.get("fort_progression", ""),
                cls.get("ref_progression", ""),
                cls.get("will_progression", ""),
                cls.get("spellcasting_type"),
                cls.get("spellcasting_style"),
                cls.get("max_spell_level"),
                cls.get("alignment_restriction", ""),
                cls.get("description", ""),
                cls.get("url", ""),
            ))
            stats["inserted"] += 1

        # Get class ID
        class_row = conn.execute("SELECT id FROM classes WHERE name = ?", (name,)).fetchone()
        if not class_row:
            continue
        class_id = class_row[0]

        # Import class features
        for feature in cls.get("class_features", []):
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO class_features
                    (class_id, name, level, feature_type, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    class_id,
                    feature.get("name", ""),
                    feature.get("level", 1),
                    feature.get("feature_type", "class_feature"),
                    feature.get("description", ""),
                ))
                stats["features"] += 1
            except sqlite3.IntegrityError:
                pass

        # Import progression table
        for row in cls.get("progression", []):
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO class_progression
                    (class_id, level, bab, fort_save, ref_save, will_save, special)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    class_id,
                    row.get("level", 1),
                    row.get("bab", 0),
                    row.get("fort_save", 0),
                    row.get("ref_save", 0),
                    row.get("will_save", 0),
                    row.get("special", ""),
                ))
                stats["progression"] += 1
            except sqlite3.IntegrityError:
                pass

        # Import class skills
        for skill_name in cls.get("class_skills", []):
            skill_row = conn.execute(
                "SELECT id FROM skills WHERE name = ?", (skill_name,)
            ).fetchone()
            if skill_row:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO class_skills (class_id, skill_id) VALUES (?, ?)",
                        (class_id, skill_row[0])
                    )
                except sqlite3.IntegrityError:
                    pass

    conn.commit()
    return stats


def import_races(conn, races: list[dict], source_id: int, merge: bool = True) -> dict:
    """Import race records with racial traits."""
    stats = {"inserted": 0, "skipped": 0, "traits": 0}

    for race in races:
        name = race.get("name", "").strip()
        if not name:
            continue

        existing = conn.execute("SELECT id FROM races WHERE name = ?", (name,)).fetchone()

        if existing and merge:
            race_id = existing[0]
            # Update with new data
            conn.execute("""
                UPDATE races SET
                    race_type = COALESCE(NULLIF(?, 'other'), race_type),
                    size = COALESCE(NULLIF(?, 'Medium'), size),
                    base_speed = COALESCE(?, base_speed),
                    ability_modifiers = COALESCE(NULLIF(?, ''), ability_modifiers),
                    type = COALESCE(NULLIF(?, 'Humanoid'), type),
                    languages = COALESCE(NULLIF(?, ''), languages),
                    url = COALESCE(NULLIF(?, ''), url)
                WHERE id = ?
            """, (
                race.get("race_type", "other"),
                race.get("size", "Medium"),
                race.get("base_speed"),
                race.get("ability_modifiers", ""),
                race.get("type", "Humanoid"),
                race.get("languages", ""),
                race.get("url", ""),
                race_id,
            ))
        elif existing:
            stats["skipped"] += 1
            continue
        else:
            conn.execute("""
                INSERT OR IGNORE INTO races
                (name, source_id, race_type, size, base_speed,
                 ability_modifiers, type, subtypes, languages,
                 bonus_languages, description, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, source_id,
                race.get("race_type", "other"),
                race.get("size", "Medium"),
                race.get("base_speed", 30),
                race.get("ability_modifiers", ""),
                race.get("type", "Humanoid"),
                race.get("subtypes", ""),
                race.get("languages", ""),
                race.get("bonus_languages", ""),
                race.get("description", ""),
                race.get("url", ""),
            ))
            stats["inserted"] += 1

        # Get race ID
        race_row = conn.execute("SELECT id FROM races WHERE name = ?", (name,)).fetchone()
        if not race_row:
            continue
        race_id = race_row[0]

        # Import racial traits
        for trait in race.get("racial_traits", []):
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO racial_traits
                    (race_id, name, trait_type, description, replaces)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    race_id,
                    trait.get("name", ""),
                    trait.get("trait_type", ""),
                    trait.get("description", ""),
                    trait.get("replaces", ""),
                ))
                stats["traits"] += 1
            except sqlite3.IntegrityError:
                pass

    conn.commit()
    return stats


def rebuild_search_index(conn):
    """Rebuild the FTS5 search index after import."""
    print("  Rebuilding search index...")
    conn.execute("DELETE FROM search_index")

    index_queries = [
        ("spell", "spells", "s"),
        ("feat", "feats", "f"),
        ("class", "classes", "c"),
        ("race", "races", "r"),
        ("monster", "monsters", "m"),
        ("equipment", "equipment", "e"),
        ("magic_item", "magic_items", "mi"),
    ]

    for content_type, table, alias in index_queries:
        try:
            conn.execute(f"""
                INSERT INTO search_index (name, content_type, description, source, content_id)
                SELECT {alias}.name, '{content_type}', {alias}.description, src.name, {alias}.id
                FROM {table} {alias}
                LEFT JOIN sources src ON {alias}.source_id = src.id
            """)
        except sqlite3.OperationalError:
            pass

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM search_index").fetchone()[0]
    print(f"  ✓ Search index: {count:,} entries")


def main():
    parser = argparse.ArgumentParser(description="Import scraped d20pfsrd data into SQLite")
    parser.add_argument('--type', nargs='+', dest='content_types',
                       help='Content types to import (spells, feats, classes, races)')
    parser.add_argument('--replace', action='store_true',
                       help='Delete existing scraped records before import')
    parser.add_argument('--merge', action='store_true', default=True,
                       help='Merge with existing data (skip duplicates, default)')
    parser.add_argument('--db', type=str, default=str(DB_PATH),
                       help=f'Database path (default: {DB_PATH})')
    args = parser.parse_args()

    db_path = Path(args.db)

    if not db_path.exists():
        print(f"✗ Database not found at {db_path}")
        print(f"  Run 'python scripts/import_psrd.py' first to create the base database,")
        print(f"  or create an empty one with: sqlite3 {db_path} < schema/pf1e_schema.sql")
        sys.exit(1)

    print("╔" + "═" * 58 + "╗")
    print("║   Import Scraped d20pfsrd Data                           ║")
    print("╚" + "═" * 58 + "╝")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    source_id = ensure_source(conn)
    merge = not args.replace

    # Determine which types to import
    all_types = ['spells', 'feats', 'classes', 'races']
    types_to_import = args.content_types or all_types

    results = {}

    for content_type in types_to_import:
        data = load_parsed(content_type)
        if not data:
            print(f"\n[{content_type}] No parsed data found — skipping")
            continue

        print(f"\n[{content_type.upper()}] Importing {len(data)} records (merge={merge})...")

        if content_type == "spells":
            stats = import_spells(conn, data, source_id, merge)
        elif content_type == "feats":
            stats = import_feats(conn, data, source_id, merge)
        elif content_type == "classes":
            stats = import_classes(conn, data, source_id, merge)
        elif content_type == "races":
            stats = import_races(conn, data, source_id, merge)
        else:
            print(f"  ⚠ No importer for '{content_type}'")
            continue

        results[content_type] = stats
        parts = [f"{v} {k}" for k, v in stats.items() if v > 0]
        print(f"  → {', '.join(parts)}")

    # Update source record count
    total_records = conn.execute("""
        SELECT
            (SELECT COUNT(*) FROM spells WHERE source_id = ?) +
            (SELECT COUNT(*) FROM feats WHERE source_id = ?) +
            (SELECT COUNT(*) FROM classes WHERE source_id = ?) +
            (SELECT COUNT(*) FROM races WHERE source_id = ?)
    """, (source_id, source_id, source_id, source_id)).fetchone()[0]

    conn.execute(
        "UPDATE sources SET record_count = ? WHERE id = ?",
        (total_records, source_id)
    )
    conn.commit()

    # Rebuild search index
    print(f"\n--- Post-Processing ---")
    rebuild_search_index(conn)

    # Summary
    print(f"\n{'=' * 60}")
    print("Import Complete!")
    print(f"{'=' * 60}")

    for table in ['sources', 'classes', 'class_features', 'class_progression',
                  'races', 'racial_traits', 'feats', 'skills',
                  'spells', 'spell_class_levels']:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:25s}: {count:,}")

    db_size = db_path.stat().st_size / (1024 * 1024)
    print(f"\n  Database: {db_path} ({db_size:.1f} MB)")

    conn.close()


if __name__ == "__main__":
    main()
