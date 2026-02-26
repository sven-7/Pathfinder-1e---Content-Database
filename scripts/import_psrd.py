#!/usr/bin/env python3
"""
import_psrd.py — Import PSRD-Data JSON files into SQLite database.

Reads the JSON files from the cloned PSRD-Data repository and populates
the pf1e.db SQLite database according to our schema.

PSRD-Data JSON Structure (per file):
  - type: "class", "spell", "feat", "section", "race", "skill", etc.
  - name: display name
  - source: source book name
  - body: HTML description
  - url: pfsrd:// reference URL
  - sections: nested child sections
  - Plus type-specific fields (e.g., school/range/duration for spells)
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.json"
SCHEMA_PATH = ROOT / "schema" / "pf1e_schema.sql"


class HTMLTextExtractor(HTMLParser):
    """Strip HTML tags, keeping just text content."""
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_data(self, data):
        self.result.append(data)

    def get_text(self):
        return ''.join(self.result).strip()


def strip_html(html_str):
    """Convert HTML string to plain text."""
    if not html_str:
        return ""
    extractor = HTMLTextExtractor()
    extractor.feed(html_str)
    return extractor.get_text()


def ensure_string(value, separator=', '):
    """Convert any value to a string safe for SQLite binding.

    PSRD JSON fields can be strings, lists, dicts, or None.
    This ensures we always pass a string to SQLite.
    """
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                if 'text' in item:
                    parts.append(str(item['text']))
                elif 'type' in item and len(item) <= 3:
                    parts.append(str(item.get('type', '')))
                else:
                    parts.append(', '.join(f"{k}: {v}" for k, v in item.items()))
            else:
                parts.append(str(item))
        return separator.join(parts)
    if isinstance(value, dict):
        if 'text' in value:
            return str(value['text'])
        return json.dumps(value)
    return str(value)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def init_database(db_path, schema_path):
    """Create database and apply schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
        print(f"  Removed existing database")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    with open(schema_path) as f:
        conn.executescript(f.read())

    print(f"  ✓ Database created at {db_path}")
    return conn


def ensure_source(conn, book_name, abbreviation, folder_name):
    """Insert or get source record."""
    cursor = conn.execute(
        "SELECT id FROM sources WHERE psrd_folder = ?", (folder_name,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    conn.execute(
        "INSERT INTO sources (name, abbreviation, psrd_folder, import_date) VALUES (?, ?, ?, datetime('now'))",
        (book_name, abbreviation, folder_name)
    )
    conn.commit()
    cursor = conn.execute("SELECT last_insert_rowid()")
    return cursor.fetchone()[0]


def walk_json_files(data_dir, book_folder):
    """Yield all JSON files in a book directory, recursively."""
    book_path = data_dir / book_folder
    if not book_path.exists():
        return
    for json_file in sorted(book_path.rglob("*.json")):
        try:
            with open(json_file, encoding='utf-8') as f:
                data = json.load(f)
            yield json_file, data
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"    ⚠ Skipping {json_file.name}: {e}")


def extract_body_text(data):
    """Extract description from body field or nested sections."""
    if 'body' in data and data['body']:
        return strip_html(data['body'])

    parts = []
    for section in data.get('sections', []):
        if 'body' in section and section['body']:
            parts.append(strip_html(section['body']))
    return '\n\n'.join(parts) if parts else ""


def format_components(components_raw):
    """Format spell components from various PSRD formats."""
    if isinstance(components_raw, list):
        comp_parts = []
        for c in components_raw:
            if isinstance(c, dict):
                ct = c.get('type', '')
                text = c.get('text', '')
                if text:
                    comp_parts.append(f"{ct} ({text})")
                else:
                    comp_parts.append(ct)
            else:
                comp_parts.append(str(c))
        return ', '.join(comp_parts)
    elif isinstance(components_raw, dict):
        comp_parts = []
        for ct, detail in components_raw.items():
            if isinstance(detail, dict) and 'text' in detail:
                comp_parts.append(f"{ct} ({detail['text']})")
            elif detail and detail is not True:
                comp_parts.append(f"{ct} ({detail})")
            else:
                comp_parts.append(ct)
        return ', '.join(comp_parts)
    return ensure_string(components_raw)


def import_spell(conn, data, source_id):
    """Import a spell record."""
    name = data.get('name', '').strip()
    if not name:
        return False

    # Safely convert ALL fields — any of them could be lists in PSRD JSON
    school = ensure_string(data.get('school', ''))
    subschool = ensure_string(data.get('subschool', ''))
    descriptor = ensure_string(data.get('descriptor', ''))
    casting_time = ensure_string(data.get('casting_time', ''))
    components = format_components(data.get('components', ''))
    range_val = ensure_string(data.get('range', ''))
    area = ensure_string(data.get('area', ''))
    effect = ensure_string(data.get('effect', ''))
    target = ensure_string(data.get('target', ''))
    duration = ensure_string(data.get('duration', ''))
    saving_throw = ensure_string(data.get('saving_throw', ''))
    spell_resistance = ensure_string(data.get('spell_resistance', ''))

    conn.execute("""
        INSERT OR IGNORE INTO spells
        (name, source_id, school, subschool, descriptors,
         casting_time, components, range, area, effect, target,
         duration, saving_throw, spell_resistance, description, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, source_id, school, subschool, descriptor,
        casting_time, components, range_val, area, effect, target,
        duration, saving_throw, spell_resistance,
        extract_body_text(data),
        ensure_string(data.get('url', ''))
    ))

    # Get spell ID
    cursor = conn.execute("SELECT id FROM spells WHERE name = ? AND source_id = ?", (name, source_id))
    row = cursor.fetchone()
    if not row:
        return False
    spell_id = row[0]

    # Import class/level associations
    # Format: "level" with list of dicts [{"class": "wizard", "level": 3}, ...]
    levels = data.get('level', data.get('levels', []))
    if isinstance(levels, list):
        for entry in levels:
            if isinstance(entry, dict):
                class_name = str(entry.get('class', '')).lower().strip()
                level = entry.get('level')
                if class_name and level is not None:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO spell_class_levels (spell_id, class_name, level) VALUES (?, ?, ?)",
                            (spell_id, class_name, int(level))
                        )
                    except (ValueError, TypeError):
                        pass
    elif isinstance(levels, dict):
        for class_name, level in levels.items():
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO spell_class_levels (spell_id, class_name, level) VALUES (?, ?, ?)",
                    (spell_id, class_name.lower().strip(), int(level))
                )
            except (ValueError, TypeError):
                pass

    return True


def import_feat(conn, data, source_id):
    """Import a feat record."""
    name = data.get('name', '').strip()
    if not name:
        return False

    feat_type = 'general'
    subtype = ensure_string(data.get('subtype', '')).lower()
    if 'combat' in subtype:
        feat_type = 'combat'
    elif 'metamagic' in subtype:
        feat_type = 'metamagic'
    elif 'item creation' in subtype:
        feat_type = 'item_creation'
    elif 'teamwork' in subtype:
        feat_type = 'teamwork'
    elif 'critical' in subtype:
        feat_type = 'critical'
    elif 'grit' in subtype:
        feat_type = 'grit'
    elif 'style' in subtype:
        feat_type = 'style'
    elif 'performance' in subtype:
        feat_type = 'performance'
    elif 'racial' in subtype:
        feat_type = 'racial'
    elif 'story' in subtype:
        feat_type = 'story'
    elif 'mythic' in subtype:
        feat_type = 'mythic'

    prerequisites = ''
    benefit = ''
    normal = ''
    special = ''

    for section in data.get('sections', []):
        sec_name = section.get('name', '').lower().strip()
        sec_body = strip_html(section.get('body', ''))
        if sec_name in ('prerequisite', 'prerequisites'):
            prerequisites = sec_body
        elif sec_name == 'benefit':
            benefit = sec_body
        elif sec_name == 'normal':
            normal = sec_body
        elif sec_name == 'special':
            special = sec_body

    conn.execute("""
        INSERT OR IGNORE INTO feats
        (name, source_id, feat_type, prerequisites, benefit, normal, special, description, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, source_id, feat_type, prerequisites, benefit, normal, special,
        extract_body_text(data), ensure_string(data.get('url', ''))
    ))
    return True


def import_skill(conn, data, source_id):
    """Import a skill record."""
    name = data.get('name', '').strip()
    if not name:
        return False

    ability_map = {
        'acrobatics': 'dex', 'appraise': 'int', 'bluff': 'cha',
        'climb': 'str', 'craft': 'int', 'diplomacy': 'cha',
        'disable device': 'dex', 'disguise': 'cha', 'escape artist': 'dex',
        'fly': 'dex', 'handle animal': 'cha', 'heal': 'wis',
        'intimidate': 'cha', 'knowledge': 'int',
        'linguistics': 'int', 'perception': 'wis', 'perform': 'cha',
        'profession': 'wis', 'ride': 'dex', 'sense motive': 'wis',
        'sleight of hand': 'dex', 'spellcraft': 'int', 'stealth': 'dex',
        'survival': 'wis', 'swim': 'str', 'use magic device': 'cha',
    }

    name_lower = name.lower()
    ability = ability_map.get(name_lower, None)
    if not ability and name_lower.startswith('knowledge'):
        ability = 'int'

    trained_only_skills = {
        'disable device', 'handle animal', 'knowledge', 'linguistics',
        'profession', 'sleight of hand', 'spellcraft', 'use magic device'
    }
    trained_only = 1 if name_lower in trained_only_skills or name_lower.startswith('knowledge') else 0

    acp_skills = {'acrobatics', 'climb', 'disable device', 'escape artist', 'fly', 'ride', 'sleight of hand', 'stealth', 'swim'}
    acp = 1 if name_lower in acp_skills else 0

    conn.execute("""
        INSERT OR IGNORE INTO skills
        (name, ability, trained_only, armor_check_penalty, description, url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, ability, trained_only, acp, extract_body_text(data), ensure_string(data.get('url', ''))))
    return True


def import_class(conn, data, source_id):
    """Import a class record."""
    name = data.get('name', '').strip()
    if not name:
        return False

    class_type = 'base'
    url = ensure_string(data.get('url', ''))
    if 'prestige' in url.lower():
        class_type = 'prestige'
    elif 'npc' in url.lower():
        class_type = 'npc'

    conn.execute("""
        INSERT OR IGNORE INTO classes
        (name, source_id, class_type, description, url)
        VALUES (?, ?, ?, ?, ?)
    """, (name, source_id, class_type, extract_body_text(data), url))

    cursor = conn.execute("SELECT id FROM classes WHERE name = ? AND source_id = ?", (name, source_id))
    row = cursor.fetchone()
    if row:
        class_id = row[0]
        import_class_sections(conn, data, class_id)

    return True


def import_class_sections(conn, data, class_id, level=None):
    """Recursively import class feature sections."""
    for section in data.get('sections', []):
        sec_name = section.get('name', '').strip()
        sec_type = section.get('type', '')

        if sec_name and sec_type in ('section', 'class_feature', 'ability'):
            body = extract_body_text(section)
            if body:
                conn.execute("""
                    INSERT OR IGNORE INTO class_features
                    (class_id, name, level, feature_type, description, url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (class_id, sec_name, level or 1, sec_type or 'class_feature',
                      body, ensure_string(section.get('url', ''))))

        if section.get('sections'):
            import_class_sections(conn, section, class_id, level)


def import_race(conn, data, source_id):
    """Import a race record."""
    name = data.get('name', '').strip()
    if not name:
        return False

    conn.execute("""
        INSERT OR IGNORE INTO races
        (name, source_id, description, url)
        VALUES (?, ?, ?, ?)
    """, (name, source_id, extract_body_text(data), ensure_string(data.get('url', ''))))
    return True


def import_monster(conn, data, source_id):
    """Import a monster/creature record."""
    name = data.get('name', '').strip()
    if not name:
        return False

    cr = data.get('cr', '')
    cr_numeric = None
    if cr:
        try:
            if '/' in str(cr):
                num, den = str(cr).split('/')
                cr_numeric = float(num) / float(den)
            else:
                cr_numeric = float(cr)
        except (ValueError, ZeroDivisionError):
            pass

    conn.execute("""
        INSERT OR IGNORE INTO monsters
        (name, source_id, cr, cr_numeric, xp,
         alignment, size, type, description, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, source_id, str(cr), cr_numeric,
        data.get('xp'),
        ensure_string(data.get('alignment', '')),
        ensure_string(data.get('size', '')),
        ensure_string(data.get('creature_type', '')),
        extract_body_text(data),
        ensure_string(data.get('url', ''))
    ))
    return True


def import_item(conn, data, source_id):
    """Import an equipment or magic item record."""
    name = data.get('name', '').strip()
    if not name:
        return False

    slot = ensure_string(data.get('slot', ''))
    subtype = ensure_string(data.get('subtype', '')).lower()
    aura = ensure_string(data.get('aura', ''))
    cl = data.get('cl', data.get('caster_level', ''))
    weight = ensure_string(data.get('weight', ''))
    price = ensure_string(data.get('price', data.get('cost', '')))

    if aura or cl or slot or 'wondrous' in subtype or 'magic' in subtype:
        # Parse caster_level to int if possible
        cl_int = None
        cl_str = ensure_string(cl)
        try:
            cl_int = int(cl_str) if cl_str else None
        except (ValueError, TypeError):
            # Try extracting first number
            m = re.search(r'\d+', cl_str)
            cl_int = int(m.group()) if m else None

        conn.execute("""
            INSERT OR IGNORE INTO magic_items
            (name, source_id, slot, aura, caster_level, price, weight, description, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, source_id, slot, aura, cl_int,
            price, weight,
            extract_body_text(data),
            ensure_string(data.get('url', ''))
        ))
    else:
        conn.execute("""
            INSERT OR IGNORE INTO equipment
            (name, source_id, cost, weight, description, url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name, source_id, price, weight,
            extract_body_text(data),
            ensure_string(data.get('url', ''))
        ))

    return True


def import_book(conn, data_dir, book_folder, book_config, source_id):
    """Import all JSON files from a single book directory."""
    counters = {'spell': 0, 'feat': 0, 'skill': 0, 'class': 0, 'race': 0,
                'creature': 0, 'item': 0, 'other': 0}

    for json_path, data in walk_json_files(data_dir, book_folder):
        data_type = data.get('type', 'section')
        relative = json_path.relative_to(data_dir / book_folder)
        parent_dir = str(relative.parent).lower()

        try:
            if data_type == 'spell' or 'spell' in parent_dir:
                if import_spell(conn, data, source_id):
                    counters['spell'] += 1
            elif data_type == 'feat' or 'feat' in parent_dir:
                if import_feat(conn, data, source_id):
                    counters['feat'] += 1
            elif data_type == 'skill' or parent_dir == 'skills':
                if import_skill(conn, data, source_id):
                    counters['skill'] += 1
            elif data_type == 'class' or 'class/core' in parent_dir or 'class/prestige' in parent_dir:
                if import_class(conn, data, source_id):
                    counters['class'] += 1
            elif data_type == 'race' or 'race' in parent_dir:
                if import_race(conn, data, source_id):
                    counters['race'] += 1
            elif data_type == 'creature' or 'bestiary' in book_folder:
                if import_monster(conn, data, source_id):
                    counters['creature'] += 1
            elif data_type == 'item' or 'equipment' in parent_dir or 'magic_items' in parent_dir or 'magic' in parent_dir:
                if import_item(conn, data, source_id):
                    counters['item'] += 1
            else:
                counters['other'] += 1
        except Exception as e:
            print(f"    ⚠ Error importing {json_path.name}: {e}")

    return counters


def build_search_index(conn):
    """Populate the FTS5 search index from all tables."""
    print("  Building search index...")

    conn.execute("DELETE FROM search_index")

    conn.execute("""
        INSERT INTO search_index (name, content_type, description, source, content_id)
        SELECT s.name, 'spell', s.description, src.name, s.id
        FROM spells s LEFT JOIN sources src ON s.source_id = src.id
    """)

    conn.execute("""
        INSERT INTO search_index (name, content_type, description, source, content_id)
        SELECT f.name, 'feat', f.description, src.name, f.id
        FROM feats f LEFT JOIN sources src ON f.source_id = src.id
    """)

    conn.execute("""
        INSERT INTO search_index (name, content_type, description, source, content_id)
        SELECT c.name, 'class', c.description, src.name, c.id
        FROM classes c LEFT JOIN sources src ON c.source_id = src.id
    """)

    conn.execute("""
        INSERT INTO search_index (name, content_type, description, source, content_id)
        SELECT r.name, 'race', r.description, src.name, r.id
        FROM races r LEFT JOIN sources src ON r.source_id = src.id
    """)

    conn.execute("""
        INSERT INTO search_index (name, content_type, description, source, content_id)
        SELECT m.name, 'monster', m.description, src.name, m.id
        FROM monsters m LEFT JOIN sources src ON m.source_id = src.id
    """)

    conn.execute("""
        INSERT INTO search_index (name, content_type, description, source, content_id)
        SELECT e.name, 'equipment', e.description, src.name, e.id
        FROM equipment e LEFT JOIN sources src ON e.source_id = src.id
    """)

    conn.execute("""
        INSERT INTO search_index (name, content_type, description, source, content_id)
        SELECT m.name, 'magic_item', m.description, src.name, m.id
        FROM magic_items m LEFT JOIN sources src ON m.source_id = src.id
    """)

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM search_index").fetchone()[0]
    print(f"  ✓ Search index: {count} entries")


def main():
    print("=" * 60)
    print("Pathfinder 1e Content Database — PSRD Import")
    print("=" * 60)

    config = load_config()
    psrd_config = config["psrd_data"]
    data_dir = ROOT / psrd_config["local_path"]

    if not data_dir.exists():
        print(f"\n✗ PSRD-Data not found at {data_dir}")
        print("  Run 'python scripts/fetch_sources.py' first.")
        sys.exit(1)

    db_path = ROOT / config["database"]["path"]
    print(f"\nInitializing database...")
    conn = init_database(db_path, SCHEMA_PATH)

    total = {'spell': 0, 'feat': 0, 'skill': 0, 'class': 0, 'race': 0,
             'creature': 0, 'item': 0, 'other': 0}

    for book_folder, book_info in psrd_config["books"].items():
        book_name = book_folder.replace('_', ' ').title()
        abbrev = book_info["abbreviation"]
        source_id = ensure_source(conn, book_name, abbrev, book_folder)

        print(f"\n[{abbrev}] {book_name}...")
        counters = import_book(conn, data_dir, book_folder, book_info, source_id)
        conn.commit()

        total_for_book = sum(counters.values())
        conn.execute("UPDATE sources SET record_count = ? WHERE id = ?", (total_for_book, source_id))
        conn.commit()

        parts = [f"{v} {k}s" for k, v in counters.items() if v > 0]
        if parts:
            print(f"    → {', '.join(parts)}")
        else:
            print(f"    → (no typed records found — content may be in nested sections)")

        for k in total:
            total[k] += counters[k]

    print(f"\n--- Post-Processing ---")
    build_search_index(conn)

    print(f"\n{'=' * 60}")
    print(f"Import Complete!")
    print(f"{'=' * 60}")
    for k, v in total.items():
        if v > 0:
            print(f"  {k:12s}: {v:,}")
    print(f"  {'TOTAL':12s}: {sum(total.values()):,}")

    scl_count = conn.execute("SELECT COUNT(*) FROM spell_class_levels").fetchone()[0]
    print(f"\n  Spell-class associations: {scl_count:,}")

    db_size = db_path.stat().st_size / (1024 * 1024)
    print(f"\n  Database: {db_path} ({db_size:.1f} MB)")

    conn.close()


if __name__ == "__main__":
    main()