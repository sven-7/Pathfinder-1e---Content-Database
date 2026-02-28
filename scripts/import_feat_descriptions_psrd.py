#!/usr/bin/env python3
"""
Import feat benefit/prerequisite/normal/special/description text from PSRD
SQLite books into the main feats table.

Only fills columns that are currently NULL or empty (pass --overwrite to
replace existing values too).

Run:
  python scripts/import_feat_descriptions_psrd.py
  python scripts/import_feat_descriptions_psrd.py --overwrite
"""

from __future__ import annotations
import argparse
import html as htmlmod
import pathlib
import re
import sqlite3

ROOT     = pathlib.Path(__file__).parent.parent
PSRD_DIR = ROOT / "data" / "psrd"
DB_PATH  = ROOT / "db" / "pf1e.db"

# Books to process (in priority order — later books don't overwrite earlier)
BOOKS = [
    "book-cr.db",
    "book-apg.db",
    "book-acg.db",
    "book-uc.db",
    "book-um.db",
    "book-arg.db",
    "book-ucampaign.db",
    "book-ma.db",
]

# PSRD child-section name → main DB feats column
CHILD_MAP: dict[str, str] = {
    "benefits":      "benefit",
    "benefit":       "benefit",
    "prerequisites": "prerequisites",
    "prerequisite":  "prerequisites",
    "normal":        "normal",
    "special":       "special",
}


def strip_html(s: str | None) -> str:
    text = re.sub(r"<[^>]+>", "", s or "")
    return htmlmod.unescape(text).strip()


def extract_feat_data(psrd_cur: sqlite3.Cursor, feat_section_id: int,
                      lft: int, rgt: int) -> dict[str, str | None]:
    """
    Extract benefit/prerequisites/normal/special/description from a feat section.
    Returns a dict with keys matching feats table columns.
    """
    data: dict[str, str | None] = {}

    # Get the feat's own description (flavor text)
    psrd_cur.execute(
        "SELECT description FROM sections WHERE section_id = ?",
        (feat_section_id,),
    )
    row = psrd_cur.fetchone()
    if row and row["description"]:
        data["description"] = strip_html(row["description"])

    # Get child sections
    psrd_cur.execute(
        """
        SELECT name, description, body
        FROM sections
        WHERE lft > ? AND rgt < ?
        ORDER BY lft
        """,
        (lft, rgt),
    )
    for child in psrd_cur.fetchall():
        child_name = (child["name"] or "").strip().lower()
        col = CHILD_MAP.get(child_name)
        if col is None:
            continue
        # Prefer body (HTML) over description
        text = strip_html(child["body"] or child["description"] or "")
        if text:
            data[col] = text

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing non-NULL/non-empty values",
    )
    args = parser.parse_args()

    main_conn = sqlite3.connect(DB_PATH)
    main_conn.row_factory = sqlite3.Row
    main_cur = main_conn.cursor()

    # Build a normalised name → (id, existing data) lookup
    main_cur.execute("""
        SELECT id, name, benefit, prerequisites, normal, special, description
        FROM feats
    """)
    feats_by_name: dict[str, sqlite3.Row] = {}
    for row in main_cur.fetchall():
        feats_by_name[row["name"].strip().lower()] = row

    total_updated = 0
    total_skipped = 0

    for book_filename in BOOKS:
        book_path = PSRD_DIR / book_filename
        if not book_path.exists():
            print(f"[skip] {book_filename} not found")
            continue

        psrd_conn = sqlite3.connect(book_path)
        psrd_conn.row_factory = sqlite3.Row
        psrd_cur = psrd_conn.cursor()

        psrd_cur.execute(
            "SELECT section_id, name, lft, rgt FROM sections WHERE type='feat' ORDER BY name"
        )
        feat_sections = psrd_cur.fetchall()

        book_updated = book_skipped = book_missing = 0

        for fs in feat_sections:
            psrd_name = (fs["name"] or "").strip()
            key = psrd_name.lower()

            feat_row = feats_by_name.get(key)
            if not feat_row:
                book_missing += 1
                continue

            feat_data = extract_feat_data(psrd_cur, fs["section_id"], fs["lft"], fs["rgt"])
            if not feat_data:
                continue

            # Build UPDATE for columns that are empty (or all if --overwrite)
            updates: dict[str, str] = {}
            for col, value in feat_data.items():
                if not value:
                    continue
                existing = feat_row[col] if col in feat_row.keys() else None
                if existing and not args.overwrite:
                    book_skipped += 1
                    continue
                updates[col] = value

            if not updates:
                continue

            set_clause = ", ".join(f"{col} = ?" for col in updates)
            main_cur.execute(
                f"UPDATE feats SET {set_clause} WHERE id = ?",
                (*updates.values(), feat_row["id"]),
            )
            book_updated += 1
            total_updated += 1

        main_conn.commit()
        psrd_conn.close()
        print(f"{book_filename}: updated {book_updated}, skipped {book_skipped}, not-in-DB {book_missing}")
        total_skipped += book_skipped

    print(f"\n=== Done: {total_updated} feats updated, {total_skipped} fields skipped ===")

    # ── Verification ─────────────────────────────────────────────────────────
    print("\nCoverage after import:")
    cols = ["benefit", "prerequisites", "normal", "special", "description"]
    main_cur.execute("SELECT COUNT(*) as total FROM feats")
    total = main_cur.fetchone()["total"]
    for col in cols:
        main_cur.execute(
            f"SELECT COUNT(*) as cnt FROM feats WHERE {col} IS NOT NULL AND {col} != ''"
        )
        n = main_cur.fetchone()["cnt"]
        print(f"  {col:15s}: {n:4d} / {total}")

    # Sample a few updated feats
    print("\nSample — benefit text (first 100 chars):")
    main_cur.execute("""
        SELECT name, benefit FROM feats
        WHERE benefit IS NOT NULL AND benefit != ''
        ORDER BY name
        LIMIT 8
    """)
    for r in main_cur.fetchall():
        print(f"  {r['name']}: {(r['benefit'] or '')[:100]}")

    main_conn.close()


if __name__ == "__main__":
    main()
