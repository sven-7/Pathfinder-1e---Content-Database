# PF1e Kingmaker V2

Data-first Pathfinder 1e rebuild with deterministic ingestion, strict validation, and versioned APIs.

## Scope Implemented In This Bootstrap
- Phase 0 foundations: monorepo structure, Docker, CI, FastAPI + React shells.
- Phase 1 foundations: deterministic `extract -> parse -> validate -> load` pipeline with provenance tables.
- V2 contracts and API namespace: `/api/v2/content/*`, `/api/v2/characters/*`, `/api/v2/rules/derive`.
- Milestone prompt packs in `prompts/`.

## Repository Layout
- `backend/` FastAPI API, ingestion pipeline, migrations, tests.
- `frontend/` React + TypeScript app shell (PWA-oriented).
- `docs/` rollout and acceptance docs.
- `prompts/` milestone prompt packs for Claude/Codex.

## Quick Start

```bash
cd pf1e-kingmaker-v2
cp .env.example .env

docker compose up --build
```

Services:
- API: `http://localhost:8100`
- Web: `http://localhost:5174`
- Postgres: `localhost:5433`

## Backend Local Development

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run tests
pytest -q

# run api
uvicorn app.main:app --reload --port 8100
```

## Ingestion CLI

```bash
cd backend
python3 -m app.pipeline.cli extract --source aon --mode aon_live --ai-short-fallback --run-dir ./runs
python3 -m app.pipeline.cli parse --run ./runs/<run_id>
python3 -m app.pipeline.cli validate --run ./runs/<run_id>
python3 -m app.pipeline.cli load --run ./runs/<run_id> --dsn sqlite:///./runs/dev_v2.db
```

Catalog expansion (approved classes/feats/spells from AON indexes):

```bash
python3 -m app.pipeline.cli extract --source aon --mode aon_catalog --catalog-kind all --catalog-limit 0 --ai-short-fallback --run-dir ./runs
```

Two-tier policy behavior in `aon_catalog`:
- Records are no longer dropped by allowlist checks.
- Each record is tagged in `source_records` with:
  - `ui_enabled` (`true/false`)
  - `ui_tier` (`active` or `deferred`)
  - `policy_reason` (for example `allowlisted`, `book_not_in_allowlist`, `class_not_in_allowlist`)
- Canonical tables link back via `source_record_id`, so UI/API layers can gate deferred content without losing data.

Fixture mode (CI/local quick checks without source databases):

```bash
python3 -m app.pipeline.cli extract --source psrd --mode kairon_fixture --run-dir ./runs
```

## Notes
- The load step supports `sqlite:///...` directly for deterministic test runs.
- PostgreSQL loading is supported when `psycopg` is installed and a PostgreSQL DSN is provided.
- The schema migration is in `backend/migrations/0001_init.sql`.
- `/api/v2/rules/derive` now computes deterministic Kairon-slice stats including AC/CMB/CMD, spell slots, skill totals, attack lines, and feat prerequisite evaluation results.
- `/api/v2/characters/validate` returns prereq validation with explicit invalid feat reasons.
- Source strategy target is `AONPRD primary + d20 fallback` (see decision profile in `docs/decision_profile_2026_03_01.md`).
- `aon_live` mode archives raw HTML snapshots under `runs/<run>/raw/html/*.html` and logs fetch metadata in `aon_fetch_log.jsonl`.
- Baseline snapshot summary for the first full live catalog run is stored in `backend/baselines/aon_catalog_live_v1_summary.json`.
- If `OPENAI_API_KEY` is not available, short-description generation falls back to deterministic first-sentence heuristics.
