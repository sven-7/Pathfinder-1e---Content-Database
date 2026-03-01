# Pack B: Ingestion Framework

## Objective
Implement deterministic `extract -> parse -> validate -> load` pipeline with provenance.

## Source Policy
- Primary source: `https://aonprd.com`.
- Backup source: `https://www.d20pfsrd.com`.
- Conflict policy:
  1. Prefer AON record when complete.
  2. Use d20 record only for missing required fields.
  3. Log fallback reason and source ranking decision in run metadata.

## Tasks
1. Add CLI with subcommands.
2. Persist raw source snapshots and stable hashes.
3. Normalize parsed records into canonical shapes.
4. Enforce validation gates (junk rows, relational quality checks).
5. Load accepted records with `ingestion_runs` and `source_records` links.
6. Store both short and full descriptions for feats/spells where source provides them.
7. Add allowlist filtering for approved books/classes from decision profile.
8. Emit deterministic conflict-resolution report per ingestion run.

## Required Outputs
- CLI command set.
- Validation report + rejection report.
- Deterministic run manifest.
- Source resolution report (`aon_used`, `d20_used`, `fallback_reasons`).
