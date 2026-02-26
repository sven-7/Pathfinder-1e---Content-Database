#!/usr/bin/env python3
"""
query_test.py — Run sample queries against the database to verify it works.
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "pf1e.db"


def run_query(conn, label, sql, params=None):
    """Run a query and display results."""
    try:
        cursor = conn.execute(sql, params or ())
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return rows, columns
    except sqlite3.Error as e:
        print(f"  ✗ {label}: {e}")
        return None, None


def main():
    if not DB_PATH.exists():
        print(f"✗ Database not found at {DB_PATH}")
        print(f"  Run 'python scripts/import_psrd.py' first.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))

    print("=" * 60)
    print("Pathfinder 1e Database — Verification Queries")
    print("=" * 60)

    # --- Table counts ---
    print("\n--- Record Counts ---")
    tables = ['sources', 'classes', 'class_features', 'races', 'feats', 'skills',
              'spells', 'spell_class_levels', 'equipment', 'magic_items', 'monsters']
    for table in tables:
        rows, _ = run_query(conn, table, f"SELECT COUNT(*) FROM {table}")
        if rows:
            print(f"  {table:25s}: {rows[0][0]:,}")

    # --- Sources ---
    print("\n--- Imported Sources ---")
    rows, _ = run_query(conn, "sources",
        "SELECT abbreviation, name, record_count FROM sources ORDER BY record_count DESC")
    if rows:
        for abbrev, name, count in rows:
            print(f"  [{abbrev:5s}] {name:35s} {count:,} records")

    # --- Sample Classes ---
    print("\n--- Sample Classes ---")
    rows, _ = run_query(conn, "classes",
        "SELECT c.name, c.class_type, s.abbreviation FROM classes c LEFT JOIN sources s ON c.source_id = s.id ORDER BY c.name LIMIT 15")
    if rows:
        for name, ctype, src in rows:
            print(f"  {name:25s} [{ctype or '?':10s}] ({src or '?'})")

    # --- Sample Spells ---
    print("\n--- Sample Spells (Core) ---")
    rows, _ = run_query(conn, "spells", """
        SELECT s.name, s.school, GROUP_CONCAT(scl.class_name || ' ' || scl.level, ', ') as levels
        FROM spells s
        LEFT JOIN spell_class_levels scl ON s.id = scl.spell_id
        WHERE s.name IN ('Fireball', 'Cure Light Wounds', 'Magic Missile', 'Haste', 'Shield')
        GROUP BY s.id
    """)
    if rows:
        for name, school, levels in rows:
            print(f"  {name:25s} [{school or '?':15s}] {levels or 'no levels'}")

    # --- Spells by class ---
    print("\n--- Spell Count by Class (top 10) ---")
    rows, _ = run_query(conn, "spell_classes", """
        SELECT class_name, COUNT(*) as cnt
        FROM spell_class_levels
        GROUP BY class_name
        ORDER BY cnt DESC
        LIMIT 10
    """)
    if rows:
        for class_name, cnt in rows:
            print(f"  {class_name:20s}: {cnt:,} spells")

    # --- Search test ---
    print("\n--- Full-Text Search Test ---")
    rows, _ = run_query(conn, "search",
        "SELECT name, content_type, source FROM search_index WHERE search_index MATCH ? LIMIT 5",
        ("fireball",))
    if rows:
        for name, ctype, source in rows:
            print(f"  [{ctype:8s}] {name:30s} ({source or '?'})")
    else:
        print("  (No search results — index may be empty)")

    # --- Monster CR distribution ---
    print("\n--- Monster CR Distribution ---")
    rows, _ = run_query(conn, "monsters", """
        SELECT
            CASE
                WHEN cr_numeric < 1 THEN '< 1'
                WHEN cr_numeric BETWEEN 1 AND 5 THEN '1-5'
                WHEN cr_numeric BETWEEN 6 AND 10 THEN '6-10'
                WHEN cr_numeric BETWEEN 11 AND 15 THEN '11-15'
                WHEN cr_numeric BETWEEN 16 AND 20 THEN '16-20'
                ELSE '20+'
            END as cr_range,
            COUNT(*) as cnt
        FROM monsters
        WHERE cr_numeric IS NOT NULL
        GROUP BY cr_range
        ORDER BY MIN(cr_numeric)
    """)
    if rows:
        for cr_range, cnt in rows:
            print(f"  CR {cr_range:6s}: {cnt:,} monsters")

    print(f"\n{'=' * 60}")
    print("✓ Verification complete.")
    conn.close()


if __name__ == "__main__":
    main()
