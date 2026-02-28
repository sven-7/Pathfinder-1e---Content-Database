#!/usr/bin/env python3
"""
Extract the most rules-critical data from CoreForge for DB comparison.
Focus: class skills, spell slots, class list, race ability mods, point buy.
"""

from pyxlsb import open_workbook

FILEPATH = "/Users/stephen/Documents/GitHub/Pathfinder 1e - Content Database/example_content/Pathfinder-sCoreForge-7.4.0.1.xlsb"

def cv(c): return c.v if c is not None else None
def rows(wb, name, limit=2000):
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

def divider(title):
    print(f"\n\n{'#'*80}")
    print(f"# {title}")
    print(f"{'#'*80}")

with open_workbook(FILEPATH) as wb:

    # =========================================================================
    # 1. CLASS TABLES — complete class list
    # =========================================================================
    divider("CLASS TABLES — Complete class list with types")
    data, _ = rows(wb, "Class Tables")
    # Header is row 0 (all None), first data row has structure:
    # [idx, ?, ?, ?, fulllist, ..., class_name(col24), class_type(col25), source(col26), ...]
    print("Column mapping (0-indexed):")
    print("  col 0  = row index")
    print("  col 24 = Class Name")
    print("  col 25 = Class Type (Base/Prestige/Category)")
    print("  col 26 = Source book")
    print("\nAll classes (Base type only):")
    for row in data[1:]:
        if len(row) > 26 and row[25] == 'Base':
            print(f"  {row[24]!r:40s} type={row[25]!r} src={row[26]!r}")
    print("\nAll class categories and prestige classes (first 20):")
    count = 0
    for row in data[1:]:
        if len(row) > 26 and row[25] in ('Prestige', 'Category'):
            print(f"  {row[24]!r:40s} type={row[25]!r} src={row[26]!r}")
            count += 1
            if count >= 20:
                print("  ... (truncated)")
                break

    # =========================================================================
    # 2. SKILL MATRIX — class skills
    # =========================================================================
    divider("SKILL MATRIX — Skills and their class-skill designations")
    data, _ = rows(wb, "Skill Matrix")
    # Row 0 is header, row 1 is actual field names
    header = data[0]
    field_names = data[1] if len(data) > 1 else []
    print("True headers (row 1):")
    for i, v in enumerate(header):
        if v is not None:
            print(f"  col {i:2d}: {v!r}")
    print("\nAll skill entries (skill name, key ability, untrained, class col refs):")
    # data rows start at index 2
    seen_skills = set()
    for row in data[2:]:
        if len(row) < 12 or not non_empty(row):
            continue
        skill = row[2]
        cond  = row[3]
        acp   = row[5]
        key   = row[7]
        untrained = row[10]
        class_mod = row[33]  # 'Class' modifier reference
        if skill and isinstance(skill, str) and skill not in seen_skills:
            seen_skills.add(skill)
            print(f"  {skill!r:30s}  key={key!r:4s}  untrained={untrained!r}  ACP={acp!r}  class_mod_ref={class_mod!r}")

    # =========================================================================
    # 3. CLASS MATRIX — BAB / Save / Spell lookup tables
    # =========================================================================
    divider("CLASS MATRIX — BAB, Save, Spell progression formulas")
    data, _ = rows(wb, "Class Matrix", 50)
    print("Row format: [label, formula, values at levels 1-20]")
    for row in data:
        if not non_empty(row): continue
        label = row[2]
        formula = row[4]
        vals = row[7:27]  # levels 1-20 (cols 7-26 roughly)
        if label and isinstance(label, str):
            print(f"  {label!r:30s} formula={formula!r:30s}  L1-10: {vals[:10]}")

    # =========================================================================
    # 4. ARCHETYPE DEFINITIONS — columns
    # =========================================================================
    divider("ARCHETYPE DEFINITIONS — Column headers and sample entries")
    data, _ = rows(wb, "Archetype Definitions", 30)
    print("Header row (row 1):")
    if len(data) > 1:
        h = data[1]
        for i, v in enumerate(h):
            if v is not None and i < 30:  # first 30 cols only
                print(f"  col {i:3d}: {v!r}")
    print("\nFirst 5 archetype entries (cols 1-19):")
    for row in data[2:7]:
        print(f"  {row[1:20]}")

    # =========================================================================
    # 5. ARCHETYPE LISTS — which archetypes belong to which classes
    # =========================================================================
    divider("ARCHETYPE LISTS — Class → Archetype mapping")
    data, _ = rows(wb, "Archetype Lists", 50)
    print("Header:")
    if data:
        h = data[0]
        for i, v in enumerate(h):
            if v is not None:
                print(f"  col {i}: {v!r}")
    print("\nFirst 30 non-empty rows:")
    count = 0
    for row in data[1:]:
        if non_empty(row):
            print(f"  {row}")
            count += 1
            if count >= 30: break

    # =========================================================================
    # 6. RACES — decode the column-indexed structure
    # =========================================================================
    divider("RACES — Decoding race table (column-numbered layout)")
    data, _ = rows(wb, "Races", 100)
    # Row 0 has col header "**CUSTOM**" in last col
    # Row 1 has numeric col indices: 1, 2, 3, ...
    # Row 2 onward has data

    if len(data) > 1:
        col_index_row = data[1]  # row with col numbers
        print("Column index row (col → number mapping):")
        for i, v in enumerate(col_index_row):
            if v is not None:
                print(f"  spreadsheet col {i} = race-table col {v}")

    print("\nRows 2-15 (first 25 cols each):")
    for j, row in enumerate(data[2:17]):
        print(f"  row {j+2}: {row[:25]}")

    # =========================================================================
    # 7. RACE & STATS — ability scores and point buy
    # =========================================================================
    divider("RACE & STATS — Ability score generation / point buy")
    data, _ = rows(wb, "Race & Stats", 60)
    print("All non-empty rows (first 20 cols):")
    for i, row in enumerate(data):
        if non_empty(row):
            print(f"  row {i:2d}: {row[:20]}")

    # =========================================================================
    # 8. TABLES — misc rules lookup tables
    # =========================================================================
    divider("TABLES — Miscellaneous lookup tables")
    data, _ = rows(wb, "Tables", 200)
    print("Header row:")
    if data:
        for i, v in enumerate(data[0]):
            if v is not None:
                print(f"  col {i}: {v!r}")
    print("\nFirst 40 non-empty rows (first 15 cols):")
    count = 0
    for row in data[1:]:
        if non_empty(row):
            print(f"  {row[:15]}")
            count += 1
            if count >= 40: break

    # =========================================================================
    # 9. FEAT DEFINITIONS — exact column layout
    # =========================================================================
    divider("FEAT DEFINITIONS — Column layout and first 20 feats")
    data, _ = rows(wb, "Feat Definitions", 30)
    print("Header row (row 1):")
    if len(data) > 1:
        h = data[1]
        for i, v in enumerate(h[:30]):
            print(f"  col {i:2d}: {v!r}")
    print("\nFirst 20 feats (cols 0-19):")
    for row in data[2:22]:
        if non_empty(row):
            print(f"  {row[:20]}")

    # =========================================================================
    # 10. TRAIT DEFINITIONS — column layout
    # =========================================================================
    divider("TRAIT DEFINITIONS — Column layout and first 20 traits")
    data, _ = rows(wb, "Trait Definitions", 30)
    print("Header row (auto-detected):")
    for i, row in enumerate(data[:5]):
        strings = [v for v in row if isinstance(v, str) and v.strip()]
        if len(strings) >= 3:
            print(f"  row {i}: {row[:20]}")
            break
    print("\nFirst 20 trait entries (cols 0-14):")
    count = 0
    for row in data:
        if count >= 20: break
        if non_empty(row) and any(isinstance(v, str) and v.strip() for v in row[1:5]):
            print(f"  {row[:15]}")
            count += 1

    # =========================================================================
    # 11. SOURCE TABLES — source book codes
    # =========================================================================
    divider("SOURCE TABLES — Source book codes and names")
    data, _ = rows(wb, "Source Tables", 100)
    print("All non-empty rows:")
    for row in data:
        if non_empty(row):
            print(f"  {row[:10]}")

    # =========================================================================
    # 12. FAVORED CLASS DATA — complete list
    # =========================================================================
    divider("FAVORED CLASS DATA — Race×Class favored class bonuses")
    data, _ = rows(wb, "Favored Class Data", 50)
    print("Header (row 1):")
    if len(data) > 1:
        h = data[1]
        for i, v in enumerate(h[:20]):
            print(f"  col {i:2d}: {v!r}")
    print("\nFirst 20 entries:")
    for row in data[2:22]:
        if non_empty(row):
            print(f"  class={row[1]!r:20s} race={row[2]!r:20s} brief={row[3]!r}")

    # =========================================================================
    # 13. CLASS ABILITIES — complete schema
    # =========================================================================
    divider("CLASS ABILITIES — Full column schema")
    data, _ = rows(wb, "Class Abilities", 5)
    print("Row 0 (super-headers):")
    for i, v in enumerate(data[0]):
        if v is not None:
            print(f"  col {i}: {v!r}")
    print("Row 1 (field names):")
    for i, v in enumerate(data[1]):
        if v is not None:
            print(f"  col {i}: {v!r}")

    # =========================================================================
    # 14. LISTS — key lists (class skills by class)
    # =========================================================================
    divider("LISTS — Looking for class-skill-by-class data")
    data, _ = rows(wb, "Lists", 100)
    print("Header row (row 0, first 30 labelled cols):")
    count = 0
    for i, v in enumerate(data[0]):
        if v is not None:
            print(f"  col {i:3d}: {v!r}")
            count += 1
            if count >= 30: break
    print("\nFirst 20 non-empty data rows (cols 0-20):")
    count = 0
    for row in data[1:]:
        if non_empty(row):
            print(f"  {row[:20]}")
            count += 1
            if count >= 20: break

    # =========================================================================
    # 15. MODS — modifier type list (bonus types etc.)
    # =========================================================================
    divider("MODS — Modifier types and descriptions (first 30)")
    data, _ = rows(wb, "Mods", 50)
    # Header at row 1
    print("Header (row 1):")
    if len(data) > 1:
        for i, v in enumerate(data[1]):
            if v is not None:
                print(f"  col {i}: {v!r}")
    print("\nFirst 30 mod entries:")
    for row in data[2:32]:
        if non_empty(row):
            name = row[2] if len(row) > 2 else None
            src  = row[3] if len(row) > 3 else None
            typ  = row[7] if len(row) > 7 else None
            mod  = row[14] if len(row) > 14 else None
            desc = row[17] if len(row) > 17 else None
            print(f"  {name!r:35s} src={src!r:15s} type={typ!r:10s} mod={mod!r}")
