# Pack A: Repo + Infra

## Objective
Scaffold monorepo foundations for PF1e Kingmaker V2 with explicit extension points for future multi-user and DM modules.

## Inputs
- Existing repo for reference only.
- Target: FastAPI backend + React/TS frontend + Docker + CI.
- Decision profile: `docs/decision_profile_2026_03_01.md`.

## Tasks
1. Create root structure: backend, frontend, docs, prompts, infra.
2. Add docker-compose for db/api/web.
3. Add CI workflow for backend tests and frontend build.
4. Add startup README with exact commands.
5. Add architecture notes for future auth/campaign roles (`single-user now`, `multi-user later`).
6. Add migration convention (`0001_init.sql`, `0002_*.sql`) and service boundaries (`ingestion`, `rules`, `api`, `ui`).

## Required Outputs
- Working compose stack definition.
- CI workflow file.
- Run instructions.
- Future-extension diagram or text map for multi-user + DM modules.
