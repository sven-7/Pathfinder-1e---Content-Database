# Acceptance Checklist

## Milestone 1: Kairon Vertical Slice
- [x] Pipeline rejects junk feat records (`Feat Name`, `Benefit`, `Table: Feats`).
- [x] All ingested races have one or more linked racial traits.
- [x] `Weapon Finesse`, `Weapon Focus`, `Rapid Shot` are present and queryable.
- [x] Every content row has ingestion provenance fields.
- [x] `/api/v2/rules/derive` returns deterministic Kairon L9 baseline values with explainable breakdowns.
- [x] CI runs deterministic tests on every merge.

## Milestone 2: Source and Catalog Alignment
- [ ] AONPRD adapter is primary extractor for approved books/classes/feats/spells.
- [ ] d20 fallback resolver is deterministic and logged per record.
- [ ] Source conflict policy is implemented and reproducible.
- [ ] Spell rows include both short description and full detail content.
- [ ] Feat rows include clean short summary and detailed body content.
- [ ] Approved-book allowlist blocks out-of-scope records.

## Milestone 3: Rules and Product Foundation
- [ ] House-rule/override model exists in data + API contracts.
- [ ] Derivation applies overrides in explicit order with full breakdown trace.
- [ ] Character lifecycle supports create/update/level-up snapshots.
- [ ] Data/contracts are compatible with later multi-user roles and DM modules.
