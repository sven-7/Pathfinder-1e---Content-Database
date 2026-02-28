# CAMPAIGN_ARCHITECTURE.md

Defines target architecture for the campaign platform.

---

# High-Level Modules

- **API** (FastAPI): characters, rules queries, content lookup
- **Rules Engine** (Python): derived stats, budgets, prerequisites, combat math
- **Front-End** (Vanilla JS/HTML): creator wizard, sheet, level-up wizard, DM views

## Do Not Regress
- Correct rules formulas and tested behaviors (see `bugs-and-roadmap.md`).
- Cohesive UX: one app, consistent language, print-quality views.

---

# Current State (Post Phase 13)

- SQLite DB (pf1e.db, ~51MB) — read-only content (spells, feats, classes, etc.)
- PostgreSQL `pf1e_users` — users + characters (JSONB `data` column)
- JWT auth, character ownership enforced
- 6-step character creator wizard + level-up wizard
- Character sheet (standalone HTML, self-contained)
- 71 pytest tests verifying rules engine

---

# Dual Database Architecture

## SQLite (content — read-only)
- `classes`, `class_progression`, `class_features`, `archetypes`, `archetype_features`
- `feats`, `spells`, `spell_class_levels`, `races`, `traits`, `skills`, `class_skills`
- `weapons`, `armor`, `equipment`
- `search_index` (FTS5)

## PostgreSQL (app state — read/write)

### Current Tables (Phase 11)
- `users` (id, username, email, password_hash, created_at)
- `characters` (id, user_id, name, data JSONB, created_at, updated_at)

### Planned Tables (Phase 12 — Campaign Layer)
- `campaigns` (id, name, gm_user_id, created_at)
- `campaign_members` (campaign_id, user_id, role)

### Future Consideration (Phase 16+)
Normalized character storage (character_stats, character_skills, character_spells,
inventory_items as separate tables) is deferred. The JSONB approach works for
the current scale. Normalize only when query patterns demand it.

---

# Character Data Shape (JSONB)

The `characters.data` JSONB column stores the full character state:
- `ability_scores`: {str, dex, con, int, wis, cha}
- `class_levels`: [{class_name, level, archetype_name}]
- `feats`, `feat_details`: [{name, level, method}]
- `traits`: [name]
- `skills`: {skill_name: ranks}
- `class_talents`: [name]
- `spells`: {level: [name]}
- `equipped_armor`, `equipped_shield`: {armor_bonus, max_dex}
- `weapons`: [{name, damage_medium, critical, ...}]
- `fav_class_choice`: 'hp' | 'skill'
- `asi_choices`: {4: 'str', 8: 'dex', ...} — ability score increases at levels 4/8/12/16/20
- `hp_max`, `hp_current`

---

# Rules

- No rule logic in DB triggers
- No LLM validation in DB
- DB stores state only
- Python rules_engine enforces all game logic
- All rules changes require passing pytest suite

---

End
