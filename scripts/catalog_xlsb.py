#!/usr/bin/env python3
"""
Catalog the CoreForge .xlsb file — list all sheets, headers, and sample rows.
"""

import sys
from pyxlsb import open_workbook

FILEPATH = "/Users/stephen/Documents/GitHub/Pathfinder 1e - Content Database/example_content/Pathfinder-sCoreForge-7.4.0.1.xlsb"

KEYWORDS = {
    "class", "race", "feat", "skill", "spell", "bab", "save", "hp",
    "ability", "score", "point", "buy", "progression", "feature",
    "trait", "bonus", "level", "base", "attack",
}

def cell_val(c):
    """Return cell value, stripping None."""
    return c.v if c is not None else None

def row_values(row):
    return [cell_val(c) for c in row]

def sheet_summary(wb, name, max_data_rows=5):
    try:
        with wb.get_sheet(name) as sheet:
            rows_iter = sheet.rows()
            all_rows = []
            for i, row in enumerate(rows_iter):
                if i > 200:   # hard cap to avoid huge sheets hanging
                    all_rows.append(["... (truncated at 200 rows)"])
                    break
                vals = row_values(row)
                all_rows.append(vals)

            if not all_rows:
                return {"headers": [], "row_count": 0, "samples": []}

            headers = all_rows[0] if all_rows else []
            data_rows = all_rows[1:] if len(all_rows) > 1 else []
            # Filter out completely empty rows for sample
            non_empty = [r for r in data_rows if any(v not in (None, "", 0) for v in r)]
            samples = non_empty[:max_data_rows]
            return {
                "headers": headers,
                "row_count": len(data_rows),
                "non_empty_rows": len(non_empty),
                "samples": samples,
            }
    except Exception as e:
        return {"error": str(e)}

def is_interesting(name):
    low = name.lower()
    return any(kw in low for kw in KEYWORDS)

def main():
    print(f"Opening: {FILEPATH}\n")
    with open_workbook(FILEPATH) as wb:
        sheets = wb.sheets
        print(f"Total sheets: {len(sheets)}")
        print("Sheet names:")
        for i, s in enumerate(sheets):
            marker = " ***" if is_interesting(s) else ""
            print(f"  {i+1:3d}. {s}{marker}")

        print("\n" + "="*80)
        print("DETAILED SHEET CATALOG")
        print("="*80)

        for name in sheets:
            print(f"\n{'='*60}")
            print(f"SHEET: {name}")
            print(f"{'='*60}")
            info = sheet_summary(wb, name)
            if "error" in info:
                print(f"  ERROR: {info['error']}")
                continue

            headers = info["headers"]
            row_count = info["row_count"]
            ne = info.get("non_empty_rows", "?")
            samples = info["samples"]

            print(f"  Rows (including blanks): {row_count}")
            print(f"  Non-empty rows: {ne}")
            print(f"  Columns ({len(headers)}): {headers}")

            if samples:
                print(f"  Sample data rows (up to 5):")
                for j, row in enumerate(samples):
                    print(f"    [{j+1}] {row}")
            else:
                print("  (no non-empty data rows found)")

if __name__ == "__main__":
    main()
