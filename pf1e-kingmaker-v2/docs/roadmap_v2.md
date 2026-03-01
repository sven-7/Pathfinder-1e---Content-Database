# PF1e Kingmaker V2 Roadmap (Aligned 2026-03-01)

## Product Direction
- End-goal: Apple-like PWA for PF1e character + Kingmaker campaign management.
- Delivery order: single-user first, then multi-user, then DM modules.
- UI references: Pathbuilder, Pathminder, Wanderers Guide, and `kairon_v4_6.html`.
- Architecture: deterministic data + rules first, AI assist second.

## Locked Decisions
- Source strategy: `AONPRD` primary + `d20pfsrd` backup.
- Scope strategy: Kairon vertical slice first, then expansion packs.
- Stack: FastAPI + React/TypeScript + PostgreSQL.
- Deployment: Docker local-first, then private cloud.
- Rules policy: official rules baseline with explicit table overrides / house rules.
- UX target: web-first PWA usable on desktop and tablet.

## Scope Baseline (V1 Content)
- Books: Core Rulebook, APG, Ultimate Magic, Ultimate Combat, ARG, Ultimate Equipment, Ultimate Campaign, ACG, Kingmaker Player's Guide.
- Classes: full requested class list from decision profile.
- Feats: full AON feats catalog.
- Spells: full AON spells index with both short and full text.

## Current Status
1. Phase 0: Repo Bootstrap
- Status: done.
- Output: monorepo, Docker stack, CI, backend/frontend shells.

2. Phase 1: Pipeline Core
- Status: done.
- Output: deterministic `extract/parse/validate/load`, provenance schema, validations, test harness.

3. Phase 2: Kairon Slice Data
- Status: partially done.
- Output done: deterministic Kairon slice ingestion with strict gates.
- Gap to close: source adapter pivot from current transitional source path to `AON primary + d20 backup`.

4. Phase 3: Rules Engine V2
- Status: baseline done for Kairon slice.
- Output: deterministic derive with explainable breakdowns, feat prereq evaluation.
- Gap to close: extend coverage beyond slice classes/effects.

5. Phase 4: API V2 Contract Layer
- Status: in progress.
- Target: stable `/api/v2/content/*`, `/api/v2/characters/*`, `/api/v2/rules/derive` contracts with seeded contract tests.

6. Phase 5: React PWA Character MVP
- Status: pending.
- Target: creator/library/sheet + offline shell.

7. Phase 6: Kairon Parity Layer
- Status: pending.
- Target: conditions/resources/spell tracking + quick combat/cheat sheet parity.

8. Phase 7: Multi-User Foundation
- Status: pending.
- Target: authn, roles, campaign membership, optimistic locking, audit trail.

9. Phase 8: Kingmaker Modules
- Status: pending.
- Target: party/campaign/kingdom/NPC modules and DM views.

## Next 2 Sprints (Execution)
1. Build AON extractor + d20 fallback resolver with deterministic conflict policy.
2. Seed catalog for approved books/classes/feats/spells with allowlist gating.
3. Add short-description extraction pipeline for spells and feats.
4. Add house-rule model (data + API) with deterministic override application order.
5. Expand API V2 content endpoints and contract tests.
6. Start React PWA character create/library/sheet flow on the stabilized contracts.
