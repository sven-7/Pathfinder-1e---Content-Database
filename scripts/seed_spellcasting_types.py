#!/usr/bin/env python3
"""
Seed spellcasting_type and spellcasting_style for core spellcasting classes
that currently have NULL in those columns.

Classes already populated (ACG/OA from earlier imports) are left alone.

Run:  python scripts/seed_spellcasting_types.py
"""

import pathlib
import sqlite3

ROOT    = pathlib.Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "pf1e.db"

# (spellcasting_type, spellcasting_style)
SPELLCASTING: dict[str, tuple[str, str]] = {
    # Arcane prepared
    "Wizard":    ("arcane",     "prepared"),
    "Witch":     ("arcane",     "prepared"),
    "Magus":     ("arcane",     "prepared"),
    # Arcane spontaneous
    "Sorcerer":  ("arcane",     "spontaneous"),
    "Bard":      ("arcane",     "spontaneous"),
    "Summoner":  ("arcane",     "spontaneous"),
    # Divine prepared
    "Cleric":    ("divine",     "prepared"),
    "Druid":     ("divine",     "prepared"),
    "Paladin":   ("divine",     "prepared"),
    "Ranger":    ("divine",     "prepared"),
    "Inquisitor":("divine",     "prepared"),
    # Divine spontaneous
    "Oracle":    ("divine",     "spontaneous"),
    # Alchemical prepared
    "Alchemist": ("alchemical", "prepared"),
}


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    updated = 0
    for name, (sc_type, sc_style) in sorted(SPELLCASTING.items()):
        cur.execute(
            "SELECT id, spellcasting_type, spellcasting_style FROM classes WHERE name = ?",
            (name,),
        )
        row = cur.fetchone()
        if not row:
            print(f"  [skip] '{name}' not in DB")
            continue
        if row["spellcasting_type"] is not None:
            print(f"  [skip] '{name}' already has type={row['spellcasting_type']}")
            continue
        cur.execute(
            "UPDATE classes SET spellcasting_type = ?, spellcasting_style = ? WHERE id = ?",
            (sc_type, sc_style, row["id"]),
        )
        print(f"  {name}: {sc_type} / {sc_style}")
        updated += 1

    conn.commit()
    conn.close()
    print(f"\nUpdated {updated} classes.")

    # Verify
    conn2 = sqlite3.connect(DB_PATH)
    conn2.row_factory = sqlite3.Row
    cur2 = conn2.cursor()
    cur2.execute(
        "SELECT name, spellcasting_type, spellcasting_style FROM classes "
        "WHERE spellcasting_type IS NOT NULL ORDER BY spellcasting_type, spellcasting_style, name"
    )
    print("\nAll spellcasting classes in DB:")
    for r in cur2.fetchall():
        print(f"  {r['spellcasting_type']:12s}  {r['spellcasting_style']:12s}  {r['name']}")
    conn2.close()


if __name__ == "__main__":
    main()
