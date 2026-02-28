# Bugs, Improvements & Roadmap
*Last updated: Feb 2026 — post Phase 11*

---

## Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1–11 | Complete | Data import, API, creator wizard, multi-user auth |
| 12 | Next | DM View & Campaign Layer — campaign setup, DM-configurable rules, party management |
| 12a | Next (parallel) | Creator Bug Fixes — chip UI, Point Buy UX, talent budget enforcement, HP fix |
| 12b | Next (parallel) | Rules Engine Audit — full audit of level-up calculations, test suite vs Kairon reference |
| 13 | Planned | Level-Aware Creator — ASI, per-level FCB, talent gating, prerequisite enforcement |
| 14 | Planned | Encounter & Combat Tracker |
| 15 | Planned | Equipment Phase — full armor/weapon/gear UI overhaul |
| 16+ | Future | Party Inventory, Kingmaker tools |

---

## Critical Bugs (Fix in Phase 12a/12b)

### C-1: HP Only Computes Level 1
**Files:** `src/character_creator/builder.py`, `src/character_creator/exporter.py`
**Problem:** `compute_hp()` calculates `HIT_DIE_AVG + CON_mod` — level 1 only.
**Expected (Investigator L5, CON+1):** 30 HP (avg all) or 33 HP (max L1)
**Actual:** 6 HP
**Fix:** Loop levels 1..N: max at L1, average for L2+, minimum 1 per level, add FCB HP count.
```
HP = (die_max + CON) + sum(max(1, die_avg + CON) for L in 2..N) + fcb_hp_count
```

### C-2: Race Name Bug (builder.py)
**File:** `src/character_creator/builder.py`
**Problem:** Check uses `"Humans"` (plural) — never matches DB value `"Human"` (singular).
**Effect:** Human characters silently lose +1 skill rank per level.
**Fix:** Change `== "Humans"` to `== "Human"`.

### C-3: Investigator Has Bad Spell Slot Data in DB
**Location:** `db/pf1e.db` table `class_progression`, Investigator rows
**Problem:** `spells_per_day` column is populated for Investigator but Investigator is not a spellcaster. This causes a spell slot panel to appear in the creator and sheet.
**Fix:** Clear `spells_per_day` for Investigator rows, or add logic to suppress spell panel when `spellcasting_type IS NULL`.

---

## Major Gaps (Phase 13 Scope)

### M-1: Class Features List Empty in Exporter
`exporter.py` splits `class_progression.special` on commas, producing empty or garbled output. Feature names themselves contain commas.

### M-2 / M-7: Talent Budget Not Enforced + Wrong Schedule
All class talents shown regardless of level. No budget counter.
- Investigator: talents at ODD levels 3,5,7,...19 = **9 total** (formula: `floor((level-1)/2)` for level≥3)
- Alchemist/Rogue/Barbarian: EVEN levels 2,4,...20 = 10 total (formula: `floor(level/2)`)
- Arcanist: levels 1,3,5,...19 = 10 total (formula: `(level+1)//2`)

### M-3: No Level or Prerequisite Gating on Talents
Talents should be filtered to: (a) unlocked at or below character level, (b) prerequisites met by selected talents.

### M-4: No Ability Score Increase (ASI) Selection
Characters at level 4, 8, 12, 16, 20 earn +1 to any ability score. Not tracked or applied.

### M-5: Per-Level FCB Choices Not Supported
`fav_class_choice` is a single string; should be `fcb_choices: ['hp','skill',...]` array of length=level.

### M-6: Alchemist Formula Book Not Tracked
Formula book needs per-spell-level tracking: `INT_mod+3` starting 1st-level formulas; `INT_mod` new formulas per level; accessible by spell level unlocked per class level.

### M-8: Archetype Filter Too Broad
Investigator archetype picker shows archetypes from other classes.

---

## Moderate Issues (Phase 12a Scope)

| ID | Description |
|----|-------------|
| MOD-1 | Standard Array chip UI layout broken (post chip-UI redesign) |
| MOD-2 | Point Buy UX — no marginal cost display next to stepper buttons |
| MOD-3 | Feat prerequisites not validated in feat picker |
| MOD-4 | Wizard/Monk/Cavalier/Magus bonus feats missing from featBudget() |
| MOD-5 | Max ranks per skill (= character level) not enforced in skill stepper |
| MOD-6 | Non-spellcasters get spell panel if DB has bad spells_per_day data |
| MOD-7 | FCB dual-bonus (HP+Skills) DM option → Phase 12 scope |

---

## Level-Up Rules Engine — What Needs to Be Evaluated (Phase 12b)

The rules engine in `src/rules_engine/` and `src/character_creator/` has several functions that need full audit for multi-level correctness:

### Functions to Audit
1. `builder.py::compute_hp()` — broken (C-1)
2. `builder.py::skill_budget()` — broken race check (C-2), needs multi-level sum
3. `builder.py::feat_budget()` — missing class-specific bonus feat schedules
4. `exporter.py::_compute_derived()` — HP (C-1), class features (M-1), trait bonuses (missing), ASI (missing)
5. `progression.py::get_hp()` — verify if multi-level or not
6. `progression.py::get_bab()` / `get_save()` — verify multi-class stacking
7. `progression.py::get_spell_slots()` — verify reads correctly per level

### Trait Bonuses Not Applied
The `exporter.py` `_compute_derived()` does not apply trait effects to derived stats:
- Reactionary trait: +2 initiative (Kairon initiative shows +2 instead of expected +4)
- Clever Wordplay: changes key ability for chosen skill from CHA to INT
- Resilient: +1 to a saving throw
A trait → stat_delta lookup table is needed.

### Correct Formulas Reference
```
HP per level:   L1 = die_max + CON_mod; L2+ = die_avg + CON_mod (min 1/level)
Skill budget:   max(1, class_rpl + INT_mod) * level + (level if Human) + fcb_skill_count
Feat budget:    ceil(level/2) + class_bonus_feats(class, level) + racial_bonus(race)
Talent budget:  class-specific schedules (see bugs-and-roadmap.md §M-2/M-7)
ASI count:      len([l for l in [4,8,12,16,20] if l <= level])
Save (good):    floor(level/2) + 2
Save (poor):    floor(level/3)
BAB (full):     level
BAB (3/4):      floor(level * 3/4)
BAB (1/2):      floor(level/2)
```

---

## Self-Test Reference: Kairon (Investigator L5, Tiefling)

Character files: `characters/Kairon_Investigator_sheet.html` and higher-level variants.

| Stat | Expected | System Output | Bug |
|------|----------|---------------|-----|
| HP | 30 (avg) or 33 (max L1) | 6 | C-1 |
| BAB | +3 | +3 | ✓ |
| Fort | +2 | +2 | ✓ |
| Ref | +6 | +6 | ✓ |
| Will | +6 | +6 | ✓ |
| Init | +4 (DEX+2, Reactionary+2) | +2 | Trait bonus missing |
| AC | 12 | 12 | ✓ |
| CMB | +3 | +3 | ✓ |
| CMD | 15 | 15 | ✓ |
| Skill budget | 50 ranks | 50 | ✓ |
| Feat count | 3 | 3 | ✓ |
| Talent count | 2 | Unlimited | M-2, M-7 |
| Class features | Alchemy, Inspiration, etc. | Empty | M-1 |
| Spell panel | Should not appear | Appears | C-3 |
| ASI (level 4) | 1 applied | Not tracked | M-4 |

**Kairon L9 Expected:**
- HP: 54 (avg all) or 57 (max L1)
- BAB: +6/+1 | Fort: +4 | Ref: +8 | Will: +8
- Feats: 5 | Talents: 4 | 2 ASIs applied (L4, L8)
- Skill budget: 90 ranks

---

## Context Window Break Points

Each phase should end with: bugs fixed + Kairon test verified + this doc updated + git commit + push.

**Current checkpoint:** Post Phase 11 + chip UI redesign + rules engine research.
**Next conversation:** Start with Phase 12a (bug fixes) or 12b (engine audit) — prioritize C-1, C-2, C-3.
