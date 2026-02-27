"""Read-only DB access layer for the rules engine."""

import sqlite3
from typing import Any


class RulesDB:
    """Wraps a read-only SQLite connection. All queries return plain dicts."""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
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

    def _one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        row = self._conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _many(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
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
    # Full-text search                                                     #
    # ------------------------------------------------------------------ #

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """FTS5 search across all content types."""
        return self._many(
            "SELECT * FROM search_index WHERE search_index MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        )
