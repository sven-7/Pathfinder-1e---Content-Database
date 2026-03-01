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
python -m app.pipeline.cli extract --source psrd --mode kairon_slice --psrd-root ../../data/psrd --d20-root ../../data/d20pfsrd --run-dir ./runs
python -m app.pipeline.cli parse --run ./runs/<run_id>
python -m app.pipeline.cli validate --run ./runs/<run_id>
python -m app.pipeline.cli load --run ./runs/<run_id> --dsn sqlite:///./runs/dev_v2.db
```

Fixture mode (CI/local quick checks without source databases):

```bash
python -m app.pipeline.cli extract --source psrd --mode kairon_fixture --run-dir ./runs
```

## Notes
- The load step supports `sqlite:///...` directly for deterministic test runs.
- PostgreSQL loading is supported when `psycopg` is installed and a PostgreSQL DSN is provided.
- The schema migration is in `backend/migrations/0001_init.sql`.
