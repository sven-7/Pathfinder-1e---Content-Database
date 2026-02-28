#!/usr/bin/env python3
"""
Deep catalog of the CoreForge .xlsb — focused on rules-relevant sheets.
Reads more rows for key sheets.
"""

import sys
from pyxlsb import open_workbook

FILEPATH = "/Users/stephen/Documents/GitHub/Pathfinder 1e - Content Database/example_content/Pathfinder-sCoreForge-7.4.0.1.xlsb"

# Sheets we want to read exhaustively (up to 2000 rows each)
PRIORITY_SHEETS = {
    "Class Matrix", "Class Abilities", "Class Totals", "Class Tables",
    "Skill Matrix", "Feat Definitions", "Feats Lists",
    "Trait Definitions", "Trait List",
    "Races", "Race Traits", "Race Traits Tables",
    "Favored Class Data", "Custom Race", "Custom Class",
    "Race & Stats", "Level", "Traits", "Feats", "Skills",
    "Archetype Definitions", "Archetype Lists", "Archetype Matrix",
    "Bloodlines", "Bloodline Powers",
    "Oracle Mystery Curse", "Oracle Revelation",
    "Domains", "Domain Powers",
    "Ki Powers", "Discoveries", "Witch Hex",
    "Deed Definitions", "RogueTalents", "Ninja Tricks",
    "BarbarianRagePowers",
    "Cavalier Orders", "Order Abilities",
    "Wizard Schools", "School Powers",
    "Class Weapon List",
    "Source Tables", "Tables",
    "Special", "Drawback Definitions",
    "Mods", "Lists", "Lists Extra", "Lists Extra 2",
    "Animal Companion Data",
    "Arcana", "Judgement", "Eidolon Forms", "Evolutions",
    "Hunter Tricks", "Trapper Trap",
    "Divinity", "Bardic Performance",
    "Variant Channeling",
}

def cell_val(c):
    return c.v if c is not None else None

def row_values(row):
    return [cell_val(c) for c in row]

def read_sheet(wb, name, max_rows=2000):
    """Read up to max_rows from a sheet, return list of row-value lists."""
    try:
        with wb.get_sheet(name) as sheet:
            rows = []
            for i, row in enumerate(sheet.rows()):
                if i >= max_rows:
                    rows.append(["... TRUNCATED ..."])
                    break
                rows.append(row_values(row))
            return rows, None
    except Exception as e:
        return [], str(e)

def display_sheet(name, rows, error=None, full=False):
    print(f"\n{'='*70}")
    print(f"SHEET: {name}")
    print(f"{'='*70}")
    if error:
        print(f"  ERROR: {error}")
        return

    if not rows:
        print("  (empty)")
        return

    header = rows[0]
    data = rows[1:]
    non_empty = [r for r in data if any(v not in (None, "", 0, False) for v in r)]

    print(f"  Total rows read: {len(rows)}  |  Non-empty data rows: {len(non_empty)}")
    print(f"  Column count: {len(header)}")
    print(f"  Headers: {header}")

    if full:
        print(f"  ALL DATA ROWS:")
        for i, row in enumerate(data):
            if any(v not in (None, "", 0, False) for v in row):
                print(f"    [{i+1:4d}] {row}")
    else:
        limit = min(10, len(non_empty))
        print(f"  Sample data rows (first {limit} non-empty):")
        for i, row in enumerate(non_empty[:limit]):
            print(f"    [{i+1}] {row}")

def main():
    print(f"Opening: {FILEPATH}")

    with open_workbook(FILEPATH) as wb:
        all_sheets = wb.sheets
        print(f"\nTotal sheets: {len(all_sheets)}")
        print("All sheet names:")
        for i, s in enumerate(all_sheets):
            mark = " [PRIORITY]" if s in PRIORITY_SHEETS else ""
            print(f"  {i+1:3d}. {s}{mark}")

        print("\n\n" + "#"*80)
        print("# PRIORITY SHEETS — FULL DETAIL")
        print("#"*80)

        for name in all_sheets:
            if name not in PRIORITY_SHEETS:
                continue
            rows, err = read_sheet(wb, name, max_rows=2000)
            display_sheet(name, rows, err, full=False)

        print("\n\n" + "#"*80)
        print("# REMAINING SHEETS — BRIEF SUMMARY")
        print("#"*80)

        for name in all_sheets:
            if name in PRIORITY_SHEETS:
                continue
            rows, err = read_sheet(wb, name, max_rows=100)
            display_sheet(name, rows, err, full=False)

if __name__ == "__main__":
    main()
