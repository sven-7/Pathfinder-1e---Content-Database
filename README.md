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
| AC | ⚠️ Partial | DEX + size only — no armor until Phase 6 |

---

## Self-Evaluation

### What's Working
- Rules math is correct end-to-end (tested: Human Fighter 1 → BAB +1, Fort +5, Will +2, HP 13, Perception +3 ✓)
- Creator wizard is functional: create → save → sheet → level up
- Data coverage is broad across all 68 classes, all core spells, 37 playable races

### Current Gaps (honest)

**Feat picker is not useful yet (critical):** All 1,678 feats have `feat_type = 'general'`; prerequisites and benefit text are empty for core feats like Power Attack. A new player cannot tell what a feat does or whether they qualify. Phase 5 target.

**No equipment system (critical):** AC is DEX + size only. No weapons/armor to pick. Equipment is a freeform textarea. Phase 6 target.

**Class abilities not selectable at level-up (high):** The level-up wizard's Features step exists but doesn't present rage powers, rogue talents, etc. Phase 7 target.

**Sheet quality below target (high):** Current sheet is functional but plain. Missing spell dots, weapon roll blocks, resource trackers, and conditions-affecting-stats. Phase 8 target.

**3pp content not filtered (medium):** Archetypes and feats include third-party content. Phase 5 target.

---

## Known Issues

### High Priority
- Equipment is a freeform text area — no equipment DB, no AC from armor, no weapon stat blocks
- Spells are selectable in creator but no slot tracking, no prepared/spontaneous workflow on sheet
- Class abilities (rage powers, rogue talents, etc.) not selectable during level-up

### Medium Priority
- Feat data quality: no type, no prerequisites text, no benefit descriptions — picker shows names only
- 3rd-party content present in archetypes and feats — no `is_paizo_official` filter yet
- Feat-level association: tracked in JSON but not shown in creator for multi-level starting builds

### Low Priority
- Trait source encoding artifact: "Â" before © symbol
- Cross-class skill max ranks not enforced (PF1e allows it; cosmetic only)

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
