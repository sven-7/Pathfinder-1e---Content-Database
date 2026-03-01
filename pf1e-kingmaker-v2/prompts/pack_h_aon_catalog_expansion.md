# Pack H: AON Catalog Expansion

## Objective
Expand from Kairon slice to approved PF1e catalog using AON primary and d20 fallback.

## Inputs
- `docs/decision_profile_2026_03_01.md`
- Approved books/classes list.
- AON feats and spells indexes:
  - `https://aonprd.com/Feats.aspx`
  - `https://aonprd.com/Spells.aspx?Class=All`

## Tasks
1. Crawl/ingest approved books and classes only.
2. Ingest feats and spells with:
   - short summary text
   - full details
   - provenance fields
3. Resolve missing/partial fields from d20 with fallback logs.
4. Build incremental pack ingestion (`book_pack` argument) for staged rollout.
5. Run validation and emit missing-item reports per content family.

## Required Outputs
- Per-table row counts.
- Missing-record report for requested classes/books.
- Source-resolution report showing AON vs d20 usage.
- Deterministic fixture snapshots for CI regression.
