"""Load step: accepted records -> canonical tables with provenance."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Literal

from app.pipeline.utils import read_json, read_jsonl


Engine = Literal["sqlite", "postgres"]


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_key TEXT NOT NULL UNIQUE,
  started_at TEXT,
  source_name TEXT,
  source_version TEXT,
  git_sha TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS source_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ingestion_run_id INTEGER NOT NULL,
  source_url TEXT,
  source_book TEXT,
  raw_hash TEXT,
  parse_status TEXT,
  reject_reason TEXT,
  content_type TEXT,
  raw_payload TEXT,
  UNIQUE(ingestion_run_id, raw_hash)
);

CREATE TABLE IF NOT EXISTS classes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  class_type TEXT,
  hit_die TEXT,
  skill_ranks_per_level INTEGER,
  bab_progression TEXT,
  fort_progression TEXT,
  ref_progression TEXT,
  will_progression TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT
);

CREATE TABLE IF NOT EXISTS class_progression (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  class_name TEXT NOT NULL,
  level INTEGER NOT NULL,
  bab INTEGER NOT NULL,
  fort_save INTEGER NOT NULL,
  ref_save INTEGER NOT NULL,
  will_save INTEGER NOT NULL,
  special TEXT,
  spells_per_day TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT,
  UNIQUE(class_name, level)
);

CREATE TABLE IF NOT EXISTS class_features (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  class_name TEXT NOT NULL,
  name TEXT NOT NULL,
  level INTEGER,
  feature_type TEXT,
  description TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT,
  UNIQUE(class_name, name, level)
);

CREATE TABLE IF NOT EXISTS races (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  race_type TEXT,
  size TEXT,
  base_speed INTEGER,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT
);

CREATE TABLE IF NOT EXISTS racial_traits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_name TEXT NOT NULL,
  name TEXT NOT NULL,
  trait_type TEXT,
  description TEXT,
  replaces TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT,
  UNIQUE(race_name, name)
);

CREATE TABLE IF NOT EXISTS feats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  feat_type TEXT,
  prerequisites TEXT,
  benefit TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT
);

CREATE TABLE IF NOT EXISTS traits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  trait_type TEXT,
  prerequisites TEXT,
  benefit TEXT,
  description TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT
);

CREATE TABLE IF NOT EXISTS spells (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  school TEXT,
  description TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT
);

CREATE TABLE IF NOT EXISTS spell_class_levels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spell_name TEXT NOT NULL,
  class_name TEXT NOT NULL,
  level INTEGER NOT NULL,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT,
  UNIQUE(spell_name, class_name)
);

CREATE TABLE IF NOT EXISTS equipment (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  equipment_type TEXT,
  cost TEXT,
  weight REAL,
  description TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT
);

CREATE TABLE IF NOT EXISTS weapons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_name TEXT NOT NULL UNIQUE,
  proficiency TEXT,
  weapon_type TEXT,
  handedness TEXT,
  damage_medium TEXT,
  critical TEXT,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT
);

CREATE TABLE IF NOT EXISTS armor (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_name TEXT NOT NULL UNIQUE,
  armor_type TEXT,
  armor_bonus INTEGER,
  max_dex INTEGER,
  armor_check_penalty INTEGER,
  arcane_spell_failure INTEGER,
  ingestion_run_id INTEGER,
  source_record_id INTEGER,
  source_book TEXT,
  license_tag TEXT
);
"""


def _detect_engine(dsn: str) -> Engine:
    if dsn.startswith("sqlite:///"):
        return "sqlite"
    return "postgres"


def _open_sqlite(dsn: str) -> sqlite3.Connection:
    path = dsn.replace("sqlite:///", "", 1)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _bootstrap_sqlite(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQLITE_SCHEMA)
    conn.commit()


def _insert_source_record_sqlite(conn: sqlite3.Connection, run_id: int, row: dict, parse_status: str) -> int:
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO source_records
        (ingestion_run_id, source_url, source_book, raw_hash, parse_status, reject_reason, content_type, raw_payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            row.get("source_url"),
            row.get("source_book"),
            row.get("raw_hash"),
            parse_status,
            row.get("reject_reason"),
            row.get("content_type"),
            json.dumps(row.get("data", {}), sort_keys=True),
        ),
    )
    if cur.lastrowid:
        return int(cur.lastrowid)
    existing = conn.execute(
        "SELECT id FROM source_records WHERE ingestion_run_id = ? AND raw_hash = ?",
        (run_id, row.get("raw_hash")),
    ).fetchone()
    return int(existing[0])


def _insert_content_sqlite(conn: sqlite3.Connection, run_id: int, source_record_id: int, row: dict) -> None:
    data = row.get("data", {})
    ctype = row.get("content_type")
    provenance = (run_id, source_record_id, row.get("source_book"), row.get("license_tag", "OGL"))

    if ctype == "class":
        conn.execute(
            """
            INSERT OR REPLACE INTO classes
            (name, class_type, hit_die, skill_ranks_per_level, bab_progression, fort_progression, ref_progression, will_progression,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("name"),
                data.get("class_type"),
                data.get("hit_die"),
                data.get("skill_ranks_per_level"),
                data.get("bab_progression"),
                data.get("fort_progression"),
                data.get("ref_progression"),
                data.get("will_progression"),
                *provenance,
            ),
        )
    elif ctype == "class_progression":
        conn.execute(
            """
            INSERT OR REPLACE INTO class_progression
            (class_name, level, bab, fort_save, ref_save, will_save, special, spells_per_day,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("class_name"),
                data.get("level"),
                data.get("bab"),
                data.get("fort_save"),
                data.get("ref_save"),
                data.get("will_save"),
                data.get("special"),
                json.dumps(data.get("spells_per_day", {}), sort_keys=True),
                *provenance,
            ),
        )
    elif ctype == "class_feature":
        conn.execute(
            """
            INSERT OR REPLACE INTO class_features
            (class_name, name, level, feature_type, description,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("class_name"),
                data.get("name"),
                data.get("level"),
                data.get("feature_type"),
                data.get("description"),
                *provenance,
            ),
        )
    elif ctype == "race":
        conn.execute(
            """
            INSERT OR REPLACE INTO races
            (name, race_type, size, base_speed, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data.get("name"), data.get("race_type"), data.get("size"), data.get("base_speed"), *provenance),
        )
    elif ctype == "racial_trait":
        conn.execute(
            """
            INSERT OR REPLACE INTO racial_traits
            (race_name, name, trait_type, description, replaces,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("race_name"),
                data.get("name"),
                data.get("trait_type"),
                data.get("description"),
                data.get("replaces"),
                *provenance,
            ),
        )
    elif ctype == "feat":
        conn.execute(
            """
            INSERT OR REPLACE INTO feats
            (name, feat_type, prerequisites, benefit,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data.get("name"), data.get("feat_type"), data.get("prerequisites"), data.get("benefit"), *provenance),
        )
    elif ctype == "trait":
        conn.execute(
            """
            INSERT OR REPLACE INTO traits
            (name, trait_type, prerequisites, benefit, description,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("name"),
                data.get("trait_type"),
                data.get("prerequisites"),
                data.get("benefit"),
                data.get("description"),
                *provenance,
            ),
        )
    elif ctype == "spell":
        conn.execute(
            """
            INSERT OR REPLACE INTO spells
            (name, school, description,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (data.get("name"), data.get("school"), data.get("description"), *provenance),
        )
    elif ctype == "spell_class_level":
        conn.execute(
            """
            INSERT OR REPLACE INTO spell_class_levels
            (spell_name, class_name, level,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (data.get("spell_name"), data.get("class_name"), data.get("level"), *provenance),
        )
    elif ctype == "equipment":
        conn.execute(
            """
            INSERT OR REPLACE INTO equipment
            (name, equipment_type, cost, weight, description,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("name"),
                data.get("equipment_type"),
                data.get("cost"),
                data.get("weight"),
                data.get("description"),
                *provenance,
            ),
        )
    elif ctype == "weapon":
        conn.execute(
            """
            INSERT OR REPLACE INTO weapons
            (equipment_name, proficiency, weapon_type, handedness, damage_medium, critical,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("equipment_name"),
                data.get("proficiency"),
                data.get("weapon_type"),
                data.get("handedness"),
                data.get("damage_medium"),
                data.get("critical"),
                *provenance,
            ),
        )
    elif ctype == "armor":
        conn.execute(
            """
            INSERT OR REPLACE INTO armor
            (equipment_name, armor_type, armor_bonus, max_dex, armor_check_penalty, arcane_spell_failure,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("equipment_name"),
                data.get("armor_type"),
                data.get("armor_bonus"),
                data.get("max_dex"),
                data.get("armor_check_penalty"),
                data.get("arcane_spell_failure"),
                *provenance,
            ),
        )


def _load_sqlite(dsn: str, run_key: str, manifest: dict, accepted_rows: list[dict], rejected_rows: list[dict]) -> dict:
    conn = _open_sqlite(dsn)
    try:
        _bootstrap_sqlite(conn)

        cur = conn.execute(
            """
            INSERT OR REPLACE INTO ingestion_runs
            (run_key, started_at, source_name, source_version, git_sha, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_key,
                manifest.get("started_at"),
                manifest.get("source"),
                "bootstrap-v1",
                manifest.get("git_sha"),
                "loaded",
            ),
        )
        run_id = cur.lastrowid
        if not run_id:
            row = conn.execute("SELECT id FROM ingestion_runs WHERE run_key = ?", (run_key,)).fetchone()
            run_id = int(row[0])

        inserted = 0
        for row in accepted_rows:
            source_record_id = _insert_source_record_sqlite(conn, run_id, row, "accepted")
            _insert_content_sqlite(conn, run_id, source_record_id, row)
            inserted += 1

        for row in rejected_rows:
            _insert_source_record_sqlite(conn, run_id, row, "rejected")

        conn.commit()
        return {
            "engine": "sqlite",
            "run_id": run_id,
            "inserted_records": inserted,
            "rejected_records": len(rejected_rows),
        }
    finally:
        conn.close()


def _insert_source_record_postgres(cur, run_id: int, row: dict, parse_status: str) -> int:
    cur.execute(
        """
        INSERT INTO source_records
        (ingestion_run_id, source_url, source_book, raw_hash, parse_status, reject_reason, content_type, raw_payload)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (ingestion_run_id, raw_hash)
        DO UPDATE SET
          parse_status = EXCLUDED.parse_status,
          reject_reason = EXCLUDED.reject_reason
        RETURNING id
        """,
        (
            run_id,
            row.get("source_url"),
            row.get("source_book"),
            row.get("raw_hash"),
            parse_status,
            row.get("reject_reason"),
            row.get("content_type"),
            json.dumps(row.get("data", {}), sort_keys=True),
        ),
    )
    return int(cur.fetchone()[0])


def _insert_content_postgres(cur, run_id: int, source_record_id: int, row: dict) -> None:
    data = row.get("data", {})
    ctype = row.get("content_type")
    provenance = (run_id, source_record_id, row.get("source_book"), row.get("license_tag", "OGL"))

    if ctype == "class":
        cur.execute(
            """
            INSERT INTO classes
            (name, class_type, hit_die, skill_ranks_per_level, bab_progression, fort_progression, ref_progression, will_progression,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
              class_type = EXCLUDED.class_type,
              hit_die = EXCLUDED.hit_die,
              skill_ranks_per_level = EXCLUDED.skill_ranks_per_level,
              bab_progression = EXCLUDED.bab_progression,
              fort_progression = EXCLUDED.fort_progression,
              ref_progression = EXCLUDED.ref_progression,
              will_progression = EXCLUDED.will_progression,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (
                data.get("name"),
                data.get("class_type"),
                data.get("hit_die"),
                data.get("skill_ranks_per_level"),
                data.get("bab_progression"),
                data.get("fort_progression"),
                data.get("ref_progression"),
                data.get("will_progression"),
                *provenance,
            ),
        )
    elif ctype == "class_progression":
        cur.execute(
            """
            INSERT INTO class_progression
            (class_name, level, bab, fort_save, ref_save, will_save, special, spells_per_day,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
            ON CONFLICT (class_name, level) DO UPDATE SET
              bab = EXCLUDED.bab,
              fort_save = EXCLUDED.fort_save,
              ref_save = EXCLUDED.ref_save,
              will_save = EXCLUDED.will_save,
              special = EXCLUDED.special,
              spells_per_day = EXCLUDED.spells_per_day,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (
                data.get("class_name"),
                data.get("level"),
                data.get("bab"),
                data.get("fort_save"),
                data.get("ref_save"),
                data.get("will_save"),
                data.get("special"),
                json.dumps(data.get("spells_per_day", {}), sort_keys=True),
                *provenance,
            ),
        )
    elif ctype == "class_feature":
        cur.execute(
            """
            INSERT INTO class_features
            (class_name, name, level, feature_type, description, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (class_name, name, level) DO UPDATE SET
              feature_type = EXCLUDED.feature_type,
              description = EXCLUDED.description,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (
                data.get("class_name"),
                data.get("name"),
                data.get("level"),
                data.get("feature_type"),
                data.get("description"),
                *provenance,
            ),
        )
    elif ctype == "race":
        cur.execute(
            """
            INSERT INTO races
            (name, race_type, size, base_speed, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
              race_type = EXCLUDED.race_type,
              size = EXCLUDED.size,
              base_speed = EXCLUDED.base_speed,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (data.get("name"), data.get("race_type"), data.get("size"), data.get("base_speed"), *provenance),
        )
    elif ctype == "racial_trait":
        cur.execute(
            """
            INSERT INTO racial_traits
            (race_name, name, trait_type, description, replaces, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (race_name, name) DO UPDATE SET
              trait_type = EXCLUDED.trait_type,
              description = EXCLUDED.description,
              replaces = EXCLUDED.replaces,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (
                data.get("race_name"),
                data.get("name"),
                data.get("trait_type"),
                data.get("description"),
                data.get("replaces"),
                *provenance,
            ),
        )
    elif ctype == "feat":
        cur.execute(
            """
            INSERT INTO feats
            (name, feat_type, prerequisites, benefit, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
              feat_type = EXCLUDED.feat_type,
              prerequisites = EXCLUDED.prerequisites,
              benefit = EXCLUDED.benefit,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (data.get("name"), data.get("feat_type"), data.get("prerequisites"), data.get("benefit"), *provenance),
        )
    elif ctype == "trait":
        cur.execute(
            """
            INSERT INTO traits
            (name, trait_type, prerequisites, benefit, description, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
              trait_type = EXCLUDED.trait_type,
              prerequisites = EXCLUDED.prerequisites,
              benefit = EXCLUDED.benefit,
              description = EXCLUDED.description,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (
                data.get("name"),
                data.get("trait_type"),
                data.get("prerequisites"),
                data.get("benefit"),
                data.get("description"),
                *provenance,
            ),
        )
    elif ctype == "spell":
        cur.execute(
            """
            INSERT INTO spells
            (name, school, description, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
              school = EXCLUDED.school,
              description = EXCLUDED.description,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (data.get("name"), data.get("school"), data.get("description"), *provenance),
        )
    elif ctype == "spell_class_level":
        cur.execute(
            """
            INSERT INTO spell_class_levels
            (spell_name, class_name, level, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (spell_name, class_name) DO UPDATE SET
              level = EXCLUDED.level,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (data.get("spell_name"), data.get("class_name"), data.get("level"), *provenance),
        )
    elif ctype == "equipment":
        cur.execute(
            """
            INSERT INTO equipment
            (name, equipment_type, cost, weight, description, ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
              equipment_type = EXCLUDED.equipment_type,
              cost = EXCLUDED.cost,
              weight = EXCLUDED.weight,
              description = EXCLUDED.description,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (
                data.get("name"),
                data.get("equipment_type"),
                data.get("cost"),
                data.get("weight"),
                data.get("description"),
                *provenance,
            ),
        )
    elif ctype == "weapon":
        cur.execute(
            """
            INSERT INTO weapons
            (equipment_name, proficiency, weapon_type, handedness, damage_medium, critical,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (equipment_name) DO UPDATE SET
              proficiency = EXCLUDED.proficiency,
              weapon_type = EXCLUDED.weapon_type,
              handedness = EXCLUDED.handedness,
              damage_medium = EXCLUDED.damage_medium,
              critical = EXCLUDED.critical,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (
                data.get("equipment_name"),
                data.get("proficiency"),
                data.get("weapon_type"),
                data.get("handedness"),
                data.get("damage_medium"),
                data.get("critical"),
                *provenance,
            ),
        )
    elif ctype == "armor":
        cur.execute(
            """
            INSERT INTO armor
            (equipment_name, armor_type, armor_bonus, max_dex, armor_check_penalty, arcane_spell_failure,
             ingestion_run_id, source_record_id, source_book, license_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (equipment_name) DO UPDATE SET
              armor_type = EXCLUDED.armor_type,
              armor_bonus = EXCLUDED.armor_bonus,
              max_dex = EXCLUDED.max_dex,
              armor_check_penalty = EXCLUDED.armor_check_penalty,
              arcane_spell_failure = EXCLUDED.arcane_spell_failure,
              ingestion_run_id = EXCLUDED.ingestion_run_id,
              source_record_id = EXCLUDED.source_record_id,
              source_book = EXCLUDED.source_book,
              license_tag = EXCLUDED.license_tag
            """,
            (
                data.get("equipment_name"),
                data.get("armor_type"),
                data.get("armor_bonus"),
                data.get("max_dex"),
                data.get("armor_check_penalty"),
                data.get("arcane_spell_failure"),
                *provenance,
            ),
        )


def _load_postgres(dsn: str, run_key: str, manifest: dict, accepted_rows: list[dict], rejected_rows: list[dict]) -> dict:
    import psycopg

    migration_path = Path(__file__).resolve().parents[2] / "migrations" / "0001_init.sql"
    migration_sql = migration_path.read_text(encoding="utf-8")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(migration_sql)
            cur.execute(
                """
                INSERT INTO ingestion_runs
                (run_key, started_at, source_name, source_version, git_sha, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_key)
                DO UPDATE SET
                  started_at = EXCLUDED.started_at,
                  source_name = EXCLUDED.source_name,
                  source_version = EXCLUDED.source_version,
                  git_sha = EXCLUDED.git_sha,
                  status = EXCLUDED.status
                RETURNING id
                """,
                (
                    run_key,
                    manifest.get("started_at"),
                    manifest.get("source"),
                    "bootstrap-v1",
                    manifest.get("git_sha"),
                    "loaded",
                ),
            )
            run_id = int(cur.fetchone()[0])

            inserted = 0
            for row in accepted_rows:
                source_record_id = _insert_source_record_postgres(cur, run_id, row, "accepted")
                _insert_content_postgres(cur, run_id, source_record_id, row)
                inserted += 1

            for row in rejected_rows:
                _insert_source_record_postgres(cur, run_id, row, "rejected")

        conn.commit()

    return {
        "engine": "postgres",
        "run_id": run_id,
        "inserted_records": inserted,
        "rejected_records": len(rejected_rows),
    }


def run_load(run_path: Path, dsn: str) -> dict:
    manifest = read_json(run_path / "manifest.json")
    run_key = str(manifest["run_key"])
    accepted_rows = read_jsonl(run_path / "validation" / "accepted_records.jsonl")
    rejected_rows = read_jsonl(run_path / "validation" / "rejected_records.jsonl")

    engine = _detect_engine(dsn)
    if engine == "sqlite":
        return _load_sqlite(dsn, run_key, manifest, accepted_rows, rejected_rows)
    return _load_postgres(dsn=dsn, run_key=run_key, manifest=manifest, accepted_rows=accepted_rows, rejected_rows=rejected_rows)
