#!/usr/bin/env python3
"""
Import class progression 'Special' column from PSRD SQLite books into
class_progression.special in the main DB.

Covers:
  book-cr.db  — Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger,
                  Rogue, Sorcerer, Wizard (+ prestige classes)
  book-apg.db — Alchemist, Cavalier, Inquisitor, Magus (moved to um), Oracle,
                  Summoner, Witch
  book-acg.db — Arcanist, Bloodrager, Brawler, Hunter, Investigator, Shaman,
                  Skald, Slayer, Swashbuckler, Warpriest
  book-uc.db  — Gunslinger, Ninja, Samurai
  book-um.db  — Magus

Only updates rows where special IS NULL (or empty).  Pass --overwrite to
replace existing values too.

Run:
  python scripts/import_class_progression_psrd.py
  python scripts/import_class_progression_psrd.py --overwrite
"""

from __future__ import annotations
import argparse
import html as html_module
import pathlib
import re
import sqlite3

ROOT = pathlib.Path(__file__).parent.parent
PSRD_DIR = ROOT / "data" / "psrd"
DB_PATH  = ROOT / "db" / "pf1e.db"

# PSRD class name → DB class name (most are identical)
CLASS_NAME_MAP: dict[str, str] = {
    # Unchained variants are in a different book (not present in PSRD data we have)
    # Everything else is a direct match
}

BOOKS = [
    "book-cr.db",
    "book-apg.db",
    "book-acg.db",
    "book-uc.db",
    "book-um.db",
]


def strip_html(html_str: str) -> str:
    text = re.sub(r"<[^>]+>", "", html_str)
    text = html_module.unescape(text)
    return " ".join(text.split())


def find_special_col(header_html: str) -> int | None:
    """Return 0-based column index of the 'Special' column in the <thead> first <tr>."""
    header_rows = re.findall(r"<tr[^>]*>(.*?)</tr>", header_html, re.DOTALL | re.IGNORECASE)
    if not header_rows:
        return None
    # Use the FIRST header row to count columns
    headers = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", header_rows[0], re.DOTALL | re.IGNORECASE)
    headers_text = [strip_html(h) for h in headers]
    for i, h in enumerate(headers_text):
        if "special" in h.lower():
            return i
    return None


def parse_progression_table(body_html: str) -> dict[int, str | None]:
    """
    Parse an HTML progression table and return {level: special_text | None}.
    special_text is None if the cell is an em-dash (no feature that level).
    Handles both <tbody>-wrapped and bare <tr> formats.
    """
    result: dict[int, str | None] = {}
    if not body_html or "<table" not in body_html:
        return result

    # --- find <thead> ---
    thead_m = re.search(r"<thead[^>]*>(.*?)</thead>", body_html, re.DOTALL | re.IGNORECASE)
    if not thead_m:
        return result

    special_col = find_special_col(thead_m.group(1))
    if special_col is None:
        return result

    # --- find data rows: prefer <tbody>, fall back to all <tr> after </thead> ---
    tbody_m = re.search(r"<tbody[^>]*>(.*?)</tbody>", body_html, re.DOTALL | re.IGNORECASE)
    if tbody_m:
        data_html = tbody_m.group(1)
    else:
        # Strip everything up through </thead>, use the rest
        after_thead = body_html[thead_m.end():]
        # Also strip any trailing </table>
        after_thead = re.sub(r"</table.*$", "", after_thead, flags=re.DOTALL | re.IGNORECASE)
        data_html = after_thead

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", data_html, re.DOTALL | re.IGNORECASE)
    for row_html in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL | re.IGNORECASE)
        if not cells:
            continue
        # First cell = level ("1st", "2nd", …)
        level_text = strip_html(cells[0])
        m = re.match(r"^(\d+)", level_text)
        if not m:
            continue
        level = int(m.group(1))

        if special_col < len(cells):
            raw = strip_html(cells[special_col])
            # Em-dash variants → no special
            if raw in ("—", "\u2014", "\u2013", "-", ""):
                result[level] = None
            else:
                result[level] = raw
        else:
            result[level] = None

    return result


def find_progression_table(psrd_cur: sqlite3.Cursor, class_section_id: int) -> dict[int, str | None]:
    """
    Locate the progression table in the PSRD DB for a given class section.
    Searches within the nested-set subtree (lft/rgt).
    """
    psrd_cur.execute(
        "SELECT lft, rgt FROM sections WHERE section_id = ?", (class_section_id,)
    )
    row = psrd_cur.fetchone()
    if not row:
        return {}
    lft, rgt = row["lft"], row["rgt"]

    # Find all table-type sections within the subtree
    psrd_cur.execute(
        """
        SELECT section_id, body
        FROM sections
        WHERE lft >= ? AND rgt <= ? AND type = 'table'
        ORDER BY lft
        """,
        (lft, rgt),
    )
    for trow in psrd_cur.fetchall():
        body = trow["body"] or ""
        # Must contain a <thead> with a 'Special' column
        if "<thead" in body.lower() and "special" in body.lower():
            parsed = parse_progression_table(body)
            if parsed:
                return parsed
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing non-NULL special values",
    )
    args = parser.parse_args()

    main_conn = sqlite3.connect(DB_PATH)
    main_conn.row_factory = sqlite3.Row
    main_cur = main_conn.cursor()

    # Build class name → class_id map from main DB
    main_cur.execute("SELECT id, name FROM classes")
    class_id_map: dict[str, int] = {r["name"]: r["id"] for r in main_cur.fetchall()}

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

        # Find all class sections
        psrd_cur.execute(
            "SELECT section_id, name FROM sections WHERE type = 'class' ORDER BY name"
        )
        class_sections = psrd_cur.fetchall()

        print(f"\n=== {book_filename} ({len(class_sections)} classes) ===")

        for cs in class_sections:
            psrd_name = cs["name"]
            db_name = CLASS_NAME_MAP.get(psrd_name, psrd_name)  # default: same name

            class_id = class_id_map.get(db_name)
            if not class_id:
                print(f"  [skip] '{psrd_name}' not in main DB")
                continue

            # Parse progression table
            progression = find_progression_table(psrd_cur, cs["section_id"])
            if not progression:
                print(f"  [skip] '{psrd_name}' — no progression table found")
                continue

            class_updated = 0
            class_skipped = 0

            for level, special in sorted(progression.items()):
                if special is None:
                    # Nothing to set
                    continue

                # Check current value
                main_cur.execute(
                    """
                    SELECT id, special FROM class_progression
                    WHERE class_id = ? AND level = ?
                    """,
                    (class_id, level),
                )
                prog_row = main_cur.fetchone()
                if not prog_row:
                    # No progression row for this level — unusual
                    continue

                existing = prog_row["special"]
                if existing and not args.overwrite:
                    class_skipped += 1
                    continue

                main_cur.execute(
                    "UPDATE class_progression SET special = ? WHERE id = ?",
                    (special, prog_row["id"]),
                )
                class_updated += 1

            main_conn.commit()
            status = f"updated {class_updated}, skipped {class_skipped}"
            print(f"  {db_name}: {status}")
            total_updated += class_updated
            total_skipped += class_skipped

        psrd_conn.close()

    print(f"\n=== Done: {total_updated} rows updated, {total_skipped} rows skipped ===")

    # Show before/after for key classes
    print("\nVerification (first 5 levels for key classes):")
    for cn in ("Investigator", "Swashbuckler", "Arcanist", "Shaman", "Wizard"):
        cid = class_id_map.get(cn)
        if not cid:
            continue
        main_cur.execute(
            "SELECT level, special FROM class_progression WHERE class_id = ? ORDER BY level LIMIT 7",
            (cid,),
        )
        rows = main_cur.fetchall()
        print(f"\n  {cn}:")
        for r in rows:
            print(f"    L{r['level']:2d}: {r['special']}")

    main_conn.close()


if __name__ == "__main__":
    main()
