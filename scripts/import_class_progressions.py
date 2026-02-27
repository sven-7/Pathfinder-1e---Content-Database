#!/usr/bin/env python3
"""Parse PSRD class JSON files and populate the class_progression table.

Run once after the scraper has imported classes:
    python scripts/import_class_progressions.py
"""

import json
import os
import glob
import sqlite3
import sys

# Allow importing from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rules_engine.progression import parse_class_progression_html, LevelRow

PSRD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "psrd")
DB_PATH  = os.path.join(os.path.dirname(__file__), "..", "db", "pf1e.db")


def _find_progression_table(obj: dict | list, results: list[str]) -> None:
    """Recursively find all HTML sections containing 'Base Attack Bonus' tables."""
    if isinstance(obj, dict):
        body = obj.get("body", "")
        if isinstance(body, str) and "Base Attack Bonus" in body and "<table" in body.lower():
            results.append(body)
        for v in obj.values():
            _find_progression_table(v, results)
    elif isinstance(obj, list):
        for item in obj:
            _find_progression_table(item, results)


def process_file(path: str) -> tuple[str, list[LevelRow]]:
    """Extract (class_name, [LevelRow]) from a PSRD class JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    class_name = data.get("name", "")

    bodies: list[str] = []
    _find_progression_table(data, bodies)

    if not bodies:
        return class_name, []

    # Use the first progression table found (should be the class table)
    rows = parse_class_progression_html(bodies[0])
    return class_name, rows


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    pattern = os.path.join(PSRD_DIR, "**", "class", "**", "*.json")
    json_files = sorted(glob.glob(pattern, recursive=True))

    print(f"Found {len(json_files)} class JSON files")

    inserted_total = 0
    skipped_total  = 0
    errors         = []

    for path in json_files:
        try:
            class_name, rows = process_file(path)
        except Exception as e:
            errors.append(f"  ERROR reading {path}: {e}")
            continue

        if not class_name:
            continue

        # Resolve class_id from DB
        row = cur.execute(
            "SELECT id FROM classes WHERE name = ?", (class_name,)
        ).fetchone()
        if row is None:
            # Try case-insensitive
            row = cur.execute(
                "SELECT id FROM classes WHERE lower(name) = lower(?)", (class_name,)
            ).fetchone()
        if row is None:
            print(f"  SKIP '{class_name}' — not in classes table")
            skipped_total += 1
            continue

        class_id = row["id"]

        if not rows:
            print(f"  SKIP '{class_name}' — no progression table found in {os.path.basename(path)}")
            skipped_total += 1
            continue

        inserted = 0
        for lr in rows:
            spells_json = json.dumps(lr.spells_per_day) if lr.spells_per_day else None
            try:
                cur.execute(
                    """INSERT OR REPLACE INTO class_progression
                       (class_id, level, bab, fort_save, ref_save, will_save, special, spells_per_day)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (class_id, lr.level, lr.bab, lr.fort_save, lr.ref_save,
                     lr.will_save, lr.special or None, spells_json),
                )
                inserted += 1
            except sqlite3.Error as e:
                errors.append(f"  DB error for {class_name} level {lr.level}: {e}")

        print(f"  {class_name}: {inserted} levels inserted")
        inserted_total += inserted

    conn.commit()
    conn.close()

    print(f"\nDone. Inserted {inserted_total} rows, skipped {skipped_total} classes.")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
