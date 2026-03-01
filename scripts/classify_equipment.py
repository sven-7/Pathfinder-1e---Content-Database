#!/usr/bin/env python3
"""Classify ~3,600 NULL-type equipment rows in the SQLite database.

For each distinct item name, picks the best row (prefer source_id=1 CRB,
then source_id=6 UE) and assigns an equipment_type. Duplicate rows
(same name, worse source) stay NULL and are excluded by API queries.

Also:
  - Parses cost strings → populates cost_copper INT column
  - Cleans weight column: strips HTML entities, footnotes
  - Marks junk rows (no cost, table headers) as equipment_type='other'

Usage:
  python scripts/classify_equipment.py            # apply changes
  python scripts/classify_equipment.py --dry-run   # preview only
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "pf1e.db"

# ── Classification rules (applied in order) ─────────────────────────────

ALCHEMICAL_NAMES = {
    "acid", "antitoxin", "smokestick", "tanglefoot bag", "thunderstone",
    "tindertwig", "sunrod", "holy water", "liquid ice", "flash powder",
    "itching powder", "sneezing powder", "nushadir", "soothe syrup",
    "fuse grenade", "pellet grenade", "burst jar", "ghast retch flask",
    "bloodblock", "smelling salts", "vermin repellent", "weapon blanch",
}

def classify_name(name: str, cost: str | None) -> str:
    """Return equipment_type for a given item name."""
    nl = name.lower()

    # Alchemical items
    if any(kw in nl for kw in ("alchemist", "alchemical")):
        return "alchemical"
    if nl in ALCHEMICAL_NAMES:
        return "alchemical"

    # Clothing
    if any(kw in nl for kw in ("outfit", "vestment", "cloak", "robe", "boots")):
        return "clothing"

    # Tools
    if any(kw in nl for kw in ("kit", "tools", "masterwork tool", "lab", "spyglass",
                                 "lock", "manacles", "thieves")):
        return "tool"

    # Mounts/animals
    if any(kw in nl for kw in ("horse", "pony", "dog, riding", "mule", "donkey",
                                 "camel", "elephant", "dog, guard")):
        return "mount"

    # Vehicles
    if any(kw in nl for kw in ("cart", "wagon", "carriage", "ship", "boat",
                                 "galley", "longship", "keelboat", "rowboat",
                                 "raft", "sled", "sleigh")):
        return "vehicle"

    # Services
    if any(kw in nl for kw in ("per day", "per mile", "per week", "per month",
                                 "lodging", "hireling", "inn stay", "coach cab",
                                 "messenger", "road toll", "ship passage")):
        return "service"

    # Junk: rows with no cost are likely table headers or non-items
    if not cost or cost.strip() in ("", "—", "&mdash;", "–"):
        return "other"

    # Default: generic gear
    return "gear"


# ── Cost parsing ─────────────────────────────────────────────────────────

def parse_cost_copper(cost_str: str | None) -> int | None:
    """Parse a cost string like '10 gp', '5 sp', '1 cp' → copper pieces.

    Handles: '10 gp', '50 gp/vial', '+50 gp', '3 cp per mile',
             '1,500 gp', '15,000 gp'
    Returns None if unparseable.
    """
    if not cost_str:
        return None
    s = cost_str.strip()
    # Strip leading + (armor spikes etc.)
    s = s.lstrip("+")
    # Strip trailing qualifiers like /flask, /vial, per mile, etc.
    s = re.split(r'[/;]| per ', s)[0].strip()
    # Remove HTML entities
    s = s.replace("&mdash;", "").replace("&ndash;", "").strip()

    # Match number + denomination
    m = re.match(r'^([\d,]+(?:\.\d+)?)\s*(gp|sp|cp|pp)$', s, re.IGNORECASE)
    if not m:
        return None

    val_str = m.group(1).replace(",", "")
    denom = m.group(2).lower()

    try:
        val = float(val_str)
    except ValueError:
        return None

    multipliers = {"cp": 1, "sp": 10, "gp": 100, "pp": 1000}
    return int(val * multipliers.get(denom, 100))


# ── Weight cleaning ──────────────────────────────────────────────────────

def clean_weight(weight_str: str | None) -> float | None:
    """Parse weight string → float pounds, or None.

    Handles: '5 lbs.', '1 lb.', '1/2 lb.', '5 lbs.1' (footnote),
             '&mdash;', None, '', '—', '10 lbs.2'
    """
    if weight_str is None:
        return None
    s = str(weight_str).strip()

    # HTML entities = no weight
    if not s or s in ("—", "–", "&mdash;", "&ndash;", "0"):
        return None

    # Strip footnote digits at end: "5 lbs.1" → "5 lbs."
    s = re.sub(r'(\d)\s*$', r'\1', s)  # no-op first
    s = re.sub(r'(lbs?\.?)\s*\d+$', r'\1', s)

    # Strip unit text
    s = re.sub(r'\s*(lbs?\.?|pounds?).*$', '', s, flags=re.IGNORECASE).strip()

    # Handle fractions like "1/2"
    if "/" in s:
        parts = s.split("/")
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return None

    # Strip leading + ("+10 lbs.")
    s = s.lstrip("+").strip()

    # Remove commas
    s = s.replace(",", "")

    try:
        return float(s) if s else None
    except ValueError:
        return None


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Classify NULL-type equipment rows")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get all NULL-type equipment rows
    rows = conn.execute(
        "SELECT id, name, cost, weight, source_id FROM equipment WHERE equipment_type IS NULL ORDER BY name, source_id"
    ).fetchall()
    print(f"Found {len(rows)} rows with NULL equipment_type\n")

    # Group by name — pick best source (prefer 1=CRB, 6=UE, else lowest)
    from collections import defaultdict
    by_name: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_name[r["name"]].append(dict(r))

    # Classify and update
    counts: dict[str, int] = defaultdict(int)
    updates: list[tuple] = []  # (equipment_type, cost_copper, weight, id)

    for name, dupes in by_name.items():
        # Pick best row: prefer source_id 1 (CRB), then 6 (UE), then lowest source_id
        best = None
        for d in dupes:
            sid = d["source_id"] or 999
            if best is None:
                best = d
            elif sid == 1:
                best = d
            elif sid == 6 and (best["source_id"] or 999) != 1:
                best = d
            elif sid < (best["source_id"] or 999) and (best["source_id"] or 999) not in (1, 6):
                best = d

        eq_type = classify_name(name, best["cost"])
        cost_cp = parse_cost_copper(best["cost"])
        weight = clean_weight(str(best["weight"]) if best["weight"] is not None else None)

        # Best row gets the classification
        updates.append((eq_type, cost_cp, weight, best["id"]))
        counts[eq_type] += 1

        # Duplicate rows stay as 'other' (they're superseded)
        for d in dupes:
            if d["id"] != best["id"]:
                dup_weight = clean_weight(str(d["weight"]) if d["weight"] is not None else None)
                dup_cost = parse_cost_copper(d["cost"])
                updates.append(("other", dup_cost, dup_weight, d["id"]))
                counts["other (duplicate)"] += 1

    # Also update cost_copper and weight for existing weapon/armor rows
    existing_rows = conn.execute(
        "SELECT id, cost, weight FROM equipment WHERE equipment_type IN ('weapon', 'armor')"
    ).fetchall()
    equip_updates: list[tuple] = []
    for r in existing_rows:
        cost_cp = parse_cost_copper(r["cost"])
        weight = clean_weight(str(r["weight"]) if r["weight"] is not None else None)
        equip_updates.append((cost_cp, weight, r["id"]))

    # Summary
    print("Classification summary:")
    print("-" * 40)
    for eq_type in sorted(counts.keys()):
        print(f"  {eq_type:20s} {counts[eq_type]:>5}")
    print("-" * 40)
    total_classified = sum(v for k, v in counts.items() if k != "other (duplicate)")
    print(f"  {'TOTAL classified':20s} {total_classified:>5}")
    print(f"  {'Duplicates → other':20s} {counts.get('other (duplicate)', 0):>5}")
    print(f"\n  Weapon/armor cost/weight updates: {len(equip_updates)}")

    if args.dry_run:
        print("\n[DRY RUN] No changes written.")
        conn.close()
        return

    # Apply updates
    conn.execute("BEGIN")
    for eq_type, cost_cp, weight, row_id in updates:
        conn.execute(
            "UPDATE equipment SET equipment_type = ?, cost_copper = ?, weight = ? WHERE id = ?",
            (eq_type, cost_cp, weight, row_id),
        )
    for cost_cp, weight, row_id in equip_updates:
        conn.execute(
            "UPDATE equipment SET cost_copper = ?, weight = ? WHERE id = ?",
            (cost_cp, weight, row_id),
        )
    conn.commit()
    print(f"\nUpdated {len(updates)} gear rows + {len(equip_updates)} weapon/armor rows.")
    conn.close()


if __name__ == "__main__":
    main()
