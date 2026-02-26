# Pathfinder 1e Content Database

A structured SQLite database of Pathfinder 1st Edition SRD content, designed to power character creation, level tracking, and reference tools.

## Project Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | **Data Foundation** — Import structured data from community sources | 🔧 In Progress |
| 2 | **Rules Engine** — Prerequisites, stacking, bonus calculations | ⬜ Planned |
| 3 | **Character Creator** — Race/class selection, ability scores, starting gear | ⬜ Planned |
| 4 | **Character Sheet Panel** — Single-view character management (evolve Kairon) | ⬜ Planned |
| 5 | **Level-Up Tool** — Guided leveling with auto-calculations | ⬜ Planned |
| 6 | **Integrated Web App** — Bundle everything into single reference + management tool | ⬜ Planned |

## Data Sources

| Source | Format | Coverage | Priority |
|--------|--------|----------|----------|
| [PSRD-Data](https://github.com/devonjones/PSRD-Data) | JSON + SQLite | Core, APG, ARG, Bestiaries 1-4, UC, UE, UM, GMG, etc. | Primary |
| [Foundry VTT PF1e Content](https://github.com/baileymh/pf1e-content) | Foundry JSON | ~4,200 magic items, feats, traits, equipment | Supplementary |
| [PF Spells JSON Gist](https://gist.github.com/0fdeb2da5d7b475968c8de88c75e77ad) | JSON | All OGL spells | Validation |
| [d20pfsrd.com](https://www.d20pfsrd.com/) | HTML (scrape) | Gap-filling only | Last Resort |

## Quick Start

```bash
# Clone this repo
git clone https://github.com/sven-7/Pathfinder-1e---Content-Database.git
cd Pathfinder-1e---Content-Database

# Install dependencies
pip install -r requirements.txt

# One-command setup: fetches data sources + builds database
python scripts/setup.py

# Verify
python scripts/query_test.py
```

## Project Structure

```
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   └── sources.json              # Data source URLs and config
├── schema/
│   └── pf1e_schema.sql           # SQLite schema definition
├── scripts/
│   ├── setup.py                  # One-command setup orchestrator
│   ├── fetch_sources.py          # Download/clone data repositories
│   ├── import_psrd.py            # PSRD-Data JSON → SQLite importer
│   ├── import_foundry.py         # Foundry VTT data importer (Phase 1b)
│   ├── validate.py               # Data validation & integrity checks
│   └── query_test.py             # Sample queries to verify database
├── src/
│   ├── importers/                # Data import modules
│   ├── rules_engine/             # Game rules logic (Phase 2)
│   └── api/                      # REST API layer (Phase 3+)
├── data/                         # .gitignored — local data cache
│   ├── psrd/                     # Cloned PSRD-Data repo
│   ├── foundry/                  # Cloned Foundry content
│   └── custom/                   # Manual additions
├── db/
│   └── pf1e.db                   # Generated SQLite database
└── docs/
    ├── schema_notes.md           # Schema documentation
    └── data_coverage.md          # Import coverage tracking
```

## Legal

All game content is Open Game Content under the **Open Game License v1.0a**.
This project uses content under the **Paizo Community Use Policy**.
Not published, endorsed, or specifically approved by Paizo Inc.
