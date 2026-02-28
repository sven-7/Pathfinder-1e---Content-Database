"""One-time script: populate classes.hit_die for all classes in db/pf1e.db.

Uses the authoritative CLASS_HIT_DIE dict from builder.py.
Safe to re-run — uses INSERT OR REPLACE logic via UPDATE.
"""

import pathlib
import sqlite3

DB_PATH = pathlib.Path(__file__).parent.parent / "db" / "pf1e.db"

# Authoritative hit-die mapping (mirrors builder.py CLASS_HIT_DIE)
CLASS_HIT_DIE: dict[str, str] = {
    "Barbarian": "d12", "Unchained Barbarian": "d12",
    "Bard": "d8",
    "Cleric": "d8",
    "Druid": "d8",
    "Fighter": "d10",
    "Monk": "d8", "Unchained Monk": "d10",
    "Paladin": "d10", "Antipaladin": "d10",
    "Ranger": "d10",
    "Rogue": "d8", "Unchained Rogue": "d8",
    "Sorcerer": "d6",
    "Wizard": "d6",
    # APG
    "Alchemist": "d8",
    "Cavalier": "d10",
    "Gunslinger": "d10",
    "Inquisitor": "d8",
    "Magus": "d8",
    "Oracle": "d8",
    "Summoner": "d8", "Unchained Summoner": "d8",
    "Witch": "d6",
    # ACG
    "Arcanist": "d6",
    "Bloodrager": "d10",
    "Brawler": "d10",
    "Hunter": "d8",
    "Investigator": "d8",
    "Shaman": "d8",
    "Skald": "d8",
    "Slayer": "d10",
    "Swashbuckler": "d10",
    "Warpriest": "d8",
    # OA
    "Kineticist": "d8",
    "Medium": "d8",
    "Mesmerist": "d8",
    "Occultist": "d8",
    "Psychic": "d6",
    "Spiritualist": "d8",
    # Misc
    "Ninja": "d8",
    "Samurai": "d10",
    "Vigilante": "d8",
    "Shifter": "d10",
    "Omdura": "d8",
    # NPC classes
    "Aristocrat": "d8",
    "Commoner": "d6",
    "Expert": "d8",
    "Warrior": "d10",
    "Adept": "d6",
}


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    updated = 0
    skipped = 0

    for class_name, hit_die in CLASS_HIT_DIE.items():
        cur.execute(
            "UPDATE classes SET hit_die = ? WHERE name = ? AND (hit_die IS NULL OR hit_die = '')",
            (hit_die, class_name),
        )
        if cur.rowcount:
            updated += 1
            print(f"  SET {class_name} → {hit_die}")
        else:
            skipped += 1

    conn.commit()
    conn.close()
    print(f"\nDone: {updated} updated, {skipped} already set or not found.")


if __name__ == "__main__":
    main()
