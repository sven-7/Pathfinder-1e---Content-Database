"""Phase 5 — Import feat types, prerequisites, and benefit text from Foundry VTT data.

Sources:
  data/foundry/packs/pf-feats.db   (NDJSON, 3,541 records)

Updates feats table:
  - feat_type      (real types: Combat, Metamagic, Teamwork, etc.)
  - prerequisites  (plain text extracted from HTML description)
  - benefit        (plain text extracted from HTML description)

Also adds is_paizo_official INTEGER DEFAULT 1 to feats, archetypes, and traits tables.

Usage:
  python scripts/import_feat_data.py
  python scripts/import_feat_data.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

DB_PATH = Path("db/pf1e.db")
FOUNDRY_FEATS = Path("data/foundry/packs/pf-feats.db")

# Tags to skip when choosing feat_type (source flags, not types)
_SKIP_TAGS = {"pfs"}

# Normalise raw Foundry tag strings to clean display names
_TYPE_NORM: dict[str, str] = {
    "combat":         "Combat",
    "metamagic":      "Metamagic",
    "teamwork":       "Teamwork",
    "item creation":  "Item Creation",
    "item mastery":   "Item Mastery",
    "armor mastery":  "Armor Mastery",
    "weapon mastery": "Weapon Mastery",
    "performance":    "Performance",
    "style":          "Style",
    "racial":         "Racial",
    "general":        "General",
    "channeling":     "Channeling",
    "meditation":     "Meditation",
    "blood hex":      "Blood Hex",
    "critical":       "Critical",
    "grit":           "Grit",
    "panache":        "Panache",
    "conduit":        "Conduit",
    "stare":          "Stare",
    "targeting":      "Targeting",
    "story":          "Story",
    "mythic":         "Mythic",
    "monster":        "Monster",
    "esoteric":       "Esoteric",
    "faction":        "Faction",
    "familiar":       "Familiar",
    "alignment":      "Alignment",
}


def _strip_html(html: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", text).strip()


def _extract_section(html: str, *headers: str) -> str:
    """Extract plain text between a bold header and the next bold tag.

    Uses backreference so <b>…</b> and <strong>…</strong> are matched
    correctly without false-matching <br/> (which also starts with 'b').
    """
    for header in headers:
        # Backreference \\1 ensures the closing tag matches the opening tag.
        # This avoids <br/> being matched by a naive <b[^>]*> pattern.
        pattern = (
            rf"<(strong|b)>\s*{re.escape(header)}s?\s*</\1>"
            r"(.*?)(?=<(?:strong|b)>|$)"
        )
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            return _strip_html(m.group(2))
    return ""


def _feat_type_from_tags(tags: list) -> str:
    """Extract the most specific feat type from a Foundry tags array."""
    for tag_group in tags:
        if not isinstance(tag_group, list):
            continue
        for raw in tag_group:
            key = raw.strip().lower()
            if key in _SKIP_TAGS:
                continue
            return _TYPE_NORM.get(key, raw.strip().title())
    return "General"


def load_foundry_feats(path: Path) -> dict[str, dict]:
    """Return dict keyed by lowercase name → {feat_type, prerequisites, benefit}."""
    feats: dict[str, dict] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            name = obj.get("name", "").strip()
            if not name:
                continue

            sys_data = obj.get("system", obj.get("data", {}))
            desc_html = (sys_data.get("description") or {}).get("value", "")
            tags = sys_data.get("tags", [])

            feats[name.lower()] = {
                "feat_type":    _feat_type_from_tags(tags),
                "prerequisites": _extract_section(desc_html, "Prerequisite", "Prerequisites"),
                "benefit":       _extract_section(desc_html, "Benefit", "Benefits"),
            }
    return feats


def add_paizo_official_columns(conn: sqlite3.Connection) -> None:
    """Add is_paizo_official column to feats, archetypes, and traits if absent."""
    cur = conn.cursor()
    for table in ("feats", "archetypes", "traits"):
        cur.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cur.fetchall()}
        if "is_paizo_official" not in existing:
            print(f"  Adding is_paizo_official to {table}...")
            cur.execute(
                f"ALTER TABLE {table} ADD COLUMN is_paizo_official INTEGER DEFAULT 1"
            )
            cur.execute(f"UPDATE {table} SET is_paizo_official = 1")
    conn.commit()


def _foundry_lookup(foundry: dict, name: str) -> dict | None:
    """Try multiple name variants to find a Foundry match."""
    # 1. Direct match
    data = foundry.get(name.lower())
    if data:
        return data
    # 2. "Foo, Mythic" → "Foo (Mythic)"
    if ", " in name:
        parts = name.split(", ", 1)
        variant = f"{parts[0]} ({parts[1]})".lower()
        data = foundry.get(variant)
        if data:
            return data
    return None


def update_feats(
    conn: sqlite3.Connection, foundry: dict[str, dict], dry_run: bool = False
) -> tuple[int, int, list[str]]:
    """Update feat rows with Foundry data. Returns (matched_count, total_count, unmatched)."""
    cur = conn.cursor()
    cur.execute("SELECT id, name, url FROM feats")
    rows = cur.fetchall()

    matched = 0
    unmatched: list[str] = []

    for feat_id, name, url in rows:
        data = _foundry_lookup(foundry, name)
        if data:
            matched += 1
            if not dry_run:
                cur.execute(
                    """UPDATE feats
                       SET feat_type    = ?,
                           prerequisites = ?,
                           benefit       = ?
                       WHERE id = ?""",
                    (data["feat_type"], data["prerequisites"], data["benefit"], feat_id),
                )
        else:
            # Tag mythic path abilities and wrongly-scraped items
            url = url or ""
            if "/Mythic Heroes/" in url:
                inferred_type = "Mythic Path Ability"
            elif "/Wondrous" in url or ("/Magic Items" in url and "feat" not in url.lower()):
                inferred_type = "Item (invalid)"
            else:
                inferred_type = None

            if inferred_type and not dry_run:
                cur.execute(
                    "UPDATE feats SET feat_type = ? WHERE id = ?",
                    (inferred_type, feat_id),
                )
            unmatched.append(name)

    if not dry_run:
        conn.commit()

    return matched, len(rows), unmatched


def print_type_distribution(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT feat_type, COUNT(*) c FROM feats GROUP BY feat_type ORDER BY c DESC"
    )
    print("\n  Feat type distribution after update:")
    for row in cur.fetchall():
        label = row[0] or "NULL"
        print(f"    {label:30s} {row[1]:>5}")


def main(dry_run: bool = False) -> None:
    print("Phase 5 — Feat data import from Foundry VTT")
    if dry_run:
        print("  (DRY RUN — no DB changes)")

    print(f"  Loading {FOUNDRY_FEATS} ...")
    foundry = load_foundry_feats(FOUNDRY_FEATS)
    print(f"  Loaded {len(foundry):,} Foundry feat records")

    conn = sqlite3.connect(DB_PATH)

    print("  Ensuring is_paizo_official columns exist...")
    if not dry_run:
        add_paizo_official_columns(conn)
    else:
        print("  (skipped — dry run)")

    print("  Matching and updating feats...")
    matched, total, unmatched = update_feats(conn, foundry, dry_run=dry_run)
    pct = matched / total * 100 if total else 0
    print(f"  Matched {matched}/{total} feats ({pct:.1f}%)")

    if unmatched:
        print(f"\n  Unmatched feats ({len(unmatched)}) — will keep existing data:")
        for name in sorted(unmatched)[:40]:
            print(f"    - {name}")
        if len(unmatched) > 40:
            print(f"    ... and {len(unmatched)-40} more")

    if not dry_run:
        print_type_distribution(conn)

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report matches without writing to DB")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
