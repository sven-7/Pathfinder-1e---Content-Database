# Pack B: Ingestion Framework

## Objective
Implement deterministic `extract -> parse -> validate -> load` pipeline with provenance.

## Tasks
1. Add CLI with subcommands.
2. Persist raw source snapshots and stable hashes.
3. Normalize parsed records into canonical shapes.
4. Enforce validation gates (junk rows, relational quality checks).
5. Load accepted records with `ingestion_runs` and `source_records` links.

## Required Outputs
- CLI command set.
- Validation report + rejection report.
- Deterministic run manifest.
