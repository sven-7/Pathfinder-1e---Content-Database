#!/usr/bin/env python3
"""
Targeted deep-read of the most rules-relevant sheets in CoreForge.
Reads more rows and tries to find the true header row.
"""

import sys
from pyxlsb import open_workbook

FILEPATH = "/Users/stephen/Documents/GitHub/Pathfinder 1e - Content Database/example_content/Pathfinder-sCoreForge-7.4.0.1.xlsb"

def cell_val(c):
    return c.v if c is not None else None

def read_all_rows(wb, name, max_rows=500):
    try:
        with wb.get_sheet(name) as sheet:
            rows = []
            for i, row in enumerate(sheet.rows()):
                if i >= max_rows:
                    break
                rows.append([cell_val(c) for c in row])
            return rows, None
    except Exception as e:
        return [], str(e)

def find_header_row(rows, min_strings=3):
    """Find first row that has at least min_strings non-None string values."""
    for i, row in enumerate(rows):
        strings = [v for v in row if isinstance(v, str) and v.strip()]
        if len(strings) >= min_strings:
            return i
    return 0

def print_sheet(name, rows, error=None, show_rows=20, find_header=True):
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"SHEET: {name}")
    print(f"{sep}")
    if error:
        print(f"  ERROR: {error}")
        return
    if not rows:
        print("  (empty)")
        return

    hi = find_header_row(rows) if find_header else 0
    header = rows[hi]
    data = rows[hi+1:]
    non_empty = [r for r in data if any(v not in (None, "", 0, False) for v in r)]

    print(f"  Total rows: {len(rows)}  |  Header at row index: {hi}  |  Non-empty data: {len(non_empty)}")
    print(f"  Column count: {len(header)}")
    print(f"  Header row: {header}")
    print(f"  Non-empty data rows (up to {show_rows}):")
    for j, row in enumerate(non_empty[:show_rows]):
        print(f"    [{j+1:3d}] {row}")

def main():
    with open_workbook(FILEPATH) as wb:

        # ----------------------------------------------------------------
        # CLASS TABLES — full class list with types and sources
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Class Tables", 300)
        print_sheet("Class Tables", rows, err, show_rows=80)

        # ----------------------------------------------------------------
        # CLASS ABILITIES — every class feature at every level
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Class Abilities", 100)
        print_sheet("Class Abilities", rows, err, show_rows=30)

        # ----------------------------------------------------------------
        # SKILL MATRIX — skills and which classes have them as class skills
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Skill Matrix", 250)
        print_sheet("Skill Matrix", rows, err, show_rows=50)

        # ----------------------------------------------------------------
        # CLASS TOTALS — BAB/save/spell lookup table
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Class Totals", 200)
        print_sheet("Class Totals", rows, err, show_rows=50, find_header=False)

        # ----------------------------------------------------------------
        # FEAT DEFINITIONS — complete feat list
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Feat Definitions", 400)
        print_sheet("Feat Definitions", rows, err, show_rows=30)

        # ----------------------------------------------------------------
        # RACES — racial data
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Races", 100)
        print_sheet("Races", rows, err, show_rows=30, find_header=False)

        # ----------------------------------------------------------------
        # RACE & STATS — point buy and ability scores
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Race & Stats", 100)
        print_sheet("Race & Stats", rows, err, show_rows=50)

        # ----------------------------------------------------------------
        # LEVEL — character level progression
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Level", 100)
        print_sheet("Level", rows, err, show_rows=50)

        # ----------------------------------------------------------------
        # SKILLS (character sheet skills)
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Skills", 150)
        print_sheet("Skills", rows, err, show_rows=50)

        # ----------------------------------------------------------------
        # TRAITS (character sheet)
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Traits", 100)
        print_sheet("Traits", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # FEATS (character sheet)
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Feats", 100)
        print_sheet("Feats", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # TRAIT DEFINITIONS
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Trait Definitions", 400)
        print_sheet("Trait Definitions", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # ARCHETYPE DEFINITIONS
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Archetype Definitions", 400)
        print_sheet("Archetype Definitions", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # ARCHETYPE LISTS
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Archetype Lists", 400)
        print_sheet("Archetype Lists", rows, err, show_rows=30)

        # ----------------------------------------------------------------
        # ARCHETYPE MATRIX
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Archetype Matrix", 400)
        print_sheet("Archetype Matrix", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # RACE TRAITS
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Race Traits", 400)
        print_sheet("Race Traits", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # RACE TRAITS TABLES
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Race Traits Tables", 200)
        print_sheet("Race Traits Tables", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # FAVORED CLASS DATA
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Favored Class Data", 400)
        print_sheet("Favored Class Data", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # TABLES — misc lookup tables
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Tables", 300)
        print_sheet("Tables", rows, err, show_rows=40)

        # ----------------------------------------------------------------
        # SOURCE TABLES — source book info
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Source Tables", 200)
        print_sheet("Source Tables", rows, err, show_rows=40)

        # ----------------------------------------------------------------
        # LISTS — dropdown lists
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Lists", 400)
        print_sheet("Lists", rows, err, show_rows=40)

        # ----------------------------------------------------------------
        # LISTS EXTRA
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Lists Extra", 400)
        print_sheet("Lists Extra", rows, err, show_rows=40)

        # ----------------------------------------------------------------
        # LISTS EXTRA 2
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Lists Extra 2", 400)
        print_sheet("Lists Extra 2", rows, err, show_rows=40)

        # ----------------------------------------------------------------
        # BLOODLINES
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Bloodlines", 200)
        print_sheet("Bloodlines", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # CLASS MATRIX — BAB/save lookup by type
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Class Matrix", 100)
        print_sheet("Class Matrix", rows, err, show_rows=40, find_header=False)

        # ----------------------------------------------------------------
        # DOMAINS
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Domains", 200)
        print_sheet("Domains", rows, err, show_rows=20)

        # ----------------------------------------------------------------
        # MODS — modifier types
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Mods", 200)
        print_sheet("Mods", rows, err, show_rows=40)

        # ----------------------------------------------------------------
        # SPECIAL
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Special", 200)
        print_sheet("Special", rows, err, show_rows=30)

        # ----------------------------------------------------------------
        # DIVINITY
        # ----------------------------------------------------------------
        rows, err = read_all_rows(wb, "Divinity", 200)
        print_sheet("Divinity", rows, err, show_rows=20)

if __name__ == "__main__":
    main()
