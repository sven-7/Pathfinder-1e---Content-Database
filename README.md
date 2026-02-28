# Pathfinder 1e — Campaign Manager

A comprehensive Pathfinder 1st Edition campaign management platform: structured SRD content database, rules engine, character creator, character sheets, and eventually full campaign tooling for GMs and players.

---

## Vision

**The end goal is a cohesive, session-ready campaign manager** — not a collection of disconnected tools. Every view (creator, sheet, cheat sheet, DM panel) is part of one unified app that a player or GM opens at the table.

### User Interfaces (in order of development)

| Interface | Description | Status |
|-----------|-------------|--------|
| **Character Creator** | Guided 6-step wizard: Origins → Abilities → Feats → Extras → Skills → Review | ✅ v1 Done |
| **Classic Character Sheet** | Authoritative character record — Paizo PDF-style with roll buttons, spell dots, weapon blocks | 🔧 Phase 8 |
| **Spell & Formula Book** | Dedicated spellcaster panel — prepared/spontaneous tracking, formula tactical groupings | 🔧 Phase 9 |
| **Cheat Sheet (Modular Panels)** | Situation-based quick reference, drag-and-drop panels, print to 1–2 pages | 🔧 Phase 10 |
| **DM View** | Party overview, NPC manager, all character sheets readable by GM | 🔧 Phase 12 |
| **Campaign Manager** | Multi-user library, campaign rosters, session notes, shared loot | 🔧 Phase 12 |
| **Encounter Tracker** | Initiative order, HP per combatant, conditions, round tracking | 🔧 Phase 13 |
| **Kingmaker Tools** | Kingdom stats, hex map, settlement building, BP/edicts tracker | 🔧 Phase 15 |

### Design Principles

- **Situation-based over category-based** — The cheat sheet asks "It's my turn — what are my options?" not "here are all my feats in one box." All interfaces should prioritize what a player needs *right now*.
- **Calculated final numbers** — The player sees "+17/+12" not "BAB +6 + DEX +4 + Weapon Focus +1." Breakdowns are in tooltips, not primary display.
- **Cohesive, not fragmented** — One app, consistent visual language (parchment/Cinzel/Crimson Text), one navigation system. Not separate tools loosely connected.
- **Print-quality everywhere** — Every view has a print stylesheet. A player should be able to print any panel on letter paper before a session.
- **Paizo-official by default** — 3pp content filtered out unless explicitly enabled.

---

## Project Roadmap

### Completed

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | **Data Foundation** — d20pfsrd.com scraper + SQLite import (spells, feats, classes, archetypes, races, traits, class features) | ✅ Complete |
| 2 | **Rules Engine** — BAB/saves/HP/skills/prerequisites/combat math | ✅ Complete |
| 3 | **Character Creator v1** — 6-step wizard, sheet, level-up wizard, character library | ✅ Complete |
| 4 | **Data Layer Audit** — class_skills, spell slots, class features on sheet, size lookup | ✅ Complete |
| 5 | **Feat Filtering** — exclude monster/mythic feats from creator; prerequisite text shown in picker | ✅ Complete |
| 6 | **Equipment System** — 70 weapons + 28 armor entries; armor dropdown, shield dropdown, weapon picker in creator; AC computed from equipped armor; weapon stat blocks on sheet | ✅ Complete |
| 7 | **Creator Polish — Class Abilities & Spells** — talent selection (rage powers, rogue talents, etc.); spell selection by level in creator; level-up wizard detects new spell levels and talent gains | ✅ Complete |

### Near-Term: Content Quality

| Phase | Description | Deliverable |
|-------|-------------|-------------|
| **5** | **Feat Data & 3pp Filtering** — Reimport feat types/prerequisites/descriptions from CoreForge + Foundry; add `is_paizo_official` flag; wire type badges + prereq text into feat picker | Feat picker is genuinely useful — player can see type, requirements, and what a feat does |
| **6** | **Equipment System** — Import weapons + armor from Foundry data; equipment selection in creator; AC updates from equipped armor; weapon blocks appear on sheet | Characters have weapons and armor that affect calculated stats |

### Mid-Term: UI/UX — The Interfaces Players Want

| Phase | Description | Deliverable |
|-------|-------------|-------------|
| **7** | **Creator Polish — Class Abilities & Spells** — Class ability selection during level-up (rage powers, rogue talents, discoveries, etc.); spell selection at level-up (known/prepared per class); multi-level feat associations | Level-up wizard is complete for all class types |
| **8** | **Classic Character Sheet** — Full redesign to Paizo-parity: ornamental header, ability block, weapon stat blocks with roll buttons, resource pool trackers (Ki/Rage/Inspiration), conditions that modify displayed values, print-optimized layout | A sheet you want to bring to the table |
| **9** | **Spell & Formula Book Panel** — Dedicated spellcaster view: spell dots per level, prepared vs. spontaneous workflow, Alchemist formula book with tactical groupings (combat buffs / defensive / utility / social), infusion tracking | Spellcasters have a complete, playable spell workflow |
| **10** | **Cheat Sheet — Modular Panels** — Situation-based panels (Combat, Resources, Skills, Abilities); drag-and-drop to rearrange; toggle visibility; action economy icons (● standard, ◐ move, ◑ swift, ◆ immediate, ○ free); print to 1–2 pages | Players assemble a custom reference card for the session |

### Long-Term: Multi-User & Group Play

| Phase | Description | Deliverable |
|-------|-------------|-------------|
| **11** | **Multi-User Backend** — PostgreSQL migration for character storage; user accounts (username/password); characters owned by users; character library persisted in DB instead of JSON files | Multiple players log in and manage their own characters |
| **12** | **DM View & Campaign Layer** — Campaign model (name, GM, player roster); party overview (HP, conditions, initiative at a glance); GM reads any character sheet; simple NPC/creature manager; shared session notes | A GM can open the app and see the whole party |
| **13** | **Encounter & Combat Tracker** — Initiative order; HP tracking per combatant (PC + NPC); conditions applied per combatant; round/turn tracking; quick-access to combat panel during a character's turn | Run a combat from a single screen |
| **14** | **Party & Inventory Management** — Shared party loot pool; individual character inventory with weight; item descriptions from equipment DB; gold tracking; treasure distribution | No more spreadsheets for tracking loot |

### Future: Kingmaker & Campaign-Specific Tools

| Phase | Description | Notes |
|-------|-------------|-------|
| **15** | **Kingmaker — Kingdom Tracker** — BP pool, kingdom stats (Stability/Economy/Loyalty/Fame), edicts (Improvement/Taxation/Promotion), kingdom events, month-by-month log | Kingmaker-specific; design when campaign reaches kingdom phase |
| **16** | **Kingmaker — Settlement Builder** — Hex map of claimed territory; settlement district grid; buildings + lots; settlement modifiers | Pairs with Phase 15 |
| **17** | **World & Encounter Maps** — Upload/pin maps; mark locations; GM notes per hex; link encounters to map locations | Low priority; scope TBD |

---

## Quick Start

```bash
git clone https://github.com/sven-7/Pathfinder-1e---Content-Database.git
cd "Pathfinder-1e---Content-Database"

pip install -r requirements.txt

# Launch the app (opens browser at http://localhost:8000)
python scripts/run_app.py
```

---

## What's Been Built

### Phase 1 — Data Foundation
- SQLite database (`db/pf1e.db`, ~48 MB) built from d20pfsrd.com scraping
- **Content counts:** 2,921 spells · 1,678 feats · 68 classes · 1,306 archetypes · 5,816 archetype features · 2,653 class features · 423 races · 1,176 traits
- **Class progression:** 1,180 rows covering BAB, saves, and spell slots across all 68 classes
- Scrapers in `src/scrapers/` for spells, feats, classes, races, archetypes, traits, class features

### Phase 2 — Rules Engine
Full Python rules library in `src/rules_engine/`:

| Module | Responsibility |
|--------|---------------|
| `db.py` | Read-only SQLite wrapper (`RulesDB`) |
| `character.py` | `Character` + `ClassLevel` dataclasses, lazy derived stats |
| `progression.py` | BAB, save, HP, spell slot lookups from `class_progression` |
| `skills.py` | Skill totals, class skill detection, trained bonus |
| `combat.py` | AC breakdown, CMB/CMD, initiative, attack bonus |
| `bonuses.py` | Bonus stacking (dodge/racial/untyped/circumstance) |
| `prerequisites.py` | Prerequisite parsing and checking → `PrereqResult` |

### Phase 3 — Character Creator GUI
Local web app at `http://localhost:8000`:

**6-step creation wizard:**
1. **Origins** — Name, alignment, starting level, race picker (37 races: Core/Featured/Uncommon), class picker with archetype dropdown
2. **Abilities** — Standard Array / Point Buy (25pt) / Roll 4d6 / Manual entry; racial mods applied live
3. **Feats & Traits** — Filterable feat browser; trait browser; budget scales with level; feats tagged with level + method
4. **Extras** — Class talents (rage powers, rogue talents, discoveries, hexes, etc.); spell selection; favored class bonus toggle (HP or Skill Rank per level)
5. **Skills** — Rank allocator with class skill highlighting and per-skill breakdown
6. **Review** — Full stat preview; Save & View Sheet / Download JSON / Save to Library

**Character sheet** (`/sheet`) — Derived stats, HP tracker, conditions, dice roller, print stylesheet, Level Up button

**Level-up wizard** (`/levelup`) — 7-step flow: Load → HP → Ability → Skills → Feat → Features → Review

### Phase 4 — Data Layer Audit

| Component | Status | Notes |
|-----------|--------|-------|
| BAB | ✅ Correct | Full/¾/½ at all levels, multi-class sums |
| Saves | ✅ Correct | good=floor(lvl/2)+2, poor=floor(lvl/3) |
| HP | ✅ Correct | Max at L1, avg (d6→4, d8→5, d10→6, d12→7) thereafter |
| Skill totals | ✅ Fixed | `class_skills` table: 776 rows, 68 classes; +3 trained bonus works |
| Spell slots | ✅ Fixed | All spellcasting classes covered |
| Class features | ✅ Fixed | Sheet shows class_progression.special + archetype features |
| Size lookup | ✅ Fixed | `combat.py` reads `races.size` from DB |
| AC | ✅ Fixed (Phase 6) | Full armor/shield/dex/max_dex calculation |

### Phase 5 — Feat Filtering
- Monster and Mythic feat types excluded from creator picker by default
- Prerequisite text (`feat_type`, `prerequisites` fields) shown in picker where data exists
- ~100+ monster feats removed from selection pool

### Phase 6 — Equipment System
- 70 CRB weapons (simple/martial/exotic, melee/ranged) seeded via `scripts/seed_weapons_armor.py`
- 28 armor/shield entries (light/medium/heavy/shield types, max_dex, ACP, ASF)
- Creator Extras step: armor dropdown, shield dropdown, weapon picker (up to 4 weapons, filterable by proficiency/type)
- Exporter computes: `ac_total = 10 + min(dex, max_dex) + armor + shield`; touch/flat-footed AC breakdowns
- Iterative attacks: `num_attacks = 1 + max(0, (bab - 1) // 5)` — Fighter 6 shows `+9/+4` ✓
- Sheet displays: equipped armor/shield with stats, weapon blocks with pre-computed attack/damage strings

### Phase 7 — Creator Polish: Class Abilities & Spells
- Class talent selection (rage powers, rogue talents, discoveries, hexes, etc.) in creator Extras step
- `CLASS_TALENT_MAP` maps 12 classes to their pickable feature types; uses `/api/classes/{name}/features`
- Spell selection by level using actual `class_progression.spells_per_day` DB data (not a formula guess)
- Cantrip/orison keys: key `0` = cantrips; key `1`-`9` = 1st–9th level spells
- Sorcerer/Bard show "at will" cantrip tab + numbered spell levels from their per-day table
- Level-up wizard (Step 5 "Features") detects talent gains via `special` field substring match; detects new spell levels by comparing current vs previous level's `spells_per_day` keys
- Spell slot display fixed (Feb 2026): DB re-imported with 0-indexed keys after parser bug found

---

## Self-Evaluation

### Rules Engine — Verified Against Pathfinder Iconics (Feb 2026)

All four standard Pathfinder Society core iconic characters verified correct at Level 1:

| Character | Race | Class | BAB | Fort | Ref | Will | Result |
|-----------|------|-------|-----|------|-----|------|--------|
| Kyra | Human | Cleric 1 (STR 14 DEX 10 CON 12 INT 10 WIS 18 CHA 14) | +0 | +3 | +0 | +6 | ✅ All correct |
| Valeros | Human | Fighter 1 (STR 18 DEX 14 CON 14 INT 10 WIS 12 CHA 8) | +1 | +4 | +2 | +1 | ✅ All correct |
| Merisiel | Elf | Rogue 1 (STR 10 DEX 20 CON 12 INT 14 WIS 10 CHA 14) | +0 | +1 | +7 | +0 | ✅ All correct |
| Ezren | Human | Wizard 1 (STR 10 DEX 14 CON 12 INT 18 WIS 12 CHA 11) | +0 | +1 | +2 | +3 | ✅ All correct |

Multi-class verified: Fighter 1 / Wizard 2 → BAB +2, Fort +2, Ref +0, Will +3 ✓

Skill total verified: Kyra Heal (1 rank + WIS +4 + class +3) = **+8** ✓

### What's Working
- Rules math correct end-to-end for all tested builds (Kyra/Valeros/Merisiel/Ezren ✓)
- Creator wizard is functional: create → save → sheet → level up → re-save
- 37 playable races with correct ability mods, size, and speed
- 68 classes with hit die, skill ranks, spell slots, class features
- 70 weapons + 28 armor entries; AC computed from equipped items
- Spell selection uses actual class progression data (not formula guesses)
- Class talent selection (rage powers, rogue talents, etc.) in creator and level-up

### Current Gaps (post-Phase 7)

**Sheet quality below target (high):** Sheet is functional but plain. No spell dots, no roll buttons, no resource trackers (rage rounds/ki points), conditions don't modify displayed values. Phase 8 target.

**Spells known vs. prepared not distinguished (medium):** Creator lets you pick spells but doesn't distinguish between Wizard (spellbook/prepared) vs. Sorcerer (spells known, spontaneous). Both show the same picker. A future improvement.

**Cleric domain spells counted as base slots (low):** The `+1` domain bonus was stripped from the import (e.g., `"1+1"` → `1`). Domain spells are tracked as a class feature, not as extra slots. Current behavior is close enough for play.

**3pp archetypes present (medium):** Archetype list includes third-party content with no Paizo-official flag. Phase 5 only filtered feats, not archetypes. Needs `is_paizo_official` column on archetypes table.

**No spell descriptions in picker (medium):** Creator spell picker shows name only. No description, school, range, or casting time. Makes it hard to choose wisely during creation.

**Favored class bonus not reflected on sheet (low):** Creator tracks `favClassChoice` (HP or skill rank per level) but the sheet display doesn't show the actual applied bonus HP/skill ranks clearly.

---

## Known Issues

### High Priority
- **Sheet redesign needed** — Current sheet is functional but lacks roll buttons, spell dots, resource trackers, and conditions that modify displayed stats (Phase 8 target)
- **No spell descriptions in picker** — Spell selection shows name only; no school, range, description, or casting time
- **No prepared/spontaneous workflow** — Sheet doesn't distinguish Wizard (prepare daily) from Sorcerer (known pool); no slot-usage tracking

### Medium Priority
- **3pp archetypes present** — No `is_paizo_official` flag on archetypes table; third-party archetypes mixed in with Paizo content
- **Feat descriptions sparse** — Many feats show prerequisite text but no benefit description; need data import from Foundry or CoreForge
- **Favored class bonus display** — The HP or skill rank bonus is tracked in creator JSON but not clearly labeled on the sheet
- **Spells known vs. spells prepared** — Creator conflates the two; Wizard and Cleric should use "prepare X spells from spellbook/prayer list" workflow

### Low Priority
- **Trait source encoding artifact** — "Â" character before © in some trait source fields
- **Cross-class skill ranks not limited** — PF1e technically allows full rank investment in cross-class skills; no cap enforced (intentional simplification)
- **Alchemist spell selection** — Alchemist uses "formulae" not "spells"; creator shows "Spells" label but should say "Formulae / Extracts"
- **Saving throw names** — DB column is `fort_save`/`ref_save`/`will_save`; JS sometimes assumes `fort`/`ref`/`will` keys; both work in practice but inconsistent
- **HP at level 1** — Creator correctly uses max die at level 1, but the exporter fallback (`hp_max = HIT_DIE_AVG + CON`) uses average die even at level 1 if `hp_max` wasn't saved in the character dict

### Verified Working (do not regress)
- BAB/saves/HP for all 4 CRB classes at level 1 ✓
- Iterative attack strings: Fighter 6 → `+9/+4`, Fighter 11 → `+14/+9/+4` ✓
- AC: 10 + min(DEX, max_dex_from_armor) + armor + shield ✓
- Class skills: +3 trained bonus when 1+ rank in a class skill ✓
- Spell slots: 0-indexed keys (0=cantrips, 1=1st level) after Feb 2026 re-import ✓
- Race ability mods: Dwarf +CON +WIS -CHA, Elf +DEX +INT -CON, etc. ✓

---

## Project Structure

```
├── README.md
├── requirements.txt
├── .gitignore
│
├── db/
│   └── pf1e.db                        # SQLite database (~48 MB)
│
├── src/
│   ├── api/
│   │   ├── app.py                     # FastAPI app, lifespan, route registration
│   │   └── routes/
│   │       ├── races.py               # GET /api/races
│   │       ├── classes.py             # GET /api/classes, archetypes, features
│   │       ├── feats.py               # GET /api/feats (excludes monster/mythic by default)
│   │       ├── skills.py              # GET /api/skills, class skills
│   │       ├── traits.py              # GET /api/traits
│   │       ├── spells.py              # GET /api/spells (class_name + level filter)
│   │       ├── equipment.py           # GET /api/equipment/weapons, /api/equipment/armor
│   │       └── characters.py          # CRUD /api/characters, sheet HTML export
│   │
│   ├── character_creator/
│   │   ├── builder.py                 # CharacterBuilder wizard logic
│   │   ├── ability_scores.py          # standard_array, point_buy, roll_4d6
│   │   └── exporter.py                # generate_sheet_html() → standalone HTML
│   │
│   ├── rules_engine/                  # Phase 2 rules library
│   │   └── ...
│   │
│   └── scrapers/                      # d20pfsrd.com scrapers
│       ├── base.py, manifest.py
│       ├── spell_parser.py, feat_parser.py, class_parser.py
│       ├── race_parser.py, archetype_parser.py
│       ├── trait_parser.py, class_feature_parser.py
│       └── static_data.py             # 38 languages + 35 skills
│
├── static/
│   ├── creator.html                   # Character creation wizard
│   ├── sheet.html                     # Character sheet template
│   ├── levelup.html                   # Level-up wizard
│   ├── css/
│   │   ├── parchment.css              # Shared design tokens (Cinzel/Crimson Text)
│   │   ├── creator.css
│   │   └── sheet.css
│   └── js/
│       └── creator.js                 # Wizard state machine (~1,600 lines)
│
├── scripts/
│   ├── run_app.py                     # python scripts/run_app.py → opens browser
│   ├── scrape_d20pfsrd.py             # Main scraper orchestrator
│   ├── import_scraped.py              # JSON → SQLite importer
│   ├── import_class_progressions.py   # PSRD class progression importer
│   ├── seed_weapons_armor.py          # CRB weapon/armor stat seed (Phase 6)
│   └── scrape_missing_archetypes.py   # Gap-fill archetype scraper
│
├── characters/                        # Saved character JSON files (gitignored)
│   └── *.json
│
├── data/
│   ├── psrd/                          # PSRD-Data source JSONs
│   ├── foundry/                       # Foundry VTT PF1e content (21,551 records)
│   └── foundry-archetypes/            # Foundry archetype data (7,285 records)
│
└── example_content/                   # Reference files (gitignored)
    ├── Goals/                         # Project origin summaries
    ├── kairon_v4_6.html               # Target sheet design reference
    ├── kairon_levelup.html            # Target level-up design reference
    ├── Pathfinder-sCoreForge-7.4.0.1.xlsb  # PF1e rules reference
    └── ChatGPT PostgreSQL/            # ETL pipeline for XLSB → Postgres
```

---

## Iconic Character Reference Builds

These Pathfinder Society iconic characters are used to verify rules engine correctness. All verified against official Paizo stat blocks (20-point buy).

All scores below are **final scores** (racial mods applied). ✓ = verified against official Paizo stat block. ≈ = estimated from standard PFS 20-point buy guidance.

| Character | Race | Class | STR | DEX | CON | INT | WIS | CHA | BAB | Fort | Ref | Will |
|-----------|------|-------|-----|-----|-----|-----|-----|-----|-----|------|-----|------|
| **Valeros** | Human | Fighter 1 | 18 | 14 | 14 | 10 | 12 | 8 | +1 ✓ | +4 ✓ | +2 ✓ | +1 ✓ |
| **Kyra** | Human | Cleric 1 | 14 | 10 | 12 | 10 | 18 | 14 | +0 ✓ | +3 ✓ | +0 ✓ | +6 ✓ |
| **Merisiel** | Elf | Rogue 1 | 10 | 20 | 12 | 14 | 10 | 14 | +0 ✓ | +1 ✓ | +7 ✓ | +0 ✓ |
| **Ezren** | Human | Wizard 1 | 10 | 14 | 12 | 18 | 12 | 11 | +0 ✓ | +1 ✓ | +2 ✓ | +3 ✓ |
| **Amiri** | Human | Barbarian 1 | 20 | 15 | 15 | 10 | 12 | 8 | +1 ≈ | +4 ≈ | +2 ≈ | +1 ≈ |
| **Harsk** | Dwarf | Ranger 1 | 14 | 16 | 16 | 10 | 14 | 6 | +1 ≈ | +5 ≈ | +5 ≈ | +2 ≈ |
| **Seoni** | Human | Sorcerer 1 | 10 | 14 | 12 | 10 | 12 | 20 | +0 ≈ | +1 ≈ | +2 ≈ | +3 ≈ |
| **Seelah** | Human | Paladin 1 | 16 | 12 | 14 | 10 | 14 | 17 | +1 ≈ | +4 ≈ | +1 ≈ | +4 ≈ |
| **Lem** | Halfling | Bard 1 | 8 | 17 | 12 | 14 | 10 | 18 | +0 ≈ | +1 ≈ | +5 ≈ | +2 ≈ |
| **Lini** | Gnome | Druid 1 | 6 | 14 | 14 | 12 | 18 | 14 | +0 ≈ | +4 ≈ | +2 ≈ | +6 ≈ |

> Note: Paladin Divine Grace (CHA to all saves) activates at **Level 2** — Level 1 saves are standard.

**Recreation checklist for PFS standard builds:**
- 20-point ability buy (PFS standard)
- Paizo-official race and class (no archetypes for core iconics)
- Starting level 1, no traits (PFS simplified)
- Weapons from CRB mundane table

## Data Sources

| Source | Format | Coverage | Status |
|--------|--------|----------|--------|
| [d20pfsrd.com](https://www.d20pfsrd.com/) | HTML (scraped) | Spells, feats, classes, races, archetypes, traits, class features | ✅ Imported |
| [PSRD-Data](https://github.com/devonjones/PSRD-Data) | JSON | Class progressions (BAB/saves/spells) for 45 CRB/APG classes | ✅ Imported |
| [Foundry VTT PF1e](https://github.com/baileymh/pf1e-content) | Foundry JSON | 21,551 records: feats, items, spells, archetypes, class abilities | ⚠️ Available — Phase 5 (feats) + Phase 6 (equipment) target |
| CoreForge spreadsheet | Excel (.xlsb) | Full rules reference — feat types, prereqs, class skills, equipment | ⚠️ Available — Phase 5 feat reimport target |

---

## Legal

All game content is Open Game Content under the **Open Game License v1.0a**.
This project uses content under the **Paizo Community Use Policy**.
Not published, endorsed, or specifically approved by Paizo Inc.
