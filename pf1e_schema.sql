-- Pathfinder 1e Content Database Schema
-- Designed for character creation, level tracking, and reference tools
-- SQLite3

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================
-- SOURCE TRACKING
-- ============================================================

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- e.g. "Core Rulebook"
    abbreviation TEXT,                    -- e.g. "CRB"
    publisher TEXT DEFAULT 'Paizo',
    psrd_folder TEXT,                     -- maps to PSRD-Data directory name
    import_date TEXT,
    record_count INTEGER DEFAULT 0
);

-- ============================================================
-- CLASSES
-- ============================================================

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    class_type TEXT CHECK(class_type IN ('base', 'prestige', 'npc', 'hybrid', 'unchained', 'occult')),
    hit_die TEXT,                         -- e.g. "d10", "d8"
    skill_ranks_per_level INTEGER,
    bab_progression TEXT CHECK(bab_progression IN ('full', 'three_quarter', 'half')),
    fort_progression TEXT CHECK(fort_progression IN ('good', 'poor')),
    ref_progression TEXT CHECK(ref_progression IN ('good', 'poor')),
    will_progression TEXT CHECK(will_progression IN ('good', 'poor')),
    spellcasting_type TEXT CHECK(spellcasting_type IN ('arcane', 'divine', 'psychic', 'alchemical', NULL)),
    spellcasting_style TEXT CHECK(spellcasting_style IN ('prepared', 'spontaneous', NULL)),
    max_spell_level INTEGER,             -- NULL for non-casters
    alignment_restriction TEXT,           -- e.g. "any non-lawful", "any good"
    description TEXT,
    url TEXT,                            -- pfsrd:// reference URL
    UNIQUE(name, source_id)
);

CREATE TABLE IF NOT EXISTS class_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL REFERENCES classes(id),
    skill_id INTEGER NOT NULL REFERENCES skills(id),
    UNIQUE(class_id, skill_id)
);

CREATE TABLE IF NOT EXISTS class_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL REFERENCES classes(id),
    name TEXT NOT NULL,
    level INTEGER NOT NULL,              -- level gained
    feature_type TEXT,                   -- e.g. "class_feature", "rage_power", "mercy", "discovery"
    description TEXT,
    replaces TEXT,                       -- for archetypes: what feature this replaces
    url TEXT
);

CREATE TABLE IF NOT EXISTS class_progression (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL REFERENCES classes(id),
    level INTEGER NOT NULL,
    bab INTEGER NOT NULL,
    fort_save INTEGER NOT NULL,
    ref_save INTEGER NOT NULL,
    will_save INTEGER NOT NULL,
    special TEXT,                        -- comma-separated feature names at this level
    spells_per_day TEXT,                 -- JSON: {"0": 4, "1": 2, ...}
    UNIQUE(class_id, level)
);

-- ============================================================
-- ARCHETYPES
-- ============================================================

CREATE TABLE IF NOT EXISTS archetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    class_id INTEGER NOT NULL REFERENCES classes(id),
    source_id INTEGER REFERENCES sources(id),
    description TEXT,
    url TEXT,
    UNIQUE(name, class_id)
);

CREATE TABLE IF NOT EXISTS archetype_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    archetype_id INTEGER NOT NULL REFERENCES archetypes(id),
    name TEXT NOT NULL,
    level INTEGER,
    description TEXT,
    replaces TEXT,                       -- name of class feature replaced
    url TEXT
);

-- ============================================================
-- RACES
-- ============================================================

CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    source_id INTEGER REFERENCES sources(id),
    race_type TEXT CHECK(race_type IN ('core', 'featured', 'uncommon', 'other')),
    size TEXT CHECK(size IN ('Fine', 'Diminutive', 'Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan', 'Colossal')),
    base_speed INTEGER DEFAULT 30,
    ability_modifiers TEXT,              -- JSON: {"str": 2, "dex": -2, "cha": 2}
    type TEXT,                           -- e.g. "Humanoid"
    subtypes TEXT,                       -- e.g. "elf, human"
    languages TEXT,                      -- starting languages
    bonus_languages TEXT,                -- available bonus languages
    description TEXT,
    url TEXT
);

CREATE TABLE IF NOT EXISTS racial_traits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id INTEGER NOT NULL REFERENCES races(id),
    name TEXT NOT NULL,
    trait_type TEXT,                     -- e.g. "defense", "offense", "senses", "feat_and_skill"
    description TEXT,
    replaces TEXT,                       -- for alternate racial traits
    url TEXT
);

-- ============================================================
-- FEATS
-- ============================================================

CREATE TABLE IF NOT EXISTS feats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    feat_type TEXT,                      -- e.g. "general", "combat", "metamagic", "item_creation", "teamwork", "mythic"
    prerequisites TEXT,                  -- raw text prerequisites
    prerequisite_feats TEXT,             -- comma-separated feat names
    benefit TEXT,
    normal TEXT,                         -- what happens without the feat
    special TEXT,                        -- special notes
    description TEXT,
    url TEXT,
    UNIQUE(name, source_id)
);

-- ============================================================
-- SKILLS
-- ============================================================

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    ability TEXT CHECK(ability IN ('str', 'dex', 'con', 'int', 'wis', 'cha')),
    trained_only INTEGER DEFAULT 0,     -- boolean
    armor_check_penalty INTEGER DEFAULT 0, -- boolean
    description TEXT,
    url TEXT
);

-- ============================================================
-- SPELLS
-- ============================================================

CREATE TABLE IF NOT EXISTS spells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    school TEXT,                         -- e.g. "evocation"
    subschool TEXT,                      -- e.g. "charm"
    descriptors TEXT,                    -- e.g. "fire, mind-affecting" (comma-separated)
    casting_time TEXT,
    components TEXT,                     -- e.g. "V, S, M (bat guano and sulfur)"
    range TEXT,
    area TEXT,
    effect TEXT,
    target TEXT,
    duration TEXT,
    saving_throw TEXT,
    spell_resistance TEXT,
    description TEXT,
    url TEXT,
    UNIQUE(name, source_id)
);

CREATE TABLE IF NOT EXISTS spell_class_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spell_id INTEGER NOT NULL REFERENCES spells(id),
    class_name TEXT NOT NULL,           -- "wizard", "cleric", "sorcerer", etc.
    level INTEGER NOT NULL,
    UNIQUE(spell_id, class_name)
);

-- ============================================================
-- EQUIPMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    equipment_type TEXT CHECK(equipment_type IN ('weapon', 'armor', 'shield', 'gear', 'alchemical', 'tool', 'clothing', 'mount', 'vehicle', 'service', 'other')),
    cost TEXT,                           -- raw cost string, e.g. "15 gp"
    cost_copper INTEGER,                 -- normalized to copper pieces
    weight REAL,                         -- in pounds
    description TEXT,
    url TEXT
);

CREATE TABLE IF NOT EXISTS weapons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id),
    proficiency TEXT CHECK(proficiency IN ('simple', 'martial', 'exotic')),
    weapon_type TEXT CHECK(weapon_type IN ('melee', 'ranged', 'ammunition')),
    handedness TEXT CHECK(handedness IN ('light', 'one-handed', 'two-handed')),
    damage_small TEXT,                   -- e.g. "1d4"
    damage_medium TEXT,                  -- e.g. "1d6"
    critical TEXT,                       -- e.g. "19-20/x2"
    range_increment TEXT,                -- e.g. "20 ft."
    damage_type TEXT,                    -- e.g. "S", "P", "B"
    special TEXT                         -- e.g. "trip, reach"
);

CREATE TABLE IF NOT EXISTS armor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id),
    armor_type TEXT CHECK(armor_type IN ('light', 'medium', 'heavy', 'shield')),
    armor_bonus INTEGER,
    max_dex INTEGER,
    armor_check_penalty INTEGER,
    arcane_spell_failure INTEGER,        -- percentage
    speed_30 TEXT,
    speed_20 TEXT
);

-- ============================================================
-- MAGIC ITEMS
-- ============================================================

CREATE TABLE IF NOT EXISTS magic_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    slot TEXT,                           -- e.g. "head", "ring", "none"
    item_type TEXT,                      -- e.g. "wondrous", "rod", "staff", "ring", "potion", "scroll", "wand", "weapon", "armor"
    aura TEXT,                           -- e.g. "moderate transmutation"
    caster_level INTEGER,
    price TEXT,                          -- raw price string
    price_gp INTEGER,                    -- normalized to gp
    weight REAL,
    description TEXT,
    construction_requirements TEXT,
    construction_cost TEXT,
    url TEXT
);

-- ============================================================
-- MONSTERS (for GM tools / encounter building)
-- ============================================================

CREATE TABLE IF NOT EXISTS monsters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    cr TEXT,                             -- can be fraction: "1/2"
    cr_numeric REAL,                     -- 0.5 for "1/2"
    xp INTEGER,
    alignment TEXT,
    size TEXT,
    type TEXT,                           -- e.g. "Aberration"
    subtypes TEXT,
    initiative INTEGER,
    hit_points INTEGER,
    hit_dice TEXT,
    ac INTEGER,
    ac_touch INTEGER,
    ac_flat_footed INTEGER,
    fort_save INTEGER,
    ref_save INTEGER,
    will_save INTEGER,
    speed TEXT,
    str INTEGER, dex INTEGER, con INTEGER,
    int_score INTEGER, wis INTEGER, cha INTEGER,
    bab INTEGER,
    cmb INTEGER,
    cmd INTEGER,
    feats TEXT,
    skills TEXT,
    languages TEXT,
    special_qualities TEXT,
    environment TEXT,
    organization TEXT,
    treasure TEXT,
    description TEXT,
    url TEXT
);

-- ============================================================
-- FULL-TEXT SEARCH (for quick lookups)
-- ============================================================

CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    name,
    content_type,     -- 'spell', 'feat', 'class', 'race', 'item', 'monster'
    description,
    source,
    content_id        -- reference to the actual table row
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_spells_school ON spells(school);
CREATE INDEX IF NOT EXISTS idx_spells_name ON spells(name);
CREATE INDEX IF NOT EXISTS idx_spell_class_levels_class ON spell_class_levels(class_name);
CREATE INDEX IF NOT EXISTS idx_spell_class_levels_level ON spell_class_levels(level);
CREATE INDEX IF NOT EXISTS idx_feats_type ON feats(feat_type);
CREATE INDEX IF NOT EXISTS idx_feats_name ON feats(name);
CREATE INDEX IF NOT EXISTS idx_classes_type ON classes(class_type);
CREATE INDEX IF NOT EXISTS idx_class_features_level ON class_features(class_id, level);
CREATE INDEX IF NOT EXISTS idx_equipment_type ON equipment(equipment_type);
CREATE INDEX IF NOT EXISTS idx_monsters_cr ON monsters(cr_numeric);
CREATE INDEX IF NOT EXISTS idx_monsters_type ON monsters(type);
