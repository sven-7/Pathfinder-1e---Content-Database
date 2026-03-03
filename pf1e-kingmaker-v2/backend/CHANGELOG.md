# Backend Changelog

## 2026-03-03

- Replaced in-memory campaign/domain persistence with SQLAlchemy-backed repositories and service wiring.
- Added app-domain migrations for `campaigns`, `parties`, `party_members`, `sessions`, `encounters`, `rule_overrides`, `characters`, and `character_snapshots`.
- Implemented `/api/v2/characters` CRUD endpoints (`POST`, `GET by id`, `GET list`, `PUT`, `DELETE`) with DB persistence.
- Kept `/api/v2/characters/validate` and `/api/v2/rules/derive` compatible with stored `CharacterV2` payloads.
- Restored and DB-backed `/api/v2/campaigns`, `/api/v2/parties`, and `/api/v2/sessions` endpoints.
- Added repository/service tests, API contract tests, and Docker integration evidence.
