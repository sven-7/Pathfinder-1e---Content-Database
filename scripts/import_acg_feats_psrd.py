#!/usr/bin/env python3
"""
Import 129 Advanced Class Guide feats from book-acg.db that are missing
from the main feats table.

Also adds benefit/prerequisites/normal/special for any ACG feats that are
already in the DB but lack text.

Run:
  python scripts/import_acg_feats_psrd.py
  python scripts/import_acg_feats_psrd.py --dry-run
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
ACG_DB   = PSRD_DIR / "book-acg.db"

ACG_SOURCE_ID = 18   # "Advanced Class Guide" in sources table


def strip_html(s: str | None) -> str:
    text = re.sub(r"<[^>]+>", "", s or "")
    return htmlmod.unescape(text).strip()


def get_children(psrd_cur: sqlite3.Cursor, lft: int, rgt: int) -> dict[str, str]:
    """Return {child_name_lower: text} for child sections of a feat."""
    psrd_cur.execute(
        "SELECT name, description, body FROM sections WHERE lft > ? AND rgt < ? ORDER BY lft",
        (lft, rgt),
    )
    result: dict[str, str] = {}
    for c in psrd_cur.fetchall():
        key = (c["name"] or "").strip().lower()
        text = strip_html(c["body"] or c["description"] or "")
        if text:
            result[key] = text
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be imported without writing")
    args = parser.parse_args()

    if not ACG_DB.exists():
        print(f"ERROR: {ACG_DB} not found")
        return

    # ── Load main DB ─────────────────────────────────────────────────────────
    main_conn = sqlite3.connect(DB_PATH)
    main_conn.row_factory = sqlite3.Row
    main_cur  = main_conn.cursor()

    main_cur.execute("SELECT id, name, benefit, prerequisites FROM feats")
    db_feats: dict[str, sqlite3.Row] = {}
    for r in main_cur.fetchall():
        db_feats[r["name"].strip().lower()] = r

    # ── Load PSRD ACG ─────────────────────────────────────────────────────────
    psrd_conn = sqlite3.connect(ACG_DB)
    psrd_conn.row_factory = sqlite3.Row
    psrd_cur  = psrd_conn.cursor()

    psrd_cur.execute(
        "SELECT section_id, name, lft, rgt, description FROM sections WHERE type='feat' ORDER BY name"
    )
    acg_feats = psrd_cur.fetchall()

    # Build feat_type lookup
    psrd_cur.execute("SELECT section_id, feat_type FROM feat_types")
    ft_map = {r["section_id"]: r["feat_type"] for r in psrd_cur.fetchall()}

    # ── Process each ACG feat ─────────────────────────────────────────────────
    inserted = 0
    updated  = 0

    for f in acg_feats:
        name   = f["name"].strip()
        key    = name.lower()
        ft     = ft_map.get(f["section_id"], "General")
        desc   = strip_html(f["description"])
        children = get_children(psrd_cur, f["lft"], f["rgt"])

        benefit     = children.get("benefits") or children.get("benefit") or ""
        prereqs     = children.get("prerequisites") or children.get("prerequisite") or ""
        normal      = children.get("normal") or ""
        special     = children.get("special") or ""

        existing = db_feats.get(key)

        if existing is None:
            # ── INSERT new feat ───────────────────────────────────────────────
            if args.dry_run:
                print(f"[INSERT] {name} [{ft}]")
                if benefit:
                    print(f"         benefit: {benefit[:80]}")
            else:
                main_cur.execute(
                    """
                    INSERT INTO feats
                      (name, source_id, feat_type, prerequisites, benefit,
                       normal, special, description, is_paizo_official)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (name, ACG_SOURCE_ID, ft,
                     prereqs or None, benefit or None,
                     normal or None, special or None, desc or None),
                )
                inserted += 1
        else:
            # ── UPDATE existing feat (fill empty columns only) ────────────────
            updates: dict[str, str] = {}
            for col, val in [("benefit", benefit), ("prerequisites", prereqs),
                             ("normal", normal), ("special", special),
                             ("description", desc)]:
                if not val:
                    continue
                existing_val = existing[col] if col in existing.keys() else None
                if not existing_val:
                    updates[col] = val
            if updates:
                if args.dry_run:
                    print(f"[UPDATE] {name}: {list(updates.keys())}")
                else:
                    set_clause = ", ".join(f"{c} = ?" for c in updates)
                    main_cur.execute(
                        f"UPDATE feats SET {set_clause} WHERE id = ?",
                        (*updates.values(), existing["id"]),
                    )
                    updated += 1

    if not args.dry_run:
        main_conn.commit()

    psrd_conn.close()
    main_conn.close()

    print(f"\nACG feats: {inserted} inserted, {updated} updated")

    if not args.dry_run:
        # ── Verification ─────────────────────────────────────────────────────
        conn2 = sqlite3.connect(DB_PATH)
        conn2.row_factory = sqlite3.Row
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) as cnt FROM feats WHERE source_id = 18")
        acg_count = cur2.fetchone()["cnt"]
        print(f"ACG feats in DB now: {acg_count}")

        cur2.execute("SELECT COUNT(*) as total FROM feats")
        total = cur2.fetchone()["total"]
        cur2.execute("SELECT COUNT(*) as cnt FROM feats WHERE benefit IS NOT NULL AND benefit != ''")
        with_benefit = cur2.fetchone()["cnt"]
        print(f"Total feats: {total}, with benefit: {with_benefit} ({with_benefit*100//total}%)")
        conn2.close()


if __name__ == "__main__":
    main()
