"""
import_acg_progressions.py — Import class spell progressions from PSRD book-acg.db
and hardcode spell slots for OA classes not covered by PSRD.

Run:
    python scripts/import_acg_progressions.py [--dry-run]

Covers:
  From PSRD book-acg.db: Arcanist, Bloodrager, Hunter, Shaman, Skald, Warpriest
  Hardcoded OA:           Mesmerist, Occultist, Psychic, Spiritualist
  Hardcoded other:        Unchained Summoner, Omdura
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "pf1e.db"
PSRD_ACG = ROOT / "data" / "psrd" / "book-acg.db"

sys.path.insert(0, str(ROOT))
from src.rules_engine.progression import parse_class_progression_html, LevelRow


# ── Hardcoded spell slots for OA + other classes not in PSRD ─────────────── #
# Format: list of 20 dicts, each {level: int, spells_per_day: dict | None}
# OA class spell tables (Occult Adventures, Paizo 2015)
# spells_per_day keys: "0", "1".."9"; None = non-spellcasting level

def _oa_6th_caster(name: str) -> list[dict]:
    """6th-level psychic caster table (Mesmerist, Occultist, Spiritualist)."""
    # Spells per day: 0  1  2  3  4  5  6
    table = [
        # lvl  0  1  2  3  4  5  6
        (  1,  3, 1, None, None, None, None, None),
        (  2,  4, 2, None, None, None, None, None),
        (  3,  4, 3, None, None, None, None, None),
        (  4,  4, 3, 1,    None, None, None, None),
        (  5,  4, 4, 2,    None, None, None, None),
        (  6,  5, 4, 3,    None, None, None, None),
        (  7,  5, 4, 3,    1,    None, None, None),
        (  8,  5, 4, 4,    2,    None, None, None),
        (  9,  5, 5, 4,    3,    None, None, None),
        ( 10,  5, 5, 4,    3,    1,    None, None),
        ( 11,  6, 5, 4,    4,    2,    None, None),
        ( 12,  6, 5, 5,    4,    3,    None, None),
        ( 13,  6, 5, 5,    4,    3,    1,    None),
        ( 14,  6, 5, 5,    4,    4,    2,    None),
        ( 15,  6, 5, 5,    5,    4,    3,    None),
        ( 16,  6, 5, 5,    5,    4,    3,    1   ),
        ( 17,  6, 5, 5,    5,    4,    4,    2   ),
        ( 18,  7, 5, 5,    5,    5,    4,    3   ),
        ( 19,  7, 5, 5,    5,    5,    5,    4   ),
        ( 20,  7, 5, 5,    5,    5,    5,    5   ),
    ]
    result = []
    for row in table:
        lvl = row[0]
        spd = {}
        for i, slot_count in enumerate(row[1:]):
            if slot_count is not None:
                spd[str(i)] = slot_count
        result.append({"level": lvl, "spells_per_day": spd})
    return result


def _psychic_9th_caster() -> list[dict]:
    """9th-level psychic caster (Psychic class)."""
    table = [
        # lvl  0  1  2  3  4  5  6  7  8  9
        (  1,  3, 1, None, None, None, None, None, None, None, None),
        (  2,  4, 2, None, None, None, None, None, None, None, None),
        (  3,  4, 2, 1,    None, None, None, None, None, None, None),
        (  4,  4, 3, 2,    None, None, None, None, None, None, None),
        (  5,  4, 3, 2,    1,    None, None, None, None, None, None),
        (  6,  4, 3, 3,    2,    None, None, None, None, None, None),
        (  7,  4, 4, 3,    2,    1,    None, None, None, None, None),
        (  8,  4, 4, 3,    3,    2,    None, None, None, None, None),
        (  9,  4, 4, 4,    3,    2,    1,    None, None, None, None),
        ( 10,  4, 4, 4,    3,    3,    2,    None, None, None, None),
        ( 11,  4, 4, 4,    4,    3,    2,    1,    None, None, None),
        ( 12,  4, 4, 4,    4,    3,    3,    2,    None, None, None),
        ( 13,  4, 4, 4,    4,    4,    3,    2,    1,    None, None),
        ( 14,  4, 4, 4,    4,    4,    3,    3,    2,    None, None),
        ( 15,  4, 4, 4,    4,    4,    4,    3,    2,    1,    None),
        ( 16,  4, 4, 4,    4,    4,    4,    3,    3,    2,    None),
        ( 17,  4, 4, 4,    4,    4,    4,    4,    3,    2,    1   ),
        ( 18,  4, 4, 4,    4,    4,    4,    4,    3,    3,    2   ),
        ( 19,  4, 4, 4,    4,    4,    4,    4,    4,    3,    3   ),
        ( 20,  4, 4, 4,    4,    4,    4,    4,    4,    4,    4   ),
    ]
    result = []
    for row in table:
        lvl = row[0]
        spd = {}
        for i, slot_count in enumerate(row[1:]):
            if slot_count is not None:
                spd[str(i)] = slot_count
        result.append({"level": lvl, "spells_per_day": spd})
    return result


def _unchained_summoner_spells() -> list[dict]:
    """Unchained Summoner 6th-level arcane caster (modified spell list vs original)."""
    table = [
        # Same progression as original Summoner per Pathfinder Unchained
        # lvl  1  2  3  4  5  6
        (  1,  1, None, None, None, None, None),
        (  2,  2, None, None, None, None, None),
        (  3,  3, None, None, None, None, None),
        (  4,  3, 1,    None, None, None, None),
        (  5,  4, 2,    None, None, None, None),
        (  6,  4, 3,    None, None, None, None),
        (  7,  4, 3,    1,    None, None, None),
        (  8,  4, 4,    2,    None, None, None),
        (  9,  5, 4,    3,    None, None, None),
        ( 10,  5, 4,    3,    1,    None, None),
        ( 11,  5, 4,    4,    2,    None, None),
        ( 12,  5, 5,    4,    3,    None, None),
        ( 13,  5, 5,    4,    3,    1,    None),
        ( 14,  5, 5,    4,    4,    2,    None),
        ( 15,  5, 5,    5,    4,    3,    None),
        ( 16,  5, 5,    5,    4,    3,    1   ),
        ( 17,  5, 5,    5,    4,    4,    2   ),
        ( 18,  5, 5,    5,    5,    4,    3   ),
        ( 19,  5, 5,    5,    5,    5,    4   ),
        ( 20,  5, 5,    5,    5,    5,    5   ),
    ]
    result = []
    for row in table:
        lvl = row[0]
        spd = {}
        for i, slot_count in enumerate(row[1:]):
            if slot_count is not None:
                spd[str(i + 1)] = slot_count  # starts at 1st-level slots
        result.append({"level": lvl, "spells_per_day": spd})
    return result


def _omdura_spells() -> list[dict]:
    """Omdura 6th-level divine caster (Adventurer's Guide)."""
    table = [
        (  1,  1, None, None, None, None, None),
        (  2,  2, None, None, None, None, None),
        (  3,  3, None, None, None, None, None),
        (  4,  3, 1,    None, None, None, None),
        (  5,  4, 2,    None, None, None, None),
        (  6,  4, 3,    None, None, None, None),
        (  7,  4, 3,    1,    None, None, None),
        (  8,  4, 4,    2,    None, None, None),
        (  9,  5, 4,    3,    None, None, None),
        ( 10,  5, 4,    3,    1,    None, None),
        ( 11,  5, 4,    4,    2,    None, None),
        ( 12,  5, 5,    4,    3,    None, None),
        ( 13,  5, 5,    4,    3,    1,    None),
        ( 14,  5, 5,    4,    4,    2,    None),
        ( 15,  5, 5,    5,    4,    3,    None),
        ( 16,  5, 5,    5,    4,    3,    1   ),
        ( 17,  5, 5,    5,    4,    4,    2   ),
        ( 18,  5, 5,    5,    5,    4,    3   ),
        ( 19,  5, 5,    5,    5,    5,    4   ),
        ( 20,  5, 5,    5,    5,    5,    5   ),
    ]
    result = []
    for row in table:
        lvl = row[0]
        spd = {}
        for i, slot_count in enumerate(row[1:]):
            if slot_count is not None:
                spd[str(i + 1)] = slot_count
        result.append({"level": lvl, "spells_per_day": spd})
    return result


HARDCODED_CLASSES: dict[str, list[dict]] = {
    "Mesmerist":         _oa_6th_caster("Mesmerist"),
    "Occultist":         _oa_6th_caster("Occultist"),
    "Spiritualist":      _oa_6th_caster("Spiritualist"),
    "Psychic":           _psychic_9th_caster(),
    "Unchained Summoner": _unchained_summoner_spells(),
    "Omdura":            _omdura_spells(),
}


def load_psrd_acg(dry_run: bool = False) -> dict[str, list[LevelRow]]:
    """Load class progression rows from PSRD book-acg.db.

    Returns: {class_name: [LevelRow, ...]}
    """
    if not PSRD_ACG.exists():
        print(f"[warn] {PSRD_ACG} not found", file=sys.stderr)
        return {}

    conn = sqlite3.connect(str(PSRD_ACG))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all class-type sections with BAB progression tables
    cur.execute("""
        SELECT s.section_id, s.name, s.parent_id, s.body
        FROM sections s
        WHERE s.type = 'table'
          AND s.body LIKE '%Base Attack Bonus%'
          AND s.name != ''
    """)
    result: dict[str, list[LevelRow]] = {}
    for row in cur.fetchall():
        name = row["name"]
        body = row["body"]
        try:
            levels = parse_class_progression_html(body)
            if levels and len(levels) >= 10:
                result[name] = levels
        except Exception as e:
            print(f"  [warn] parse error for '{name}': {e}", file=sys.stderr)

    conn.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Load class name → id
    cur.execute("SELECT id, name FROM classes")
    class_map: dict[str, int] = {r["name"]: r["id"] for r in cur.fetchall()}

    # ── PSRD ACG source ───────────────────────────────────────────────── #
    psrd_classes = load_psrd_acg()
    print(f"[psrd-acg] Found {len(psrd_classes)} class progression tables")

    # ── Merge all sources ─────────────────────────────────────────────── #
    to_import: dict[str, list[dict]] = {}

    for class_name, level_rows in psrd_classes.items():
        rows_as_dicts = [
            {
                "level": lr.level,
                "bab": lr.bab,
                "fort_save": lr.fort_save,
                "ref_save": lr.ref_save,
                "will_save": lr.will_save,
                "special": lr.special,
                "spells_per_day": lr.spells_per_day,
            }
            for lr in level_rows
        ]
        to_import[class_name] = rows_as_dicts

    for class_name, spell_rows in HARDCODED_CLASSES.items():
        # For hardcoded, we only update spells_per_day on existing progression rows
        to_import[f"__spells_only__{class_name}"] = spell_rows

    # ── Apply to DB ────────────────────────────────────────────────────── #
    updated_classes = 0
    skipped = 0

    for key, rows in to_import.items():
        spells_only = key.startswith("__spells_only__")
        class_name = key.removeprefix("__spells_only__")

        class_id = class_map.get(class_name)
        if class_id is None:
            print(f"  [skip] '{class_name}' not in DB")
            skipped += 1
            continue

        # Check if this class already has spells in the DB
        existing = cur.execute(
            """SELECT COUNT(*) as c FROM class_progression
               WHERE class_id=? AND spells_per_day IS NOT NULL""",
            (class_id,),
        ).fetchone()["c"]

        if existing > 0:
            print(f"  [skip] '{class_name}' already has {existing} spell-slot rows")
            skipped += 1
            continue

        # Check if progression rows exist (for spells-only update)
        existing_levels = cur.execute(
            "SELECT COUNT(*) as c FROM class_progression WHERE class_id=?",
            (class_id,),
        ).fetchone()["c"]

        if args.dry_run:
            has_spells = sum(1 for r in rows if r.get("spells_per_day"))
            print(f"  [dry-run] '{class_name}': {len(rows)} levels, {has_spells} with spell slots (existing_rows={existing_levels})")
            continue

        if spells_only:
            # Only update spells_per_day on existing rows
            if existing_levels == 0:
                print(f"  [skip] '{class_name}': no existing progression rows to update")
                skipped += 1
                continue
            count = 0
            for r in rows:
                spd = r.get("spells_per_day")
                if spd:
                    cur.execute(
                        """UPDATE class_progression
                           SET spells_per_day = ?
                           WHERE class_id = ? AND level = ?""",
                        (json.dumps(spd), class_id, r["level"]),
                    )
                    count += cur.rowcount
            print(f"  '{class_name}': updated {count} spell-slot rows (hardcoded)")
        else:
            # Full INSERT OR REPLACE of progression rows
            count = 0
            for r in rows:
                spd = r.get("spells_per_day")
                cur.execute(
                    """INSERT OR REPLACE INTO class_progression
                       (class_id, level, bab, fort_save, ref_save, will_save, special, spells_per_day)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        class_id,
                        r["level"],
                        r.get("bab", 0),
                        r.get("fort_save", 0),
                        r.get("ref_save", 0),
                        r.get("will_save", 0),
                        r.get("special"),
                        json.dumps(spd) if spd else None,
                    ),
                )
                count += 1
            print(f"  '{class_name}': inserted/replaced {count} progression rows (psrd)")

        updated_classes += 1

    if not args.dry_run:
        conn.commit()
        print(f"\nDone. Updated {updated_classes} classes, skipped {skipped}.")
    else:
        print(f"\n[dry-run] Would update {len(to_import) - skipped} classes.")

    conn.close()


if __name__ == "__main__":
    main()
