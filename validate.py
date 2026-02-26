#!/usr/bin/env python3
"""
validate.py — Run data integrity and completeness checks.
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "pf1e.db"

# Expected minimums for Core Rulebook content
EXPECTED_MINIMUMS = {
    'classes': 15,        # 11 core + NPC classes + prestige
    'spells': 400,        # CRB has ~500 spells
    'feats': 100,         # CRB has ~130 feats
    'skills': 25,         # 35 skills in PF1e
    'races': 7,           # 7 core races
}

CORE_CLASSES = [
    'Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter',
    'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Wizard'
]

CORE_RACES = ['Dwarf', 'Elf', 'Gnome', 'Half-Elf', 'Half-Orc', 'Halfling', 'Human']


def check(label, passed, detail=""):
    status = "✓" if passed else "✗"
    msg = f"  {status} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return passed


def main():
    if not DB_PATH.exists():
        print(f"✗ Database not found. Run import first.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    all_passed = True

    print("=" * 60)
    print("Data Validation")
    print("=" * 60)

    # Minimum counts
    print("\n--- Minimum Count Checks ---")
    for table, minimum in EXPECTED_MINIMUMS.items():
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        passed = count >= minimum
        all_passed &= check(f"{table}: {count} records (min: {minimum})", passed)

    # Core classes present
    print("\n--- Core Classes ---")
    for cls in CORE_CLASSES:
        row = conn.execute("SELECT id FROM classes WHERE name = ?", (cls,)).fetchone()
        passed = row is not None
        all_passed &= check(f"Class: {cls}", passed)

    # Core races present
    print("\n--- Core Races ---")
    for race in CORE_RACES:
        row = conn.execute("SELECT id FROM races WHERE name = ?", (race,)).fetchone()
        passed = row is not None
        all_passed &= check(f"Race: {race}", passed)

    # Spell level associations
    print("\n--- Spell Data Quality ---")
    total_spells = conn.execute("SELECT COUNT(*) FROM spells").fetchone()[0]
    spells_with_levels = conn.execute(
        "SELECT COUNT(DISTINCT spell_id) FROM spell_class_levels"
    ).fetchone()[0]
    pct = (spells_with_levels / total_spells * 100) if total_spells > 0 else 0
    all_passed &= check(
        f"Spells with class/level data: {spells_with_levels}/{total_spells} ({pct:.0f}%)",
        pct > 50
    )

    # Orphan checks
    print("\n--- Referential Integrity ---")
    orphan_feats = conn.execute(
        "SELECT COUNT(*) FROM feats WHERE source_id NOT IN (SELECT id FROM sources)"
    ).fetchone()[0]
    all_passed &= check(f"Orphan feats: {orphan_feats}", orphan_feats == 0)

    orphan_spells = conn.execute(
        "SELECT COUNT(*) FROM spells WHERE source_id NOT IN (SELECT id FROM sources)"
    ).fetchone()[0]
    all_passed &= check(f"Orphan spells: {orphan_spells}", orphan_spells == 0)

    # Search index
    print("\n--- Search Index ---")
    search_count = conn.execute("SELECT COUNT(*) FROM search_index").fetchone()[0]
    all_passed &= check(f"Search index entries: {search_count}", search_count > 0)

    print(f"\n{'=' * 60}")
    if all_passed:
        print("✓ All validation checks passed!")
    else:
        print("⚠ Some checks failed. Review import process.")
    print(f"{'=' * 60}")

    conn.close()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
