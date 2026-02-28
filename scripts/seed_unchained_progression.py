#!/usr/bin/env python3
"""
Seed class_progression.special for Unchained classes (Pathfinder Unchained, 2015).

No PSRD book is available for Pathfinder Unchained, so this data is hardcoded
from the published book's class tables.

Run:  python scripts/seed_unchained_progression.py
      python scripts/seed_unchained_progression.py --overwrite
"""

from __future__ import annotations
import argparse
import pathlib
import sqlite3

ROOT    = pathlib.Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "pf1e.db"

# ── Progression tables (level → special text | None) ─────────────────────────
# Source: Pathfinder Unchained (Paizo, 2015)

UNCHAINED_BARBARIAN: dict[int, str | None] = {
    # Nearly identical to regular Barbarian (PU p.8).
    # Unchained rage grants typed bonuses to Str/Con rather than morale;
    # the class table Special column is otherwise the same.
    1:  "Fast movement, rage",
    2:  "Rage power, uncanny dodge",
    3:  "Trap sense +1",
    4:  "Rage power",
    5:  "Improved uncanny dodge",
    6:  "Rage power, trap sense +2",
    7:  "Damage reduction 1/—",
    8:  "Rage power",
    9:  "Trap sense +3",
    10: "Damage reduction 2/—, rage power",
    11: "Greater rage",
    12: "Rage power, trap sense +4",
    13: "Damage reduction 3/—",
    14: "Indomitable will, rage power",
    15: "Trap sense +5",
    16: "Damage reduction 4/—, rage power",
    17: "Tireless rage",
    18: "Rage power, trap sense +6",
    19: "Damage reduction 5/—",
    20: "Mighty rage, rage power",
}

UNCHAINED_MONK: dict[int, str | None] = {
    # PU p.14 — substantially redesigned from standard Monk.
    # Key additions: Ki pool at L2, Style Strikes, Ki Powers, Dedicated Adversary.
    1:  "Bonus feat, flurry of blows, stunning fist, unarmed strike",
    2:  "Bonus feat, evasion, ki pool, style strike",
    3:  "Dedicated adversary, maneuver training 1",
    4:  "Ki power, slow fall 20 ft., still mind, wholeness of body",
    5:  "Bonus feat, purity of body, style strike",
    6:  "Ki power, maneuver training 2, slow fall 30 ft.",
    7:  "Style strike",
    8:  "Ki power, slow fall 40 ft.",
    9:  "Bonus feat, improved evasion, maneuver training 3, style strike",
    10: "Ki power, slow fall 50 ft.",
    11: "Style strike",
    12: "Ki power, maneuver training 4, slow fall 60 ft.",
    13: "Bonus feat, style strike",
    14: "Ki power, slow fall 70 ft.",
    15: "Style strike, timeless body, tongue of the sun and moon",
    16: "Ki power, maneuver training 5, slow fall 80 ft.",
    17: "Bonus feat, style strike",
    18: "Ki power, slow fall 90 ft.",
    19: "Style strike",
    20: "Ki power, perfect self, slow fall any distance",
}

UNCHAINED_ROGUE: dict[int, str | None] = {
    # PU p.20 — key changes: Finesse Training, Danger Sense, Debilitating Injury,
    # Rogue's Edge (free skill unlock).
    1:  "Finesse training, sneak attack +1d6, trapfinding",
    2:  "Evasion, rogue talent",
    3:  "Danger sense +1, finesse training, sneak attack +2d6",
    4:  "Debilitating injury, rogue talent, uncanny dodge",
    5:  "Rogue's edge, sneak attack +3d6",
    6:  "Danger sense +2, rogue talent",
    7:  "Sneak attack +4d6",
    8:  "Improved uncanny dodge, rogue talent",
    9:  "Danger sense +3, sneak attack +5d6",
    10: "Advanced talents, rogue talent, rogue's edge",
    11: "Finesse training, sneak attack +6d6",
    12: "Danger sense +4, rogue talent",
    13: "Sneak attack +7d6",
    14: "Rogue talent",
    15: "Danger sense +5, rogue's edge, sneak attack +8d6",
    16: "Rogue talent",
    17: "Sneak attack +9d6",
    18: "Danger sense +6, rogue talent",
    19: "Finesse training, sneak attack +10d6",
    20: "Master strike, rogue talent, rogue's edge",
}

UNCHAINED_SUMMONER: dict[int, str | None] = {
    # PU p.24 — same class table as standard Summoner; key differences are the
    # eidolon's subtype system and a restricted spell list, neither of which
    # appear in the Special column.
    1:  "Cantrips, eidolon, life link, summon monster I",
    2:  "Bond senses",
    3:  "Summon monster II",
    4:  "Shield ally",
    5:  "Summon monster III",
    6:  "Maker's call",
    7:  "Summon monster IV",
    8:  "Transposition",
    9:  "Summon monster V",
    10: "Aspect",
    11: "Summon monster VI",
    12: "Greater shield ally",
    13: "Summon monster VII",
    14: "Life bond",
    15: "Summon monster VIII",
    16: "Merge forms",
    17: "Summon monster IX",
    18: "Greater aspect",
    19: "Gate",
    20: "Twin eidolon",
}

CLASSES: dict[str, dict[int, str | None]] = {
    "Unchained Barbarian": UNCHAINED_BARBARIAN,
    "Unchained Monk":      UNCHAINED_MONK,
    "Unchained Rogue":     UNCHAINED_ROGUE,
    "Unchained Summoner":  UNCHAINED_SUMMONER,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing non-NULL special values",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM classes")
    class_id_map = {r["name"]: r["id"] for r in cur.fetchall()}

    for class_name, progression in CLASSES.items():
        class_id = class_id_map.get(class_name)
        if not class_id:
            print(f"[skip] '{class_name}' not found in DB")
            continue

        updated = skipped = 0
        for level, special in sorted(progression.items()):
            if special is None:
                continue

            cur.execute(
                "SELECT id, special FROM class_progression WHERE class_id = ? AND level = ?",
                (class_id, level),
            )
            row = cur.fetchone()
            if not row:
                print(f"  [warn] {class_name} L{level}: no progression row")
                continue

            if row["special"] and not args.overwrite:
                skipped += 1
                continue

            cur.execute(
                "UPDATE class_progression SET special = ? WHERE id = ?",
                (special, row["id"]),
            )
            updated += 1

        conn.commit()
        print(f"{class_name}: updated {updated}, skipped {skipped}")

    conn.close()

    # Verify
    conn2 = sqlite3.connect(DB_PATH)
    conn2.row_factory = sqlite3.Row
    cur2 = conn2.cursor()
    print()
    for class_name in CLASSES:
        cid = class_id_map.get(class_name)
        if not cid:
            continue
        cur2.execute(
            "SELECT level, special FROM class_progression WHERE class_id = ? ORDER BY level",
            (cid,),
        )
        rows = cur2.fetchall()
        print(f"{class_name}:")
        for r in rows:
            print(f"  L{r['level']:2d}: {r['special']}")
    conn2.close()


if __name__ == "__main__":
    main()
