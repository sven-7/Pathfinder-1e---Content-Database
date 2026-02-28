"""Phase 6 — Seed weapons and armor tables with CRB mundane stats.

Sources: Pathfinder Core Rulebook / d20pfsrd.com
Links to existing equipment rows via MIN(id) per name.
Inserts new equipment rows only if name is missing.

Usage:
  python scripts/seed_weapons_armor.py
  python scripts/seed_weapons_armor.py --dry-run
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path("db/pf1e.db")

# ---------------------------------------------------------------------------
# Weapon data tuples:
#   (name, proficiency, weapon_type, handedness,
#    damage_small, damage_medium, critical, range_increment, damage_type, special)
#
# DB constraints (all lowercase):
#   proficiency IN ('simple', 'martial', 'exotic')
#   weapon_type IN ('melee', 'ranged', 'ammunition')
#   handedness  IN ('light', 'one-handed', 'two-handed')  — NULL for ranged/ammo
# ---------------------------------------------------------------------------
WEAPONS: list[tuple] = [
    # ── Simple Melee ──────────────────────────────────────────────────────────
    #  name                   prof      type    hand           dmgS    dmgM    crit           range    dtype    special
    ("Unarmed Strike",       "simple", "melee", "light",       "1d2",  "1d3",  "×2",          "",      "B",     "nonlethal"),
    ("Dagger",               "simple", "melee", "light",       "1d3",  "1d4",  "19–20/×2",   "10 ft.", "P/S",   ""),
    ("Dagger, Punching",     "simple", "melee", "light",       "1d3",  "1d4",  "×3",          "",      "P",     ""),
    ("Gauntlet",             "simple", "melee", "light",       "1d2",  "1d3",  "×2",          "",      "B",     ""),
    ("Spiked Gauntlet",      "simple", "melee", "light",       "1d3",  "1d4",  "×2",          "",      "P",     ""),
    ("Light Mace",           "simple", "melee", "light",       "1d4",  "1d6",  "×2",          "",      "B",     ""),
    ("Sickle",               "simple", "melee", "light",       "1d4",  "1d6",  "×2",          "",      "S",     "trip"),
    ("Club",                 "simple", "melee", "one-handed",  "1d4",  "1d6",  "×2",          "10 ft.","B",     ""),
    ("Heavy Mace",           "simple", "melee", "one-handed",  "1d6",  "1d8",  "×2",          "",      "B",     ""),
    ("Morningstar",          "simple", "melee", "one-handed",  "1d6",  "1d8",  "×2",          "",      "B/P",   ""),
    ("Shortspear",           "simple", "melee", "one-handed",  "1d4",  "1d6",  "×2",          "20 ft.","P",     ""),
    ("Longspear",            "simple", "melee", "two-handed",  "1d6",  "1d8",  "×3",          "",      "P",     "brace, reach"),
    ("Quarterstaff",         "simple", "melee", "two-handed",  "1d4/1d4","1d6/1d6","×2",     "",      "B",     "double, monk"),
    ("Spear",                "simple", "melee", "two-handed",  "1d6",  "1d8",  "×3",          "20 ft.","P",     "brace"),
    # ── Simple Ranged ────────────────────────────────────────────────────────
    ("Blowgun",              "simple", "ranged", None,         "1d2",  "1d3",  "×2",          "20 ft.","P",     ""),
    ("Crossbow, Light",      "simple", "ranged", None,         "1d6",  "1d8",  "19–20/×2",   "80 ft.","P",     ""),
    ("Crossbow, Heavy",      "simple", "ranged", None,         "1d8",  "1d10", "19–20/×2",  "120 ft.","P",     ""),
    ("Dart",                 "simple", "ranged", None,         "1d3",  "1d4",  "×2",          "20 ft.","P",     ""),
    ("Javelin",              "simple", "ranged", None,         "1d4",  "1d6",  "×2",          "30 ft.","P",     ""),
    ("Sling",                "simple", "ranged", None,         "1d3",  "1d4",  "×2",          "50 ft.","B",     ""),
    # ── Martial Melee ────────────────────────────────────────────────────────
    ("Handaxe",              "martial","melee", "light",       "1d4",  "1d6",  "×3",          "",      "S",     ""),
    ("Kukri",                "martial","melee", "light",       "1d3",  "1d4",  "18–20/×2",   "",      "S",     ""),
    ("Light Hammer",         "martial","melee", "light",       "1d3",  "1d4",  "×2",          "20 ft.","B",     ""),
    ("Light Pick",           "martial","melee", "light",       "1d3",  "1d4",  "×4",          "",      "P",     ""),
    ("Shortsword",           "martial","melee", "light",       "1d4",  "1d6",  "19–20/×2",   "",      "P/S",   ""),
    ("Sap",                  "martial","melee", "light",       "1d4",  "1d6",  "×2",          "",      "B",     "nonlethal"),
    ("Starknife",            "martial","melee", "light",       "1d3",  "1d4",  "×3",          "20 ft.","P",     ""),
    ("Battleaxe",            "martial","melee", "one-handed",  "1d6",  "1d8",  "×3",          "",      "S",     ""),
    ("Flail",                "martial","melee", "one-handed",  "1d6",  "1d8",  "×2",          "",      "B",     "disarm, trip"),
    ("Heavy Pick",           "martial","melee", "one-handed",  "1d4",  "1d6",  "×4",          "",      "P",     ""),
    ("Longsword",            "martial","melee", "one-handed",  "1d6",  "1d8",  "19–20/×2",   "",      "S",     ""),
    ("Rapier",               "martial","melee", "one-handed",  "1d4",  "1d6",  "18–20/×2",   "",      "P",     "finesse"),
    ("Scimitar",             "martial","melee", "one-handed",  "1d4",  "1d6",  "18–20/×2",   "",      "S",     ""),
    ("Trident",              "martial","melee", "one-handed",  "1d6",  "1d8",  "×2",          "10 ft.","P",     "brace"),
    ("Warhammer",            "martial","melee", "one-handed",  "1d6",  "1d8",  "×3",          "",      "B",     ""),
    ("Falchion",             "martial","melee", "two-handed",  "1d6",  "2d4",  "18–20/×2",   "",      "S",     ""),
    ("Glaive",               "martial","melee", "two-handed",  "1d8",  "1d10", "×3",          "",      "S",     "reach"),
    ("Greataxe",             "martial","melee", "two-handed",  "1d10", "1d12", "×3",          "",      "S",     ""),
    ("Greatclub",            "martial","melee", "two-handed",  "1d8",  "1d10", "×2",          "",      "B",     ""),
    ("Greatsword",           "martial","melee", "two-handed",  "1d10", "2d6",  "19–20/×2",   "",      "S",     ""),
    ("Guisarme",             "martial","melee", "two-handed",  "1d6",  "2d4",  "×3",          "",      "S",     "reach, trip"),
    ("Halberd",              "martial","melee", "two-handed",  "1d8",  "1d10", "×3",          "",      "P/S",   "brace, trip"),
    ("Heavy Flail",          "martial","melee", "two-handed",  "1d8",  "1d10", "19–20/×2",   "",      "B",     "disarm, trip"),
    ("Lance",                "martial","melee", "two-handed",  "1d6",  "1d8",  "×3",          "",      "P",     "reach"),
    ("Ranseur",              "martial","melee", "two-handed",  "1d6",  "2d4",  "×3",          "",      "P",     "disarm, reach"),
    ("Scythe",               "martial","melee", "two-handed",  "1d6",  "2d4",  "×4",          "",      "P/S",   "trip"),
    # ── Martial Ranged ───────────────────────────────────────────────────────
    ("Longbow",              "martial","ranged", None,         "1d6",  "1d8",  "×3",          "100 ft.","P",    ""),
    ("Longbow, Composite",   "martial","ranged", None,         "1d6",  "1d8",  "×3",          "110 ft.","P",    ""),
    ("Shortbow",             "martial","ranged", None,         "1d4",  "1d6",  "×3",          "60 ft.", "P",    ""),
    ("Shortbow, Composite",  "martial","ranged", None,         "1d4",  "1d6",  "×3",          "70 ft.", "P",    ""),
    ("Bolas",                "martial","ranged", None,         "1d3",  "1d4",  "×2",          "10 ft.", "B",    "trip"),
    ("Net",                  "martial","ranged", None,         "",     "",     "—",            "10 ft.", "—",    "entangle"),
    # ── Exotic Melee ─────────────────────────────────────────────────────────
    ("Bastard Sword",        "exotic", "melee", "one-handed",  "1d8",  "1d10", "19–20/×2",   "",      "S",     ""),
    ("Dwarven Waraxe",       "exotic", "melee", "one-handed",  "1d8",  "1d10", "×3",          "",      "S",     ""),
    ("Whip",                 "exotic", "melee", "one-handed",  "1d2",  "1d3",  "×2",          "15 ft.","S",     "disarm, nonlethal, reach, trip"),
    ("Curve Blade, Elven",   "exotic", "melee", "two-handed",  "1d8",  "1d10", "18–20/×2",   "",      "S",     "finesse"),
    ("Axe, Orc Double",      "exotic", "melee", "two-handed",  "1d6/1d6","1d8/1d8","×3",     "",      "S",     "double"),
    ("Dire Flail",           "exotic", "melee", "two-handed",  "1d6/1d6","1d8/1d8","×2",     "",      "B",     "disarm, double, trip"),
    ("Two-Bladed Sword",     "exotic", "melee", "two-handed",  "1d6/1d6","1d8/1d8","19–20/×2","",     "S",     "double"),
    ("Dwarven Urgrosh",      "exotic", "melee", "two-handed",  "1d6/1d4","1d8/1d6","×3",     "",      "P/S",   "brace, double"),
    ("Spiked Chain",         "exotic", "melee", "two-handed",  "1d6",  "2d4",  "×2",          "",      "P",     "disarm, reach, trip"),
    ("Chain, Spiked",        "exotic", "melee", "two-handed",  "1d6",  "2d4",  "×2",          "",      "P",     "disarm, reach, trip"),
    ("Kama",                 "exotic", "melee", "light",       "1d4",  "1d6",  "×2",          "",      "S",     "monk, trip"),
    ("Nunchaku",             "exotic", "melee", "light",       "1d4",  "1d6",  "×2",          "",      "B",     "disarm, monk"),
    ("Sai",                  "exotic", "melee", "light",       "1d3",  "1d4",  "×2",          "",      "B",     "disarm, monk"),
    ("Siangham",             "exotic", "melee", "light",       "1d4",  "1d6",  "×2",          "",      "P",     "monk"),
    # ── Exotic Ranged ────────────────────────────────────────────────────────
    ("Crossbow, Hand",       "exotic", "ranged", None,         "1d3",  "1d4",  "19–20/×2",   "30 ft.","P",     ""),
    ("Crossbow, Repeating Light","exotic","ranged",None,       "1d6",  "1d8",  "19–20/×2",   "80 ft.","P",     ""),
    ("Crossbow, Repeating Heavy","exotic","ranged",None,       "1d8",  "1d10", "19–20/×2",  "120 ft.","P",     ""),
    ("Shuriken",             "exotic", "ranged", None,         "1",    "1",    "×2",           "10 ft.","P",    "monk"),
    # ── Ammunition ───────────────────────────────────────────────────────────
    ("Arrows",               "simple", "ammunition", None,    "",     "",     "—",            "",      "",      "20/bundle"),
    ("Bolts",                "simple", "ammunition", None,    "",     "",     "—",            "",      "",      "10/bundle"),
    ("Bullets, Sling",       "simple", "ammunition", None,    "",     "",     "—",            "",      "",      "10/bundle"),
    ("Blowgun Darts",        "simple", "ammunition", None,    "",     "",     "—",            "",      "",      "10/bundle"),
]

# ---------------------------------------------------------------------------
# Armor data: (name, armor_type, armor_bonus, max_dex, acp, asf, speed_30, speed_20)
# armor_type DB constraint: ('light', 'medium', 'heavy', 'shield')
# max_dex: None = no limit stored as NULL
# acp: stored as negative integer (penalty)
# asf: arcane spell failure %
# ---------------------------------------------------------------------------
ARMOR: list[tuple] = [
    # Light Armor                   type     AB  MaxDex ACP   ASF   s30       s20
    ("Padded",           "light",    1,  8,   0,    5,   "30 ft.", "20 ft."),
    ("Leather",          "light",    2,  6,   0,   10,   "30 ft.", "20 ft."),
    ("Studded Leather",  "light",    3,  5,  -1,   15,   "30 ft.", "20 ft."),
    ("Chain Shirt",      "light",    4,  4,  -2,   20,   "30 ft.", "20 ft."),
    # Medium Armor
    ("Hide",             "medium",   3,  4,  -3,   20,   "20 ft.", "15 ft."),
    ("Scale Mail",       "medium",   4,  3,  -4,   25,   "20 ft.", "15 ft."),
    ("Chainmail",        "medium",   5,  2,  -5,   30,   "20 ft.", "15 ft."),
    ("Breastplate",      "medium",   6,  3,  -4,   25,   "20 ft.", "15 ft."),
    # Heavy Armor
    ("Splint Mail",      "heavy",    6,  0,  -7,   40,   "20 ft.", "15 ft."),
    ("Banded Mail",      "heavy",    6,  1,  -6,   35,   "20 ft.", "15 ft."),
    ("Half-Plate",       "heavy",    7,  0,  -7,   40,   "20 ft.", "15 ft."),
    ("Full Plate",       "heavy",    8,  1,  -6,   35,   "20 ft.", "15 ft."),
    # Shields (no speed penalty; ACP applies to attack rolls for non-proficient)
    ("Buckler",              "shield",1, None,-1,   5,   "—",      "—"),
    ("Light Wooden Shield",  "shield",1, None,-1,   5,   "—",      "—"),
    ("Light Steel Shield",   "shield",1, None,-1,   5,   "—",      "—"),
    ("Heavy Wooden Shield",  "shield",2, None,-2,  15,   "—",      "—"),
    ("Heavy Steel Shield",   "shield",2, None,-2,  15,   "—",      "—"),
    ("Tower Shield",         "shield",4,  2, -10,  50,   "—",      "—"),
    # Additional APG/UC light armor
    ("Armored Coat",     "medium",   4,  3,  -2,   20,   "20 ft.", "15 ft."),
    ("Haramaki",         "light",    1,  None, 0,    0,  "30 ft.", "20 ft."),
    ("Silken Ceremonial Armor","light",1, None, 0,   0,  "30 ft.", "20 ft."),
    ("Do-Maru",          "medium",   5,  4,  -4,   25,   "20 ft.", "15 ft."),
    ("Kikko",            "medium",   5,  4,  -3,   20,   "20 ft.", "15 ft."),
    ("Tatami-Do",        "heavy",    7,  2,  -5,   35,   "20 ft.", "15 ft."),
    ("O-Yoroi",          "heavy",    8,  2,  -6,   35,   "20 ft.", "15 ft."),
    ("Kusari Gusoku",    "heavy",    7,  1,  -8,   35,   "20 ft.", "15 ft."),
    ("Lamellar Leather", "light",    4,  3,  -2,    0,   "30 ft.", "20 ft."),
    ("Four-Mirror",      "medium",   6,  2,  -5,   30,   "20 ft.", "15 ft."),
]


def _find_equipment_id(cur: sqlite3.Cursor, name: str) -> int | None:
    """Return MIN(id) from equipment where name matches (case-insensitive)."""
    cur.execute(
        "SELECT MIN(id) FROM equipment WHERE LOWER(name) = LOWER(?)",
        (name,),
    )
    row = cur.fetchone()
    return row[0] if row and row[0] is not None else None


def seed_weapons(conn: sqlite3.Connection, dry_run: bool = False) -> tuple[int, int]:
    cur = conn.cursor()
    if not dry_run:
        cur.execute("DELETE FROM weapons")

    inserted = 0
    skipped = 0
    seen_names: set[str] = set()

    for row in WEAPONS:
        (name, proficiency, wtype, handedness,
         dmg_s, dmg_m, crit, rng, dtype, special) = row

        if name in seen_names:
            skipped += 1
            continue
        seen_names.add(name)

        if not dry_run:
            eid = _find_equipment_id(cur, name)
            if eid is None:
                cur.execute(
                    "INSERT INTO equipment (name, equipment_type) VALUES (?,?)",
                    (name, "weapon"),
                )
                eid = cur.lastrowid
            else:
                cur.execute(
                    "UPDATE equipment SET equipment_type = 'weapon' WHERE id = ?", (eid,)
                )
            cur.execute(
                """INSERT INTO weapons
                   (equipment_id, proficiency, weapon_type, handedness,
                    damage_small, damage_medium, critical, range_increment,
                    damage_type, special)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (eid, proficiency, wtype, handedness,
                 dmg_s, dmg_m, crit, rng, dtype, special),
            )
        inserted += 1

    return inserted, skipped


def seed_armor(conn: sqlite3.Connection, dry_run: bool = False) -> tuple[int, int]:
    cur = conn.cursor()
    if not dry_run:
        cur.execute("DELETE FROM armor")

    inserted = 0

    for row in ARMOR:
        (name, atype, ab, max_dex, acp, asf, s30, s20) = row

        if not dry_run:
            eid = _find_equipment_id(cur, name)
            if eid is None:
                cur.execute(
                    "INSERT INTO equipment (name, equipment_type) VALUES (?,?)",
                    (name, "armor"),
                )
                eid = cur.lastrowid
            else:
                cur.execute(
                    "UPDATE equipment SET equipment_type = 'armor' WHERE id = ?", (eid,)
                )
            cur.execute(
                """INSERT INTO armor
                   (equipment_id, armor_type, armor_bonus, max_dex,
                    armor_check_penalty, arcane_spell_failure, speed_30, speed_20)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (eid, atype, ab, max_dex, acp, asf, s30, s20),
            )
        inserted += 1

    return inserted, 0


def print_summary(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    print("\n  Weapon proficiency distribution:")
    cur.execute("SELECT proficiency, COUNT(*) FROM weapons GROUP BY proficiency ORDER BY COUNT(*) DESC")
    for r in cur.fetchall():
        print(f"    {r[0]:12s} {r[1]:>4}")

    print("\n  Weapon type distribution:")
    cur.execute("SELECT weapon_type, COUNT(*) FROM weapons GROUP BY weapon_type ORDER BY COUNT(*) DESC")
    for r in cur.fetchall():
        print(f"    {r[0]:12s} {r[1]:>4}")

    print("\n  Armor type distribution:")
    cur.execute("SELECT armor_type, COUNT(*) FROM armor GROUP BY armor_type ORDER BY COUNT(*) DESC")
    for r in cur.fetchall():
        print(f"    {r[0]:10s} {r[1]:>4}")

    print("\n  Sample weapons (martial melee one-handed):")
    cur.execute("""
        SELECT e.name, w.damage_medium, w.critical, w.damage_type
        FROM weapons w JOIN equipment e ON e.id = w.equipment_id
        WHERE w.proficiency = 'martial' AND w.handedness = 'one-handed'
        ORDER BY e.name LIMIT 8
    """)
    for r in cur.fetchall():
        print(f"    {r[0]:22s}  {r[1]:10s}  {r[2]:14s}  {r[3]}")

    print("\n  Sample armor (heavy):")
    cur.execute("""
        SELECT e.name, a.armor_bonus, a.max_dex, a.armor_check_penalty, a.arcane_spell_failure
        FROM armor a JOIN equipment e ON e.id = a.equipment_id
        WHERE a.armor_type = 'heavy'
        ORDER BY a.armor_bonus
    """)
    for r in cur.fetchall():
        print(f"    {r[0]:22s}  AC+{r[1]}  MaxDex {r[2]}  ACP {r[3]:+d}  ASF {r[4]}%")


def main(dry_run: bool = False) -> None:
    print("Phase 6 — Seed weapons and armor tables")
    if dry_run:
        print("  (DRY RUN — no DB changes)")

    conn = sqlite3.connect(DB_PATH)

    print(f"\n  Seeding {len(WEAPONS)} weapon entries (deduped by name)...")
    w_inserted, w_skipped = seed_weapons(conn, dry_run=dry_run)
    print(f"    Inserted: {w_inserted}  Skipped (duplicates): {w_skipped}")

    print(f"\n  Seeding {len(ARMOR)} armor entries...")
    a_inserted, _ = seed_armor(conn, dry_run=dry_run)
    print(f"    Inserted: {a_inserted}")

    if not dry_run:
        conn.commit()
        print_summary(conn)

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
