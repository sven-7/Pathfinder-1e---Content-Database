# Release Readiness Report - 2026-03-02

Branch: `codex/release-hardening`  
Scope: integration/runtime hardening only (no ingestion expansion)

## Gate Matrix

| Gate | Command | Result |
| --- | --- | --- |
| Backend (requested API/contracts/rules/campaign set in Docker runtime) | `docker compose -f pf1e-kingmaker-v2/docker-compose.yml run --rm -v <repo>:/workspace -w /workspace/pf1e-kingmaker-v2/backend api pytest -q tests/test_api_v2.py tests/test_api_v2_contracts_static.py tests/test_rules_engine_v2.py tests/test_rule_override_precedence.py tests/test_campaign_api_v2.py` | PASS (`21 passed in 0.25s`) |
| Backend (full suite in Docker runtime, skip-elimination check) | `docker compose -f pf1e-kingmaker-v2/docker-compose.yml run --rm -v <repo>:/workspace -w /workspace/pf1e-kingmaker-v2/backend api pytest -q` | PASS (`35 passed in 0.35s`, `0 skipped`) |
| Frontend production build | `npm -C pf1e-kingmaker-v2/frontend run build` | PASS (`vite build` completed) |
| Frontend Playwright smoke | `npm -C pf1e-kingmaker-v2/frontend run test:e2e` | PASS (`1 passed`) |
| Runtime stack bring-up | `docker compose -f pf1e-kingmaker-v2/docker-compose.yml up -d --build` | PASS (`db`, `api`, `web` up) |
| Health endpoint | `curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:8100/health` | PASS (`HTTP 200`) |
| DM campaign shell live API flow | `POST /api/v2/campaigns -> POST /api/v2/parties -> POST /api/v2/sessions -> POST /api/v2/sessions/{id}/encounters -> GET /api/v2/sessions/{id}` | PASS (`201/200` responses with persisted IDs) |

## Integration Regressions Found and Fixed

1. Pydantic model construction failed in Docker test runtime (`AbilityScoresV2` field-name annotation clash with `str`/`int`).
   - Fix: switched to alias-backed internal fields (`str_score`/`int_score`) with stable external JSON keys.
2. Rules engine ability score references broke after alias migration.
   - Fix: updated engine accessors to `str_score`/`int_score`.
3. Contract/API mismatch from rules breakdown key drift.
   - Fix: restored legacy `AC(total)` breakdown key alongside `AC:total`.
4. Rules engine override processing failed when overrides were plain dicts.
   - Fix: normalize override entries via `RuleOverrideV2.model_validate(...)` before evaluation.
5. OpenAPI schema names diverged from contract test expectations.
   - Fix: set `separate_input_output_schemas=False` on FastAPI app.

## Container Runtime Evidence

- `docker compose ps` shows stable running containers:
  - `pf1e-kingmaker-v2-api-1` (port `8100`)
  - `pf1e-kingmaker-v2-web-1` (port `5174`)
  - `pf1e-kingmaker-v2-db-1` (port `5433`)
- `docker compose logs --tail=80 api web` shows clean startup and successful health + campaign-shell request handling.

## Known Limitations

1. The frontend Playwright smoke uses route mocking and validates UI workflow/state persistence, not real API-backed character CRUD.
2. Character CRUD endpoints (`/api/v2/characters` create/update/get/list) are not currently implemented in backend V2 routes; only `/api/v2/characters/validate` is present.
3. This hardening pass intentionally does not expand ingestion/catalog scope.

## Merge Recommendation

Recommendation: **merge to `main`**.

Rationale:
- All required release gates passed.
- No critical failing tests.
- API and web containers are stable in Docker.
- DM campaign shell flow verified live against running API.
- Regressions found during hardening were fixed and revalidated in dependency-complete Docker runtime.
