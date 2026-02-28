"""Add content schema with 18 game-data tables migrated from SQLite.

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-28

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS content")

    # ── sources ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.sources (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            abbreviation TEXT,
            publisher TEXT DEFAULT 'Paizo',
            psrd_folder TEXT,
            import_date TEXT,
            record_count INTEGER DEFAULT 0
        )
    """)

    # ── skills (before class_skills FK) ──────────────────────────────────
    op.execute("""
        CREATE TABLE content.skills (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            ability TEXT CHECK(ability IN ('str', 'dex', 'con', 'int', 'wis', 'cha')),
            trained_only INTEGER DEFAULT 0,
            armor_check_penalty INTEGER DEFAULT 0,
            description TEXT,
            url TEXT
        )
    """)

    # ── classes ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.classes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            source_id INTEGER REFERENCES content.sources(id),
            class_type TEXT CHECK(class_type IN ('base', 'prestige', 'npc', 'hybrid', 'unchained', 'occult')),
            hit_die TEXT,
            skill_ranks_per_level INTEGER,
            bab_progression TEXT CHECK(bab_progression IN ('full', 'three_quarter', 'half')),
            fort_progression TEXT CHECK(fort_progression IN ('good', 'poor')),
            ref_progression TEXT CHECK(ref_progression IN ('good', 'poor')),
            will_progression TEXT CHECK(will_progression IN ('good', 'poor')),
            spellcasting_type TEXT CHECK(spellcasting_type IN ('arcane', 'divine', 'psychic', 'alchemical')),
            spellcasting_style TEXT CHECK(spellcasting_style IN ('prepared', 'spontaneous')),
            max_spell_level INTEGER,
            alignment_restriction TEXT,
            description TEXT,
            url TEXT,
            UNIQUE(name, source_id)
        )
    """)

    # ── class_skills ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.class_skills (
            id SERIAL PRIMARY KEY,
            class_id INTEGER NOT NULL REFERENCES content.classes(id),
            skill_id INTEGER NOT NULL REFERENCES content.skills(id),
            UNIQUE(class_id, skill_id)
        )
    """)

    # ── class_features ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.class_features (
            id SERIAL PRIMARY KEY,
            class_id INTEGER NOT NULL REFERENCES content.classes(id),
            name TEXT NOT NULL,
            level INTEGER NOT NULL,
            feature_type TEXT,
            description TEXT,
            replaces TEXT,
            url TEXT
        )
    """)

    # ── class_progression ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.class_progression (
            id SERIAL PRIMARY KEY,
            class_id INTEGER NOT NULL REFERENCES content.classes(id),
            level INTEGER NOT NULL,
            bab INTEGER NOT NULL,
            fort_save INTEGER NOT NULL,
            ref_save INTEGER NOT NULL,
            will_save INTEGER NOT NULL,
            special TEXT,
            spells_per_day TEXT,
            UNIQUE(class_id, level)
        )
    """)

    # ── archetypes ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.archetypes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            class_id INTEGER NOT NULL REFERENCES content.classes(id),
            source_id INTEGER REFERENCES content.sources(id),
            description TEXT,
            url TEXT,
            is_paizo_official INTEGER DEFAULT 1,
            UNIQUE(name, class_id)
        )
    """)

    # ── archetype_features ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.archetype_features (
            id SERIAL PRIMARY KEY,
            archetype_id INTEGER NOT NULL REFERENCES content.archetypes(id),
            name TEXT NOT NULL,
            level INTEGER,
            description TEXT,
            replaces TEXT,
            url TEXT
        )
    """)

    # ── races ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.races (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            source_id INTEGER REFERENCES content.sources(id),
            race_type TEXT CHECK(race_type IN ('core', 'featured', 'uncommon', 'other')),
            size TEXT CHECK(size IN ('Fine', 'Diminutive', 'Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan', 'Colossal')),
            base_speed INTEGER DEFAULT 30,
            ability_modifiers TEXT,
            type TEXT,
            subtypes TEXT,
            languages TEXT,
            bonus_languages TEXT,
            description TEXT,
            url TEXT
        )
    """)

    # ── racial_traits ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.racial_traits (
            id SERIAL PRIMARY KEY,
            race_id INTEGER NOT NULL REFERENCES content.races(id),
            name TEXT NOT NULL,
            trait_type TEXT,
            description TEXT,
            replaces TEXT,
            url TEXT
        )
    """)

    # ── feats ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.feats (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            source_id INTEGER REFERENCES content.sources(id),
            feat_type TEXT,
            prerequisites TEXT,
            prerequisite_feats TEXT,
            benefit TEXT,
            normal TEXT,
            special TEXT,
            description TEXT,
            url TEXT,
            is_paizo_official INTEGER DEFAULT 1,
            UNIQUE(name, source_id)
        )
    """)

    # ── spells ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.spells (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            source_id INTEGER REFERENCES content.sources(id),
            school TEXT,
            subschool TEXT,
            descriptors TEXT,
            casting_time TEXT,
            components TEXT,
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
        )
    """)

    # ── spell_class_levels ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.spell_class_levels (
            id SERIAL PRIMARY KEY,
            spell_id INTEGER NOT NULL REFERENCES content.spells(id),
            class_name TEXT NOT NULL,
            level INTEGER NOT NULL,
            UNIQUE(spell_id, class_name)
        )
    """)

    # ── equipment ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.equipment (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            source_id INTEGER REFERENCES content.sources(id),
            equipment_type TEXT CHECK(equipment_type IN ('weapon', 'armor', 'shield', 'gear', 'alchemical', 'tool', 'clothing', 'mount', 'vehicle', 'service', 'other')),
            cost TEXT,
            cost_copper INTEGER,
            weight TEXT,
            description TEXT,
            url TEXT
        )
    """)

    # ── weapons ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.weapons (
            id SERIAL PRIMARY KEY,
            equipment_id INTEGER NOT NULL REFERENCES content.equipment(id),
            proficiency TEXT CHECK(proficiency IN ('simple', 'martial', 'exotic')),
            weapon_type TEXT CHECK(weapon_type IN ('melee', 'ranged', 'ammunition')),
            handedness TEXT CHECK(handedness IN ('light', 'one-handed', 'two-handed')),
            damage_small TEXT,
            damage_medium TEXT,
            critical TEXT,
            range_increment TEXT,
            damage_type TEXT,
            special TEXT
        )
    """)

    # ── armor ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.armor (
            id SERIAL PRIMARY KEY,
            equipment_id INTEGER NOT NULL REFERENCES content.equipment(id),
            armor_type TEXT CHECK(armor_type IN ('light', 'medium', 'heavy', 'shield')),
            armor_bonus INTEGER,
            max_dex INTEGER,
            armor_check_penalty INTEGER,
            arcane_spell_failure INTEGER,
            speed_30 TEXT,
            speed_20 TEXT
        )
    """)

    # ── magic_items ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.magic_items (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            source_id INTEGER REFERENCES content.sources(id),
            slot TEXT,
            item_type TEXT,
            aura TEXT,
            caster_level TEXT,
            price TEXT,
            price_gp TEXT,
            weight TEXT,
            description TEXT,
            construction_requirements TEXT,
            construction_cost TEXT,
            url TEXT
        )
    """)

    # ── monsters ─────────────────────────────────────────────────────────
    # Most numeric columns are NULL or contain text (commas in xp, etc.)
    # Use TEXT for all stat columns — this is display-only data.
    op.execute("""
        CREATE TABLE content.monsters (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            source_id INTEGER REFERENCES content.sources(id),
            cr TEXT,
            cr_numeric TEXT,
            xp TEXT,
            alignment TEXT,
            size TEXT,
            type TEXT,
            subtypes TEXT,
            initiative TEXT,
            hit_points TEXT,
            hit_dice TEXT,
            ac TEXT,
            ac_touch TEXT,
            ac_flat_footed TEXT,
            fort_save TEXT,
            ref_save TEXT,
            will_save TEXT,
            speed TEXT,
            str TEXT, dex TEXT, con TEXT,
            int_score TEXT, wis TEXT, cha TEXT,
            bab TEXT,
            cmb TEXT,
            cmd TEXT,
            feats TEXT,
            skills TEXT,
            languages TEXT,
            special_qualities TEXT,
            environment TEXT,
            organization TEXT,
            treasure TEXT,
            description TEXT,
            url TEXT
        )
    """)

    # ── traits ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE content.traits (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            source_id INTEGER REFERENCES content.sources(id),
            trait_type TEXT,
            prerequisites TEXT,
            benefit TEXT,
            description TEXT,
            url TEXT,
            is_paizo_official INTEGER DEFAULT 1,
            UNIQUE(name, trait_type)
        )
    """)

    # ── search_index (PG tsvector) ───────────────────────────────────────
    op.execute("""
        CREATE TABLE content.search_index (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            content_type TEXT NOT NULL,
            description TEXT,
            source TEXT,
            content_id INTEGER,
            tsv TSVECTOR
        )
    """)
    op.execute("""
        CREATE INDEX idx_search_tsv ON content.search_index USING GIN (tsv)
    """)
    # Auto-update trigger: rebuild tsv on INSERT or UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION content.search_index_tsv_update() RETURNS trigger AS $$
        BEGIN
            NEW.tsv := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                       setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_search_index_tsv
        BEFORE INSERT OR UPDATE ON content.search_index
        FOR EACH ROW EXECUTE FUNCTION content.search_index_tsv_update()
    """)

    # ── Indexes matching SQLite ──────────────────────────────────────────
    op.execute("CREATE INDEX idx_spells_school ON content.spells(school)")
    op.execute("CREATE INDEX idx_spells_name ON content.spells(name)")
    op.execute("CREATE INDEX idx_spell_class_levels_class ON content.spell_class_levels(class_name)")
    op.execute("CREATE INDEX idx_spell_class_levels_level ON content.spell_class_levels(level)")
    op.execute("CREATE INDEX idx_feats_type ON content.feats(feat_type)")
    op.execute("CREATE INDEX idx_feats_name ON content.feats(name)")
    op.execute("CREATE INDEX idx_classes_type ON content.classes(class_type)")
    op.execute("CREATE INDEX idx_class_features_level ON content.class_features(class_id, level)")
    op.execute("CREATE INDEX idx_equipment_type ON content.equipment(equipment_type)")
    op.execute("CREATE INDEX idx_monsters_cr ON content.monsters(cr_numeric)")
    op.execute("CREATE INDEX idx_monsters_type ON content.monsters(type)")
    op.execute("CREATE INDEX idx_traits_type ON content.traits(trait_type)")
    op.execute("CREATE INDEX idx_traits_name ON content.traits(name)")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS content CASCADE")
