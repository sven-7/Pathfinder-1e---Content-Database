-- PF1e V2 canonical schema with ingestion provenance.

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id BIGSERIAL PRIMARY KEY,
  run_key TEXT NOT NULL UNIQUE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_name TEXT NOT NULL,
  source_version TEXT,
  git_sha TEXT,
  status TEXT NOT NULL CHECK (status IN ('running', 'validated', 'loaded', 'failed'))
);

CREATE TABLE IF NOT EXISTS source_records (
  id BIGSERIAL PRIMARY KEY,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id) ON DELETE CASCADE,
  source_url TEXT NOT NULL,
  source_book TEXT,
  raw_hash TEXT NOT NULL,
  parse_status TEXT NOT NULL CHECK (parse_status IN ('accepted', 'rejected')),
  reject_reason TEXT,
  content_type TEXT NOT NULL,
  raw_payload JSONB,
  UNIQUE (ingestion_run_id, raw_hash)
);

CREATE TABLE IF NOT EXISTS classes (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  class_type TEXT,
  hit_die TEXT,
  skill_ranks_per_level INTEGER,
  bab_progression TEXT,
  fort_progression TEXT,
  ref_progression TEXT,
  will_progression TEXT,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS class_progression (
  id BIGSERIAL PRIMARY KEY,
  class_name TEXT NOT NULL,
  level INTEGER NOT NULL,
  bab INTEGER NOT NULL,
  fort_save INTEGER NOT NULL,
  ref_save INTEGER NOT NULL,
  will_save INTEGER NOT NULL,
  special TEXT,
  spells_per_day JSONB,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL,
  UNIQUE (class_name, level)
);

CREATE TABLE IF NOT EXISTS class_features (
  id BIGSERIAL PRIMARY KEY,
  class_name TEXT NOT NULL,
  name TEXT NOT NULL,
  level INTEGER,
  feature_type TEXT,
  description TEXT,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL,
  UNIQUE (class_name, name, level)
);

CREATE TABLE IF NOT EXISTS races (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  race_type TEXT,
  size TEXT,
  base_speed INTEGER,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS racial_traits (
  id BIGSERIAL PRIMARY KEY,
  race_name TEXT NOT NULL,
  name TEXT NOT NULL,
  trait_type TEXT,
  description TEXT,
  replaces TEXT,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL,
  UNIQUE (race_name, name)
);

CREATE TABLE IF NOT EXISTS feats (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  feat_type TEXT,
  prerequisites TEXT,
  benefit TEXT,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS traits (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  trait_type TEXT,
  prerequisites TEXT,
  benefit TEXT,
  description TEXT,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spells (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  school TEXT,
  description TEXT,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spell_class_levels (
  id BIGSERIAL PRIMARY KEY,
  spell_name TEXT NOT NULL,
  class_name TEXT NOT NULL,
  level INTEGER NOT NULL,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL,
  UNIQUE (spell_name, class_name)
);

CREATE TABLE IF NOT EXISTS equipment (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  equipment_type TEXT,
  cost TEXT,
  weight NUMERIC,
  description TEXT,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS weapons (
  id BIGSERIAL PRIMARY KEY,
  equipment_name TEXT NOT NULL UNIQUE,
  proficiency TEXT,
  weapon_type TEXT,
  handedness TEXT,
  damage_medium TEXT,
  critical TEXT,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS armor (
  id BIGSERIAL PRIMARY KEY,
  equipment_name TEXT NOT NULL UNIQUE,
  armor_type TEXT,
  armor_bonus INTEGER,
  max_dex INTEGER,
  armor_check_penalty INTEGER,
  arcane_spell_failure INTEGER,
  ingestion_run_id BIGINT NOT NULL REFERENCES ingestion_runs(id),
  source_record_id BIGINT NOT NULL REFERENCES source_records(id),
  source_book TEXT,
  license_tag TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_source_records_content_type ON source_records(content_type);
CREATE INDEX IF NOT EXISTS idx_feats_name ON feats(name);
CREATE INDEX IF NOT EXISTS idx_races_name ON races(name);
CREATE INDEX IF NOT EXISTS idx_spells_name ON spells(name);
