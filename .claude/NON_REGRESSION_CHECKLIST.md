# NON_REGRESSION_CHECKLIST.md

Before merging major rule or sheet changes:

## Automated (run `python3 -m pytest tests/ -v`)

All 71 tests must pass. They cover:

- BAB for Fighter 6 = +6, Investigator 5 = +3, Wizard 5 = +2
- Multi-class BAB stacking (Fighter 3 + Rogue 2 = 4)
- Save math: good (floor(lvl/2)+2), poor (floor(lvl/3))
- Multi-class save stacking
- HP: max at L1, average thereafter, CON per level, favored class, minimum=level
- AC = 10 + min(dex, max_dex) + armor + shield
- CMB = BAB + STR + size; CMD = 10 + BAB + STR + DEX + size
- Iterative attacks: 1 + max(0, (bab-1)//5)
- Class skill +3 trained bonus (single and multi-class)
- Bonus stacking (dodge/untyped/circumstance stack; armor/enhancement don't)
- Prerequisite parsing (BAB, ability, feat, class feature, skill ranks)
- Spell slot keys 0-indexed
- Exporter integration (Kairon L5 reference: HP=33, BAB=3, Fort=2, Ref=6, Will=6)
- Armor max_dex cap in exporter
- Multi-class class skills in exporter

## Manual (spot-check after UI changes)

- Race modifiers display correctly on sheet
- Level-up wizard detects talent gains
- Conditions modify AC and saves correctly (sheet.html recalcStats)
- Spell panel shows for casters, hidden for non-casters
- Auth flow: login -> create -> save -> reload works end-to-end

If any automated test fails: fix before merging.
If any manual check fails: investigate and add a test.

---

End
