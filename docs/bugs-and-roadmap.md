# Bugs, Improvements & Roadmap
*Last updated: Feb 2026 — post Phase 13 level-aware creator*

---

## Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1–11 | Complete | Data import, API, creator wizard, multi-user auth |
| 12 | Next | DM View & Campaign Layer — campaign setup, DM-configurable rules, party management |
| 12a | Complete | Creator Bug Fixes — chip UI, Point Buy UX, talent budget enforcement, HP fix |
| 12b | Complete | Rules Engine Audit — 71 pytest tests, multi-class exporter fix, levelup.html auth fix |
| 13 | Complete | Level-Aware Creator — ASI selection, expanded feat budget, talent budget enforcement, feat prereq indicators, skill max label |
| PWA-0 | Planned | PWA Scaffolding — manifest.json, service worker, responsive meta, offline shell (locally hosted LAN model) |
| 14 | Planned | Encounter & Combat Tracker |
| 15 | Planned | Equipment Phase — full armor/weapon/gear UI overhaul |
| 16+ | Future | Party Inventory, Kingmaker tools |

---

## Critical Bugs (Fix in Phase 12a/12b)

### ~~C-1: HP Only Computes Level 1~~ — FIXED (Phase 12a)
**Files:** `exporter.py` now calls `get_hp()` from rules engine; `builder.py` uses max die at L1.
`progression.py` has `_CLASS_HIT_DIE_FALLBACK` dict + DB `classes.hit_die` seeded for all 68 classes.

### ~~C-2: Race Name Bug (builder.py)~~ — FIXED (Phase 12a)
Changed `"Humans"` → `"Human"`, `"Half-Elves"` → `"Half-Elf"` in `feat_budget()` and `skill_budget()`.

### ~~C-3: Investigator Spell Slots~~ — CLOSED (Not A Bug)
The Investigator IS an alchemical/prepared spellcaster (extracts, like Alchemist, max spell level 6).
DB data is correct: `spellcasting_type='alchemical'`, `spellcasting_style='prepared'`, `max_spell_level=6`.
The spell panel appearing is correct behavior.

---

## Major Gaps (Phase 13 Scope)

### ~~M-1: Class Features List Empty in Exporter~~ — IMPROVED (Phase 12a)
Comma-split of `class_progression.special` actually works correctly for all classes with populated data.
Added fallback: when `special` is empty for all levels (OA classes), queries `class_features` table instead.

### ~~M-2 / M-7: Talent Budget Not Enforced + Wrong Schedule~~ — FIXED (Phase 13)
`talentBudget()` in `creator.js` enforces class-specific schedules. Budget counter shown in talent panel title.
`toggleTalent()` blocks selection when at budget. Three schedule types: even (most classes), odd3 (Investigator), odd1 (Arcanist).
**User report (Feb 2026):** Reports still being able to select unlimited talents — may affect classes not in a schedule set (returns `Infinity`). Investigate which class triggered this.

### M-3: No Level or Prerequisite Gating on Talents
Talents should be filtered to: (a) unlocked at or below character level, (b) prerequisites met by selected talents.
**User-confirmed (Feb 2026):** Can still select talents with prerequisites without meeting them.

### ~~M-4: No Ability Score Increase (ASI) Selection~~ — FIXED (Phase 13)
ASI panel added to Abilities step when `startLevel >= 4`. Choices stored in `asiChoices` state and `asi_choices` in character JSON. `getFinalScores()` sums ASI bonuses.

### M-5: Per-Level FCB Choices Not Supported
`fav_class_choice` is a single string; should be `fcb_choices: ['hp','skill',...]` array of length=level.

### M-6: Alchemist Formula Book Not Tracked
Formula book needs per-spell-level tracking: `INT_mod+3` starting 1st-level formulas; `INT_mod` new formulas per level; accessible by spell level unlocked per class level.
**See also M-14:** Spell/formula acquisition source tracking and M-15: spell limits enforcement per tables.

### M-8: Archetype Filter Too Broad
Investigator archetype picker shows archetypes from other classes.

### M-9: Roll Method UX — Assigned Values Still Appear Selectable
**Status:** Open (user-reported Feb 2026)
When rolling 4d6 for stats, if you assign a rolled 15 to DEX, the 15 chip still appears available when assigning STR. Clicking it blanks out DEX. While the chip-pool logic handles this (re-assigns), the UX is confusing — assigned values should appear clearly locked/unavailable until explicitly unassigned.

### M-10: Missing Core Feats in Database
**Status:** Open (user-reported Feb 2026)
Several important CRB/core feats are missing or not showing in the picker: Weapon Focus, Weapon Finesse, Rapid Shot. Makes it hard to build martial characters (e.g. Ranger). Likely a data import gap — investigate which feats from CRB are missing from the `feats` table.

### M-11: Racial Traits Not Listed / Trait Section Needs Overhaul
**Status:** Open (user-reported Feb 2026)
The Traits section only shows campaign/combat/faith/magic/social/regional character traits. PF1e racial traits (Alternate Racial Traits that replace default racial abilities, e.g. Darkvision, Weapon Familiarity) are not listed anywhere. The entire trait selection UX needs reevaluation against PF1e core rules:
- **Character Traits:** 2 traits from different categories (current implementation, partially works)
- **Racial Traits:** default racial abilities + optional alternate racial traits (swaps) — NOT implemented
- **Class Traits:** not the same as character traits — currently conflated

### M-12: Armor Data Gaps — Missing Items and Variants
**Status:** Open (user-reported Feb 2026)
Only 28 armor rows in DB. Missing common items (e.g. Studded Leather). No support for:
- Masterwork variants (ACP reduced by 1)
- Magic armor (+1, +2, etc. — increased armor bonus)
- Special materials (Mithral, Darkwood, etc.)
Related to Phase 15 Equipment scope.

### M-13: No Weapon Proficiency Enforcement
**Status:** Open (user-reported Feb 2026)
Characters can equip any weapon regardless of class proficiency. A Wizard can equip a Greatsword (martial) with no warning. Should check class weapon proficiencies and flag non-proficient selections (−4 attack penalty).

### M-14: Spell/Formula Acquisition Source Tracking
**Status:** Open (user-reported Feb 2026)
No way to record HOW a spell/formula was learned: initial allotment, level-up choice, scroll/spellbook copy, or DM award. Needed for Wizard spellbooks and Alchemist formula books to track which spells are "free" (from leveling) vs. found/purchased. Proposed JSON: `{spell_name, source: 'initial'|'levelup'|'scroll'|'dm_award', level_gained}`.

### M-15: Spell/Formula Known Limits Not Enforced
**Status:** Open (user-reported Feb 2026)
No enforcement of how many spells/formulae a character can know per class tables. Should limit level-up selections per class progression tables, while allowing unlimited additions via DM Award or scroll/spellbook sources. Related to M-6 (Alchemist formula book).

### M-16: Feat Level/Method Assignment Missing
**Status:** Open (user-reported Feb 2026)
Currently all feats are tagged as `method: 'general'` at current `startLevel`. Should allow selecting which level a feat was gained and how (Level 1 general, Level 3 general, Fighter Bonus L1, DM Award, etc.). Important for multi-level characters to track feat progression accurately.

### M-17: "Extra Talent" Feats Need Special Handling
**Status:** Open (user-reported Feb 2026)
Feats like "Extra Investigator Talent", "Extra Rage Power", "Extra Rogue Talent" etc. grant an additional class talent selection. These feats should increase `talentBudget()` by 1 per instance. Currently no link between feat selection and talent budget.

---

## Bugs — Creator UX (user-reported Feb 2026)

### UX-1: Recent Characters "Sheet" Link Returns Auth Error
**Status:** Open
Clicking "Sheet" in the Recent Characters sidebar opens `/api/characters/${id}/sheet` in a new tab via `<a>` tag. This is an unauthenticated GET request — returns `{"detail":"Not authenticated"}`. The JWT token is in localStorage but `<a href>` navigation doesn't include auth headers. Need either: (a) a session cookie fallback, (b) a token query param, or (c) open via JS `fetch()` + blob URL.

### UX-2: Feat Overbudget Does Not Block Step Progression
**Status:** Open
If you select feats, then go back and change level/class (reducing budget), the feats step shows "4/3" but `validateCurrentStep()` for case 2 (feats) returns `[]` — no validation. User can proceed to review with more feats than allowed. Should either block progression or warn.

---

## Moderate Issues (Phase 12a Scope)

| ID | Description |
|----|-------------|
| MOD-1 | Standard Array chip UI layout broken (post chip-UI redesign) |
| ~~MOD-2~~ | ~~Point Buy UX~~ — FIXED (Phase 12a): marginal cost shown on +/- buttons, budget check uses marginal cost |
| ~~MOD-3~~ | ~~Feat prerequisites not validated in feat picker~~ — FIXED (Phase 13): `checkFeatPrereqs()` parses ability scores, BAB, and feat chains. Unmet prereqs shown with red text/border (still selectable as DM override). **User report (Feb 2026):** Wants hard block or at minimum a confirmation before selecting unmet-prereq feats, not just visual indicators. |
| ~~MOD-4~~ | ~~Wizard/Monk/Cavalier/Magus bonus feats missing from featBudget()~~ — FIXED (Phase 13): `classBonusFeats()` counts "bonus feat" in progression data. Falls back to Fighter formula when progression not loaded. |
| ~~MOD-5~~ | ~~Max ranks per skill (= character level) not enforced in skill stepper~~ — FIXED (Phase 13): "(max)" label shown when ranks equal level cap. Already enforced by `changeRank()`. |
| MOD-6 | Non-spellcasters get spell panel if DB has bad spells_per_day data |
| MOD-7 | FCB dual-bonus (HP+Skills) DM option → Phase 12 scope |

---

## Phase 12b: Rules Engine Audit — COMPLETE

71 pytest tests covering all rules engine modules. All pass. Key findings:

### Functions Audited & Verified
1. `progression.py::get_hp()` — max at L1, average thereafter, CON per level, favored class HP, minimum = total level ✅
2. `progression.py::get_bab()` / `get_save()` — multi-class stacking verified (Fighter 3 + Rogue 2) ✅
3. `progression.py::get_spell_slots()` — reads correctly per level from DB ✅
4. `combat.py::ac/cmb/cmd/initiative/attack_bonus` — all formulas correct ✅
5. `bonuses.py::BonusStack` — stacking rules (dodge/untyped/circumstance stack, others don't) ✅
6. `prerequisites.py` — parsing and checking of BAB, ability, feat, class feature prereqs ✅
7. `skills.py` — class skill bonus, multi-class union, totals ✅
8. `exporter.py::_compute_derived()` — full integration verified against Kairon L5 reference ✅

### Bugs Fixed (Phase 12b)
- **Exporter multi-class class skills**: only loaded skills from first class level; now unions all
- **levelup.html missing auth**: `apiFetch()` and `exportLevelUp()` now include JWT auth headers + 401 handling

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
| HP | 33 (max L1) | 33 | ~~C-1~~ FIXED |
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
| Talent count | 2 | 1 (budget enforced) | ~~M-2, M-7~~ FIXED |
| Class features | Alchemy, Inspiration, etc. | 14 entries | ~~M-1~~ FIXED |
| Spell panel | Should appear (extracts) | Appears | ~~C-3~~ Not a bug |
| ASI (level 4) | 1 applied | ASI panel available | ~~M-4~~ FIXED |

**Kairon L9 Expected:**
- HP: 54 (avg all) or 57 (max L1)
- BAB: +6/+1 | Fort: +4 | Ref: +8 | Will: +8
- Feats: 5 | Talents: 4 | 2 ASIs applied (L4, L8)
- Skill budget: 90 ranks

---

## Context Window Break Points

Each phase should end with: bugs fixed + Kairon test verified + this doc updated + git commit + push.

**Current checkpoint:** Post Phase 13 — level-aware creator complete (ASI, feat budget, talent budget, prereq indicators, skill max label).
**Next conversation:** Phase 12 (DM campaign layer) or Phase 14 (Encounter & Combat Tracker).
