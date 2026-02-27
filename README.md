# Pathfinder 1e Content Database

A structured SQLite database of Pathfinder 1st Edition SRD content, powering a local character creation and management web app.

---

## Project Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | **Data Foundation** — Scrape & import content into SQLite | ✅ Complete |
| 2 | **Rules Engine** — BAB/saves/HP/skills/prerequisites/combat | ✅ Complete |
| 3 | **Character Creator GUI** — FastAPI + vanilla JS wizard | ✅ Complete (v1) |
| 4 | **Data Layer Audit** — Fill coverage gaps, validate accuracy | 🔧 In Progress |
| 5 | **Sheet & Level-Up Polish** — Spells panel, weapons, full export | ⬜ Planned |
| 6 | **Feat/Skill Intelligence** — Prerequisite enforcement, auto-suggestions | ⬜ Planned |

---

## Quick Start

```bash
git clone https://github.com/sven-7/Pathfinder-1e---Content-Database.git
cd "Pathfinder-1e---Content-Database"

pip install -r requirements.txt

# Launch the character creator (opens browser at http://localhost:8000)
python scripts/run_app.py
```

---

## What's Been Built

### Phase 1 — Data Foundation
- SQLite database (`db/pf1e.db`, ~48 MB) built from d20pfsrd.com scraping
- **Content counts:** 2,921 spells · 1,678 feats · 68 classes · 1,306 archetypes · 5,816 archetype features · 2,653 class features · 423 races · 1,176 traits
- **Class progression:** 1,180 rows covering BAB, saves, and spell slots across all 68 classes (45 from PSRD JSON, 23 computed from formulas)
- Scrapers in `src/scrapers/` for spells, feats, classes, races, archetypes, traits, class features
- Import pipeline in `scripts/import_scraped.py`

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
| `__init__.py` | Public API surface |

### Phase 3 — Character Creator GUI
Local web app at `http://localhost:8000`:

**5-step creation wizard:**
1. **Origins** — Name, alignment, starting level, race picker (37 canonical races grouped Core/Featured/Uncommon), class picker with archetype dropdown
2. **Abilities** — Standard Array / Point Buy (25pt) / Roll 4d6 / Manual entry; racial mods applied live
3. **Feats & Traits** — Filterable feat browser (1,678 feats); trait browser (1,176 traits); budget scales with level
4. **Skills** — Rank allocator with class skill highlighting; budget = `(ranks/lvl + INT mod) × level`
5. **Review** — Full stat preview; Save & View Sheet / Download JSON / Save to Library

**Starting Level support:** Set 1–20 for mid-campaign characters. Feat budget, skill budget, HP, and max ranks per skill all scale correctly.

**Character sheet** (`/sheet`) — Derived stats, HP tracker, conditions, dice roller, print stylesheet, Level Up button

**Level-up wizard** (`/levelup`) — 7-step flow: HP → Ability (4/8/12/16/20) → Skills → Feat → Features → Review → Export

**Character history** — Recent saves persist in localStorage with quick Sheet / Level Up links

---

## Project Structure

```
├── README.md
├── requirements.txt
├── .gitignore
│
├── db/
│   └── pf1e.db                       # SQLite database (~48 MB)
│
├── src/
│   ├── api/
│   │   ├── app.py                    # FastAPI app, lifespan, routes
│   │   └── routes/
│   │       ├── races.py              # GET /api/races (37 canonical playable)
│   │       ├── classes.py            # GET /api/classes, archetypes, progression
│   │       ├── feats.py              # GET /api/feats (search, type filter)
│   │       ├── skills.py             # GET /api/skills, class skills
│   │       ├── traits.py             # GET /api/traits
│   │       └── characters.py         # CRUD /api/characters, sheet HTML export
│   │
│   ├── character_creator/
│   │   ├── builder.py                # CharacterBuilder wizard logic
│   │   ├── ability_scores.py         # standard_array, point_buy, roll_4d6
│   │   └── exporter.py               # generate_sheet_html() → standalone HTML
│   │
│   ├── rules_engine/                 # Phase 2 library (see above)
│   │   └── ...
│   │
│   └── scrapers/                     # d20pfsrd.com scrapers
│       ├── base.py
│       ├── spell_parser.py
│       ├── feat_parser.py
│       ├── class_parser.py
│       ├── race_parser.py
│       ├── archetype_parser.py
│       ├── trait_parser.py
│       └── class_feature_parser.py
│
├── static/
│   ├── creator.html                  # Character creation wizard
│   ├── sheet.html                    # Character sheet template
│   ├── levelup.html                  # Level-up wizard
│   ├── css/
│   │   ├── parchment.css             # Shared design tokens (Cinzel/Crimson Text)
│   │   ├── creator.css
│   │   └── sheet.css
│   └── js/
│       └── creator.js                # Wizard state machine
│
├── scripts/
│   ├── run_app.py                    # python scripts/run_app.py → opens browser
│   ├── scrape_d20pfsrd.py            # Main scraper orchestrator
│   ├── import_scraped.py             # JSON → SQLite importer
│   ├── import_class_progressions.py  # PSRD class progression importer
│   └── scrape_missing_archetypes.py  # Gap-fill archetype scraper
│
├── characters/                       # Saved character JSON files (gitignored)
│   └── *.json
│
├── data/
│   ├── psrd/                         # PSRD-Data source JSONs
│   ├── foundry/                      # Foundry VTT PF1e content
│   └── foundry-archetypes/           # Foundry archetype data
│
└── example_content/                  # Reference files (gitignored)
    ├── kairon_v4_6.html              # Reference character sheet
    ├── kairon_levelup.html           # Reference level-up wizard
    └── Pathfinder-sCoreForge-7.4.0.1.xlsb  # PF1e rules reference spreadsheet
```

---

## Known Data Gaps (Phase 4 Targets)

### High Priority
| Gap | Impact | Notes |
|-----|--------|-------|
| `class_skills` table is empty | No +3 trained bonus applied | Skills API returns totals without trained bonus |
| Spell slots NULL for ACG/OA classes | Spellcasting classes show no slot data | PSRD only covers CRB/APG classes |
| Race descriptions thin | Wizard previews show no flavour text | Scraped data incomplete |
| `ability_modifiers` NULL in DB | Handled by hardcode in `races.py` | 37 playable races work; all others excluded |
| Race `race_type` NULL for all 423 rows | Handled by whitelist in `races.py` | Non-playable rows silently excluded |

### Medium Priority
| Gap | Impact | Notes |
|-----|--------|-------|
| Arcanist exploit parse rate ~30% | Missing ~18 exploits | Prose format, no "Benefit:" label |
| Kineticist wild talents: 0 URLs found | No wild talent data | Index page structure differs from other classes |
| Ranger combat styles: 0 URLs | Missing combat style feats | Same issue |
| Witch hexes: sub-category pages only | Hex descriptions missing | Deeper crawl needed |
| Warpriest blessings: 404s | No blessing data | Index page structure changed |

### Low Priority
- `sources` table missing Paizo book names for ~40% of feats (source_id NULL)
- Trait source field has "Â" encoding artifact before copyright symbol
- Cross-class skill max ranks not enforced in creator (PF1e allows it, so cosmetic only)
- No item/equipment database (weapons, armour, gear)

---

## Data Sources

| Source | Format | Coverage | Status |
|--------|--------|----------|--------|
| [d20pfsrd.com](https://www.d20pfsrd.com/) | HTML (scraped) | Spells, feats, classes, races, archetypes, traits, class features | ✅ Imported |
| [PSRD-Data](https://github.com/devonjones/PSRD-Data) | JSON | Class progressions (BAB/saves/spells) for 45 CRB/APG classes | ✅ Imported |
| [Foundry VTT PF1e](https://github.com/baileymh/pf1e-content) | Foundry JSON | Archetypes, class features (available in `data/foundry/`) | ⬜ Not yet evaluated |
| CoreForge spreadsheet | Excel (.xlsb) | Full rules reference, ability mods, race data | ✅ Used for validation |

---

## Legal

All game content is Open Game Content under the **Open Game License v1.0a**.
This project uses content under the **Paizo Community Use Policy**.
Not published, endorsed, or specifically approved by Paizo Inc.
