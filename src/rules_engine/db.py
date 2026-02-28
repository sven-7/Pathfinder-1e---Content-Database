"""Read-only DB access layer for the rules engine.

Supports two backends:
  - SQLite  (default) — file:path?mode=ro
  - PostgreSQL        — postgresql://... DSN via psycopg2
"""

import re
import sqlite3
from typing import Any


class RulesDB:
    """Wraps a read-only database connection. All queries return plain dicts."""

    def __init__(self, dsn: str):
        self._pg = dsn.startswith("postgresql://") or dsn.startswith("postgres://")
        if self._pg:
            import psycopg2
            import psycopg2.extras
            self._conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)
            self._conn.set_session(readonly=True, autocommit=True)
        else:
            self._conn = sqlite3.connect(f"file:{dsn}?mode=ro", uri=True)
            self._conn.row_factory = sqlite3.Row

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _tbl(self, name: str) -> str:
        """Return schema-qualified table name for PG, bare name for SQLite."""
        return f"content.{name}" if self._pg else name

    def _normalize_sql(self, sql: str) -> str:
        """Convert SQLite ? placeholders to %s for psycopg2."""
        if self._pg:
            return sql.replace("?", "%s")
        return sql

    def _qualify_tables(self, sql: str) -> str:
        """Prefix bare content table names with 'content.' for PG backend."""
        if not self._pg:
            return sql
        tables = [
            "sources", "classes", "class_skills", "class_features",
            "class_progression", "archetypes", "archetype_features",
            "races", "racial_traits", "feats", "skills", "spells",
            "spell_class_levels", "equipment", "weapons", "armor",
            "magic_items", "monsters", "traits", "search_index",
        ]
        result = sql
        for t in tables:
            # Match table names at word boundaries, but not already prefixed
            result = re.sub(
                rf'(?<!content\.)(?<!\w){re.escape(t)}(?=\s|[,;).]|$)',
                f'content.{t}',
                result,
            )
        return result

    def _one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        sql = self._qualify_tables(self._normalize_sql(sql))
        if self._pg:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            cur.close()
            return dict(row) if row else None
        else:
            row = self._conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def _many(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        sql = self._qualify_tables(self._normalize_sql(sql))
        if self._pg:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
        else:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    # ------------------------------------------------------------------ #
    # Feats                                                                #
    # ------------------------------------------------------------------ #

    def get_feat(self, name: str) -> dict | None:
        return self._one("SELECT * FROM feats WHERE name = ?", (name,))

    def get_all_feats(self) -> list[dict]:
        return self._many("SELECT * FROM feats ORDER BY name")

    # ------------------------------------------------------------------ #
    # Classes                                                              #
    # ------------------------------------------------------------------ #

    def get_class(self, name: str) -> dict | None:
        return self._one("SELECT * FROM classes WHERE name = ?", (name,))

    def get_all_classes(self) -> list[dict]:
        return self._many("SELECT * FROM classes ORDER BY name")

    def get_class_features(self, class_id: int) -> list[dict]:
        return self._many(
            "SELECT * FROM class_features WHERE class_id = ? ORDER BY level, name",
            (class_id,),
        )

    def get_class_skills(self, class_id: int) -> list[dict]:
        return self._many(
            """SELECT s.id, s.name FROM skills s
               JOIN class_skills cs ON cs.skill_id = s.id
               WHERE cs.class_id = ?
               ORDER BY s.name""",
            (class_id,),
        )

    def get_class_progression(self, class_id: int) -> list[dict]:
        return self._many(
            "SELECT * FROM class_progression WHERE class_id = ? ORDER BY level",
            (class_id,),
        )

    def get_archetypes_for_class(self, class_name: str) -> list[dict]:
        return self._many(
            """SELECT a.* FROM archetypes a
               JOIN classes c ON c.name = ?
               WHERE a.parent_class = ?
               ORDER BY a.name""",
            (class_name, class_name),
        )

    def get_archetype(self, name: str) -> dict | None:
        return self._one("SELECT * FROM archetypes WHERE name = ?", (name,))

    def get_archetype_for_class(self, class_name: str, archetype_name: str) -> dict | None:
        """Look up an archetype by class + archetype name."""
        return self._one(
            """SELECT a.* FROM archetypes a
               JOIN classes c ON c.id = a.class_id
               WHERE c.name = ? AND a.name = ?""",
            (class_name, archetype_name),
        )

    def get_archetype_features(self, archetype_id: int) -> list[dict]:
        """Return all features for an archetype, ordered by level."""
        return self._many(
            "SELECT * FROM archetype_features WHERE archetype_id = ? ORDER BY level",
            (archetype_id,),
        )

    # ------------------------------------------------------------------ #
    # Skills                                                               #
    # ------------------------------------------------------------------ #

    def get_skill(self, name: str) -> dict | None:
        return self._one("SELECT * FROM skills WHERE name = ?", (name,))

    def get_all_skills(self) -> list[dict]:
        return self._many("SELECT * FROM skills ORDER BY name")

    # ------------------------------------------------------------------ #
    # Spells                                                               #
    # ------------------------------------------------------------------ #

    def get_spell(self, name: str) -> dict | None:
        return self._one("SELECT * FROM spells WHERE name = ?", (name,))

    def get_spells_for_class(self, class_name: str, level: int | None = None) -> list[dict]:
        if level is not None:
            return self._many(
                """SELECT s.* FROM spells s
                   JOIN spell_class_levels scl ON scl.spell_id = s.id
                   WHERE scl.class_name = ? AND scl.level = ?
                   ORDER BY s.name""",
                (class_name, level),
            )
        return self._many(
            """SELECT s.*, scl.level as spell_level FROM spells s
               JOIN spell_class_levels scl ON scl.spell_id = s.id
               WHERE scl.class_name = ?
               ORDER BY scl.level, s.name""",
            (class_name,),
        )

    # ------------------------------------------------------------------ #
    # Races                                                                #
    # ------------------------------------------------------------------ #

    def get_race(self, name: str) -> dict | None:
        return self._one("SELECT * FROM races WHERE name = ?", (name,))

    # ------------------------------------------------------------------ #
    # Traits                                                               #
    # ------------------------------------------------------------------ #

    def get_trait(self, name: str) -> dict | None:
        return self._one("SELECT * FROM traits WHERE name = ?", (name,))

    # ------------------------------------------------------------------ #
    # Equipment                                                            #
    # ------------------------------------------------------------------ #

    def get_weapons(self) -> list[dict]:
        """Return all weapons joined with equipment base data."""
        return self._many(
            """SELECT e.id as equipment_id, e.name, e.cost, e.weight,
                      w.id as weapon_id, w.proficiency, w.weapon_type, w.handedness,
                      w.damage_small, w.damage_medium, w.critical,
                      w.range_increment, w.damage_type, w.special
               FROM weapons w
               JOIN equipment e ON e.id = w.equipment_id
               WHERE w.weapon_type != 'ammunition'
               ORDER BY w.proficiency, w.handedness, e.name"""
        )

    def get_armor(self) -> list[dict]:
        """Return all armor/shields joined with equipment base data."""
        return self._many(
            """SELECT e.id as equipment_id, e.name, e.cost, e.weight,
                      a.id as armor_id, a.armor_type, a.armor_bonus, a.max_dex,
                      a.armor_check_penalty, a.arcane_spell_failure,
                      a.speed_30, a.speed_20
               FROM armor a
               JOIN equipment e ON e.id = a.equipment_id
               ORDER BY a.armor_type, a.armor_bonus, e.name"""
        )

    # ------------------------------------------------------------------ #
    # Full-text search                                                     #
    # ------------------------------------------------------------------ #

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search across all content types."""
        if self._pg:
            return self._many(
                """SELECT name, content_type, description, source, content_id,
                          ts_rank(tsv, plainto_tsquery('english', %s)) AS rank
                   FROM content.search_index
                   WHERE tsv @@ plainto_tsquery('english', %s)
                   ORDER BY rank DESC
                   LIMIT %s""",
                (query, query, limit),
            )
        return self._many(
            "SELECT * FROM search_index WHERE search_index MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        )
