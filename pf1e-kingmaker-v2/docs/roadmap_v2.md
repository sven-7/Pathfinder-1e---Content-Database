# PF1e Kingmaker V2 Roadmap

## Locked Decisions
- New separate repo path.
- PSRD baseline + curated d20 gap fill.
- Kairon vertical slice first.
- FastAPI + React/TS.
- Docker local-first, private cloud later.
- In-app AI after deterministic rules baseline.

## Delivered In Bootstrap
- Phase 0 scaffold complete.
- Phase 1 framework complete (`extract/parse/validate/load`).
- V2 API route shell complete.
- Contract models complete (`CharacterV2`, `DerivedStatsV2`).

## Immediate Next Work
1. Finish PostgreSQL loader implementation parity.
2. Expand parser adapters for real PSRD and d20 raw inputs.
3. Add Kairon fixture ingestion assertions for all expected entities.
4. Implement full deterministic rules engine package with source-backed effect deltas.
