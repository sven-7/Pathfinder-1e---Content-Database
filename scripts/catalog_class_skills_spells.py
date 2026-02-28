#!/usr/bin/env python3
"""
Extract class skills by class and spell slot data from CoreForge.
The class skills are embedded in the Archetype Definitions sheet col 14
(as a comma-separated string for each class's "base" archetype).
The spell slot data is in Class Matrix (rows 23-31+).
Also look at the Class Totals sheet for spell data.
"""

from pyxlsb import open_workbook

FILEPATH = "/Users/stephen/Documents/GitHub/Pathfinder 1e - Content Database/example_content/Pathfinder-sCoreForge-7.4.0.1.xlsb"

def cv(c): return c.v if c is not None else None
def read_rows(wb, name, limit=2000):
    try:
        with wb.get_sheet(name) as sh:
            out = []
            for i, row in enumerate(sh.rows()):
                if i >= limit: break
                out.append([cv(c) for c in row])
            return out, None
    except Exception as e:
        return [], str(e)

def non_empty(row):
    return any(v not in (None, "", 0, False) for v in row)

with open_workbook(FILEPATH) as wb:

    print("="*80)
    print("CLASS SKILLS — from Archetype Definitions (col 14 for base-class rows)")
    print("="*80)
    data, _ = read_rows(wb, "Archetype Definitions", 2000)
    # Row 0 = blank, row 1 = header
    # col 1 = Base Class, col 2 = Archetype, col 3 = Class Type
    # col 14 = Class Skills (text), col 5 = Skill Points, col 4 = Hit Die
    for row in data[2:]:
        if len(row) < 18:
            continue
        base_class = row[1]
        archetype  = row[2]
        class_type = row[3]
        hit_die    = row[4]
        skill_pts  = row[5]
        fort       = row[8]
        ref        = row[9]
        will       = row[10]
        bab        = row[11]
        spells     = row[12]
        stat       = row[13]
        class_skills = row[14]
        source     = row[17]
        # Only print "base" archetype rows (same name as class)
        if base_class == archetype:
            print(f"\nClass: {base_class}")
            print(f"  Hit Die: {hit_die}  Skill Pts/Lvl: {skill_pts}")
            print(f"  BAB type: {bab}  Fort: {fort}  Ref: {ref}  Will: {will}")
            print(f"  Spells: {spells}  Stat: {stat}  Source: {source}")
            if class_skills:
                print(f"  Class Skills: {class_skills}")

    print("\n\n" + "="*80)
    print("SPELL SLOT TABLES — from Class Matrix (rows for spell types)")
    print("="*80)
    data, _ = read_rows(wb, "Class Matrix", 100)
    # The spell slot tables are labelled rows, starting around row 22
    # They show spell slots by level for each spell progression type
    in_spells = False
    for row in data:
        if len(row) < 8: continue
        label = row[2]
        if isinstance(label, str) and ('Caster' in label or 'Arcane' in label
                                        or 'Divine' in label or 'Spells' in label
                                        or 'spell' in label.lower()):
            in_spells = True
        if in_spells and non_empty(row):
            print(f"  label={row[2]!r:30s}  formula={row[4]!r:30s}  L1-10: {row[7:17]}")

    print("\n\n" + "="*80)
    print("SPELL SLOT DETAILED — Class Totals sheet (spell progression rows)")
    print("="*80)
    data, _ = read_rows(wb, "Class Totals", 300)
    # This is a massive lookup table. Find rows with spell-related labels.
    for i, row in enumerate(data):
        if len(row) < 5: continue
        # Scan for cells that mention spell slots
        for j, v in enumerate(row[:35]):
            if isinstance(v, str) and any(w in v.lower() for w in ['spell', 'slot', 'cast', 'caster']):
                print(f"  row {i:3d} col {j}: {v!r}  ->  {row[:35]}")
                break

    print("\n\n" + "="*80)
    print("SPELL SLOT FROM CLASS MATRIX — All labelled rows with level data")
    print("="*80)
    data, _ = read_rows(wb, "Class Matrix", 100)
    for i, row in enumerate(data):
        if not non_empty(row): continue
        label = row[2]
        formula = row[4]
        # Show ALL labelled rows
        if isinstance(label, str) and label.strip():
            vals_1_20 = row[7:27]
            print(f"  [{i:2d}] {label!r:35s}  formula={formula!r:35s}  values: {vals_1_20}")

    print("\n\n" + "="*80)
    print("ARCHETYPE LISTS — Class to archetype mapping (all rows)")
    print("="*80)
    data, _ = read_rows(wb, "Archetype Lists", 2000)
    # Print header
    if data:
        print("Header:", data[0])
    # All data
    count = 0
    for row in data[1:]:
        if non_empty(row) and count < 100:
            print(f"  {row}")
            count += 1

    print("\n\n" + "="*80)
    print("RACES — Full race data (all rows, first 40 cols)")
    print("="*80)
    data, _ = read_rows(wb, "Races", 100)
    for i, row in enumerate(data):
        if non_empty(row):
            print(f"  row {i:2d}: {row[:40]}")
