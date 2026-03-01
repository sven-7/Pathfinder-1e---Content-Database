# Acceptance Checklist (Milestone 1)

- [ ] Pipeline rejects junk feat records (`Feat Name`, `Benefit`, `Table: Feats`).
- [ ] All ingested races have one or more linked racial traits.
- [ ] `Weapon Finesse`, `Weapon Focus`, `Rapid Shot` are present and queryable.
- [ ] Every content row has ingestion provenance fields.
- [ ] `/api/v2/rules/derive` returns deterministic Kairon L9 baseline values.
- [ ] CI runs deterministic tests on every merge.
