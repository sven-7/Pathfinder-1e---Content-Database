# Database Schema Notes

## Design Principles

1. **SQLite-first** — Zero config, single file, portable. Can migrate to PostgreSQL later if needed.
2. **Normalized where practical** — Spell-class-level relationships are junction tables, but we keep denormalized text fields (like `prerequisites` on feats) because PF1e data is messy and not always machine-parseable.
3. **HTML preserved in description fields** — The source data includes HTML formatting. We store both raw HTML (in `description`) and could add plain-text columns later. The search index uses stripped text.
4. **FTS5 search index** — Full-text search across all content types. Query with `SELECT * FROM search_index WHERE search_index MATCH 'fireball'`.

## Key Relationships

```
sources ──┬── classes ──── class_features
          │             └── class_skills ── skills
          │             └── class_progression
          ├── archetypes ── archetype_features
          ├── races ────── racial_traits
          ├── feats
          ├── spells ───── spell_class_levels
          ├── equipment ─┬─ weapons
          │              └─ armor
          ├── magic_items
          └── monsters
```

## PSRD-Data JSON Type Mapping

| PSRD `type` field | Target table | Notes |
|-------------------|-------------|-------|
| spell | spells | Has school, level, components, etc. |
| feat | feats | Prerequisites in nested sections |
| skill | skills | Ability scores hardcoded in importer |
| class | classes | Features in nested sections |
| creature | monsters | CR can be fractional |
| race | races | Traits in nested sections |
| section | (various) | Generic container — routed by directory path |

## Known Limitations

- **Class progression tables** — PSRD-Data stores these as HTML tables in body text. Parsing BAB/saves per level requires HTML table extraction. Phase 1 imports the raw data; Phase 2 will parse progression tables.
- **Feat prerequisites** — Stored as raw text. Machine-readable prerequisite parsing is a Phase 2 rules engine task.
- **Archetype feature replacements** — Not always explicitly marked in source data. May need manual curation.
- **Spell descriptions** — Some contain HTML entities (em-dashes, etc.) that need normalization.
