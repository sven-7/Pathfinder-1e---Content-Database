#!/usr/bin/env python3
"""Migrate content data from SQLite (db/pf1e.db) to PostgreSQL content schema.

Usage:
    python scripts/migrate_sqlite_to_pg.py                 # real run
    python scripts/migrate_sqlite_to_pg.py --dry-run       # preview only

Requires CONTENT_DATABASE_URL or DATABASE_URL env var pointing to the PG instance
where `alembic upgrade head` has already created the content schema.
"""

import argparse
import os
import pathlib
import sqlite3
import sys

REPO_ROOT = pathlib.Path(__file__).parent.parent
SQLITE_PATH = REPO_ROOT / "db" / "pf1e.db"

# Tables in FK-safe insertion order (parents before children)
TABLE_ORDER = [
    "sources",
    "skills",
    "classes",
    "class_skills",
    "class_features",
    "class_progression",
    "archetypes",
    "archetype_features",
    "races",
    "racial_traits",
    "feats",
    "spells",
    "spell_class_levels",
    "equipment",
    "weapons",
    "armor",
    "magic_items",
    "monsters",
    "traits",
]

BATCH_SIZE = 500


def get_pg_dsn() -> str:
    dsn = os.getenv("CONTENT_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not dsn:
        print("ERROR: Set CONTENT_DATABASE_URL or DATABASE_URL env var.")
        sys.exit(1)
    # Strip asyncpg adapter suffix if present
    return dsn.replace("+asyncpg", "")


def get_columns(sqlite_conn: sqlite3.Connection, table: str) -> list[str]:
    """Return column names for a SQLite table."""
    cur = sqlite_conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    table: str,
    dry_run: bool = False,
) -> int:
    """Migrate one table from SQLite to PG. Returns row count."""
    columns = get_columns(sqlite_conn, table)
    col_list = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))

    rows = sqlite_conn.execute(f"SELECT {col_list} FROM {table}").fetchall()
    if not rows:
        return 0

    if dry_run:
        return len(rows)

    cur = pg_conn.cursor()

    # Truncate for idempotent re-runs
    cur.execute(f"TRUNCATE content.{table} CASCADE")

    # Batch insert
    insert_sql = f"INSERT INTO content.{table} ({col_list}) VALUES ({placeholders})"
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        cur.executemany(insert_sql, batch)

    pg_conn.commit()
    cur.close()
    return len(rows)


def reset_sequence(pg_conn, table: str, columns: list[str]):
    """Reset SERIAL sequence to max(id) + 1 if table has an 'id' column."""
    if "id" not in columns:
        return
    cur = pg_conn.cursor()
    cur.execute(f"SELECT MAX(id) FROM content.{table}")
    max_id = cur.fetchone()[0]
    if max_id is not None:
        seq_name = f"content.{table}_id_seq"
        cur.execute(f"SELECT setval('{seq_name}', {max_id})")
    pg_conn.commit()
    cur.close()


def populate_search_index(pg_conn, dry_run: bool = False) -> int:
    """Build the search_index from spells, feats, classes, races, monsters, traits, magic_items."""
    if dry_run:
        cur = pg_conn.cursor()
        # Estimate count from source tables
        count = 0
        for tbl, ctype in [
            ("spells", "spell"), ("feats", "feat"), ("classes", "class"),
            ("races", "race"), ("monsters", "monster"), ("traits", "trait"),
            ("magic_items", "item"),
        ]:
            cur.execute(f"SELECT COUNT(*) FROM content.{tbl}")
            count += cur.fetchone()[0]
        cur.close()
        return count

    cur = pg_conn.cursor()
    cur.execute("TRUNCATE content.search_index CASCADE")

    sources = [
        ("spells", "spell"),
        ("feats", "feat"),
        ("classes", "class"),
        ("races", "race"),
        ("monsters", "monster"),
        ("traits", "trait"),
        ("magic_items", "item"),
    ]

    total = 0
    for tbl, ctype in sources:
        # All these tables have: id, name, description; some also have source_id
        cur.execute(f"""
            INSERT INTO content.search_index (name, content_type, description, source, content_id)
            SELECT t.name, '{ctype}', t.description,
                   COALESCE(s.name, ''), t.id
            FROM content.{tbl} t
            LEFT JOIN content.sources s ON s.id = t.source_id
        """)
        total += cur.rowcount

    pg_conn.commit()
    cur.close()
    return total


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite content to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Preview row counts without writing")
    args = parser.parse_args()

    if not SQLITE_PATH.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_PATH}")
        sys.exit(1)

    # Connect SQLite (read-only)
    sqlite_conn = sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True)

    # Connect PG
    import psycopg2
    pg_dsn = get_pg_dsn()
    pg_conn = psycopg2.connect(pg_dsn)

    if args.dry_run:
        print("=== DRY RUN — no data will be written ===\n")

    print(f"Source: {SQLITE_PATH}")
    print(f"Target: {pg_dsn.split('@')[1] if '@' in pg_dsn else pg_dsn}\n")

    total_rows = 0
    for table in TABLE_ORDER:
        count = migrate_table(sqlite_conn, pg_conn, table, dry_run=args.dry_run)
        total_rows += count
        status = "would migrate" if args.dry_run else "migrated"
        print(f"  {table:25s} {count:>6,} rows {status}")

        # Reset sequences (skip in dry-run)
        if not args.dry_run:
            columns = get_columns(sqlite_conn, table)
            reset_sequence(pg_conn, table, columns)

    # Populate search index
    search_count = populate_search_index(pg_conn, dry_run=args.dry_run)
    status = "would index" if args.dry_run else "indexed"
    print(f"\n  {'search_index':25s} {search_count:>6,} rows {status}")
    total_rows += search_count

    print(f"\n{'Would migrate' if args.dry_run else 'Migrated'} {total_rows:,} total rows.")

    sqlite_conn.close()
    pg_conn.close()


if __name__ == "__main__":
    main()
