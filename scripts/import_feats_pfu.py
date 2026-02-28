#!/usr/bin/env python3
"""Phase 15c — Import feats from PathfinderUtilities (PFU).

Source:
  PathfinderUtilities/PFDB/dbs/feats/feats.js  (~3,523 feats, 29 pipe-delimited fields)

Merges with existing feats by case-insensitive name match:
  - Matched feats: fills in NULL/empty columns (benefit, prerequisites, etc.)
  - Unmatched feats: INSERTs as new rows with is_paizo_official=1
  - --overwrite: replaces existing non-NULL values too

Also populates prerequisite_feats (comma-separated names) from PFU structured pre_feat IDs.

Usage:
  python scripts/import_feats_pfu.py                # Full import to SQLite
  python scripts/import_feats_pfu.py --dry-run      # Preview without writing
  python scripts/import_feats_pfu.py --overwrite     # Replace existing values
  python scripts/import_feats_pfu.py --pfu-path PATH # Override feats.js location
"""

from __future__ import annotations

import argparse
import html as htmlmod
import pathlib
import re
import sqlite3

ROOT     = pathlib.Path(__file__).resolve().parent.parent
DB_PATH  = ROOT / "db" / "pf1e.db"
DEFAULT_PFU_PATH = ROOT.parent / "PathfinderUtilities" / "PFDB" / "dbs" / "feats" / "feats.js"

# ── PFU type array (0-indexed) ──────────────────────────────────────────────
PFU_TYPES = [
    'Achievement', 'Alignment', 'Armor Mastery', 'Betrayal', 'Blood Hex',
    'Called Shot', 'Combat', 'Combination', 'Conduit', 'Coven', 'Critical',
    'Damnation', 'Esoteric', 'Faction', 'Familiar', 'Gathlain Court Title',
    'General', 'Grit', 'Hero Point', 'Item Creation', 'Item Mastery',
    'Meditation', 'Metamagic', 'Monster', 'Mythic', 'Origin', 'Panache',
    'Performance', 'Possession', 'Shield Mastery', 'Stare', 'Story',
    'Style', 'Targeting', 'Teamwork', 'Trick', 'Weapon Mastery', 'Words Of Power',
]

# ── PFU source abbreviation array (0-indexed; source_gen is 1-indexed into this) ──
PFU_SOURCES = [
    'CR', 'Be', 'APG', 'UM', 'UC', 'ARG', 'UCA', 'MA', 'ACG', 'MC',
    'PU', 'OA', 'UI', 'HA', 'VC', 'AG', 'BD', 'UW', 'PA', 'CS',
    'PC', 'AP', 'AM', 'OP',
]

# PFU acronyms array for {{{N}}} expansion (0-indexed)
PFU_ACRONYMS = [
    'UC', 'MC', 'PotR', 'DTT', 'RTT', 'VC', 'APG', 'BotB', 'BoA', 'UW',
    'ARG', 'PA',
]

# Map PFU source abbreviation → our sources.id
# Existing source rows in DB
PFU_SOURCE_TO_DB: dict[str, int] = {
    'CR':  1,   # Core Rulebook
    'APG': 2,   # Advanced Player's Guide
    'ARG': 3,   # Advanced Race Guide
    'UM':  4,   # Ultimate Magic
    'UC':  5,   # Ultimate Combat
    'UCA': 7,   # Ultimate Campaign
    'Be':  8,   # Bestiary
    'MA':  13,  # Mythic Adventures
    'MC':  15,  # Monster Codex
    'ACG': 18,  # Advanced Class Guide
    'OA':  19,  # Occult Adventures
    'UI':  20,  # Ultimate Intrigue
    'UW':  21,  # Ultimate Wilderness
    'PU':  22,  # Pathfinder Unchained
    'AG':  23,  # Adventurer's Guide
}

# New source rows to create (abbreviation → (full name, abbreviation))
NEW_SOURCES: dict[str, tuple[str, str]] = {
    'HA': ('Horror Adventures', 'HA'),
    'VC': ('Villain Codex', 'VC'),
    'BD': ('Book of the Damned', 'BD'),
    'PA': ('Planar Adventures', 'PA'),
    'CS': ('Campaign Setting', 'CS'),
    'PC': ('Player Companion', 'PC'),
    'AP': ('Adventure Path', 'AP'),
    'AM': ('Adventure Module', 'AM'),
    'OP': ('Other Publications', 'OP'),
}

# Types that are "generic" — less specific than subtypes
_GENERIC_TYPES = {'Combat', 'General'}

# Field indices (0-based) in PFU pipe-delimited lines
F_ID             = 0
F_NAME           = 1
F_TYPE           = 2
F_PRE_AB_SCORE   = 3
F_PRE_FEAT       = 4
F_PRE_RACE       = 5
F_PRE_LEVEL      = 6
F_PRE_MTIER      = 7
F_PRE_CLASS      = 8
F_PRE_BAB        = 9
F_PRE_CASTER     = 10
F_PRE_SKILL      = 11
F_INTRO          = 12
F_DESCRIPTION    = 13
F_PREREQUISITES  = 14
F_BENEFIT        = 15
F_NORMAL         = 16
F_NOTE           = 17
F_GOAL           = 18
F_COMPLETION     = 19
F_RESIDUAL       = 20
F_SPECIAL        = 21
F_SUGGESTED      = 22
F_COMBAT_TRICK   = 23
F_SOURCE_CT      = 24
F_PAGE_CT        = 25
F_SOURCE_GEN     = 26
F_SOURCE_DET     = 27
F_PAGE           = 28

NUM_FIELDS = 29

# Words that should stay lowercase in title case (unless first word)
_MINOR_WORDS = {
    'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'yet', 'so',
    'at', 'by', 'in', 'of', 'on', 'to', 'up', 'as', 'if', 'vs', 'via',
    'from', 'into', 'with',
}


def _capitalize_word(word: str) -> str:
    """Capitalize a word, handling hyphens and parentheses."""
    # Handle parenthesized words: (mythic) → (Mythic)
    if word.startswith('(') and len(word) > 1:
        return '(' + _capitalize_word(word[1:])
    # Handle hyphenated words: two-weapon → Two-Weapon
    if '-' in word:
        return '-'.join(_capitalize_word(p) for p in word.split('-'))
    return word.capitalize()


def title_case(name: str) -> str:
    """Title-case a feat name, keeping minor words lowercase (except first/last)."""
    words = name.strip().split()
    if not words:
        return name
    result = []
    for i, w in enumerate(words):
        # Always capitalize first and last word
        if i == 0 or i == len(words) - 1:
            result.append(_capitalize_word(w))
        elif w.lower() in _MINOR_WORDS:
            result.append(w.lower())
        else:
            result.append(_capitalize_word(w))
    return ' '.join(result)


def strip_pfu_markup(text: str) -> str:
    """Strip PFU-specific markup from text fields."""
    if not text:
        return ''
    # ´´´text´´´ → text (italic markers)
    text = text.replace('´´´', '')
    # '''text''' → text (bold markers)
    text = text.replace("'''", '')
    # [[[N]]] → remove (table references)
    text = re.sub(r'\[\[\[\d+\]\]\]', '', text)
    # {{{N}}} → expand from acronyms array
    def expand_acronym(m: re.Match) -> str:
        idx = int(m.group(1))
        if 0 <= idx < len(PFU_ACRONYMS):
            return PFU_ACRONYMS[idx]
        return m.group(0)
    text = re.sub(r'\{\{\{(\d+)\}\}\}', expand_acronym, text)
    # <br /> → space
    text = re.sub(r'<br\s*/?\s*>', ' ', text, flags=re.IGNORECASE)
    # HTML entities
    text = htmlmod.unescape(text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def resolve_type(type_str: str) -> str:
    """Resolve PFU type field (semicolon-separated indices) to a single feat type."""
    if not type_str.strip():
        return 'General'
    indices = []
    for part in type_str.split(';'):
        part = part.strip()
        if part.isdigit():
            indices.append(int(part))
    if not indices:
        return 'General'

    # Resolve to type names
    type_names = []
    for idx in indices:
        if 0 <= idx < len(PFU_TYPES):
            type_names.append(PFU_TYPES[idx])
        else:
            type_names.append('General')

    # If Mythic is present, use Mythic
    if 'Mythic' in type_names:
        return 'Mythic'

    # Pick most specific: prefer non-generic types
    specific = [t for t in type_names if t not in _GENERIC_TYPES]
    if specific:
        return specific[0]

    return type_names[0]


def resolve_source(source_gen_str: str) -> str | None:
    """Resolve PFU source_gen (1-indexed) to PFU source abbreviation."""
    if not source_gen_str.strip():
        return None
    try:
        idx = int(source_gen_str) - 1  # 1-indexed → 0-indexed
        if 0 <= idx < len(PFU_SOURCES):
            return PFU_SOURCES[idx]
    except ValueError:
        pass
    return None


def parse_feats_js(path: pathlib.Path) -> dict[int, dict]:
    """Parse PFU feats.js into {pfu_id: parsed_dict}.

    For duplicate IDs, keeps the first row with a non-empty name.
    """
    feats: dict[int, dict] = {}
    skipped_lines = 0

    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.rstrip('\n').rstrip('\r')

            # Skip JS wrapper lines
            if line.startswith('var ') or line.startswith('`') or line.startswith("`;"):
                continue
            if '.split(' in line:
                continue

            # Skip comments and blank lines
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            fields = line.split('|')
            if len(fields) != NUM_FIELDS:
                skipped_lines += 1
                continue

            # Parse ID
            try:
                pfu_id = int(fields[F_ID].strip())
            except ValueError:
                skipped_lines += 1
                continue

            name = fields[F_NAME].strip()
            if not name:
                # Duplicate row with empty name — skip
                if pfu_id in feats:
                    continue
                # Row with no name at all — skip
                skipped_lines += 1
                continue

            # Keep first row with non-empty name per ID
            if pfu_id in feats:
                continue

            feats[pfu_id] = {
                'pfu_id':       pfu_id,
                'name':         name,
                'type_raw':     fields[F_TYPE].strip(),
                'pre_feat':     fields[F_PRE_FEAT].strip(),
                'pre_bab':      fields[F_PRE_BAB].strip(),
                'pre_class':    fields[F_PRE_CLASS].strip(),
                'pre_skill':    fields[F_PRE_SKILL].strip(),
                'intro':        fields[F_INTRO].strip(),
                'description':  fields[F_DESCRIPTION].strip(),
                'prerequisites': fields[F_PREREQUISITES].strip(),
                'benefit':      fields[F_BENEFIT].strip(),
                'normal':       fields[F_NORMAL].strip(),
                'note':         fields[F_NOTE].strip(),
                'goal':         fields[F_GOAL].strip(),
                'completion':   fields[F_COMPLETION].strip(),
                'special':      fields[F_SPECIAL].strip(),
                'source_gen':   fields[F_SOURCE_GEN].strip(),
                'source_det':   fields[F_SOURCE_DET].strip(),
            }

    if skipped_lines:
        print(f"  Skipped {skipped_lines} unparseable lines")

    return feats


def ensure_sources(conn: sqlite3.Connection, dry_run: bool) -> dict[str, int]:
    """Create any missing source rows. Returns full PFU abbrev → source_id map."""
    mapping = dict(PFU_SOURCE_TO_DB)
    cur = conn.cursor()

    for abbrev, (full_name, db_abbrev) in NEW_SOURCES.items():
        # Check if already exists
        cur.execute("SELECT id FROM sources WHERE abbreviation = ?", (db_abbrev,))
        row = cur.fetchone()
        if row:
            mapping[abbrev] = row[0]
        else:
            if dry_run:
                print(f"  [NEW SOURCE] {full_name} ({db_abbrev})")
                mapping[abbrev] = -1  # Placeholder
            else:
                cur.execute(
                    "INSERT INTO sources (name, abbreviation) VALUES (?, ?)",
                    (full_name, db_abbrev),
                )
                mapping[abbrev] = cur.lastrowid
                print(f"  Created source: {full_name} ({db_abbrev}) → id={cur.lastrowid}")

    if not dry_run:
        conn.commit()

    return mapping


def build_prereq_feat_names(pfu_feats: dict[int, dict]) -> dict[int, str]:
    """Build pfu_id → title-cased name map for resolving pre_feat references."""
    result = {}
    for pfu_id, f in pfu_feats.items():
        name = title_case(f['name'])
        # Mythic feats: append ", Mythic" to match DB naming convention
        if resolve_type(f['type_raw']) == 'Mythic':
            name = f"{name}, Mythic"
        result[pfu_id] = name
    return result


def resolve_prereq_feats(pre_feat_str: str, id_to_name: dict[int, str]) -> str:
    """Resolve semicolon-separated PFU feat IDs to comma-separated feat names."""
    if not pre_feat_str:
        return ''
    parts = []
    for part in pre_feat_str.split(';'):
        part = part.strip()
        if not part:
            continue
        try:
            feat_id = int(part)
            name = id_to_name.get(feat_id)
            if name:
                parts.append(name)
        except ValueError:
            continue
    return ', '.join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without writing to DB')
    parser.add_argument('--overwrite', action='store_true',
                        help='Replace existing non-NULL values')
    parser.add_argument('--pfu-path', type=pathlib.Path, default=DEFAULT_PFU_PATH,
                        help='Path to PFU feats.js')
    args = parser.parse_args()

    print("Phase 15c — Import feats from PathfinderUtilities")
    if args.dry_run:
        print("  (DRY RUN — no DB changes)")
    if args.overwrite:
        print("  (OVERWRITE mode — replacing existing values)")

    # ── Validate source file ─────────────────────────────────────────────────
    pfu_path = args.pfu_path
    if not pfu_path.exists():
        print(f"ERROR: {pfu_path} not found")
        return

    # ── Parse PFU data ───────────────────────────────────────────────────────
    print(f"  Parsing {pfu_path} ...")
    pfu_feats = parse_feats_js(pfu_path)
    print(f"  Parsed {len(pfu_feats):,} unique PFU feats")

    # Build prereq name map
    id_to_name = build_prereq_feat_names(pfu_feats)

    # ── Connect to DB ────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── Ensure source rows exist ─────────────────────────────────────────────
    source_map = ensure_sources(conn, args.dry_run)

    # ── Load existing feats ──────────────────────────────────────────────────
    cur.execute(
        "SELECT id, name, feat_type, prerequisites, prerequisite_feats, "
        "benefit, normal, special, description, is_paizo_official FROM feats"
    )
    db_feats: dict[str, sqlite3.Row] = {}
    for r in cur.fetchall():
        db_feats[r['name'].strip().lower()] = r

    print(f"  Existing DB feats: {len(db_feats):,}")

    # ── Process each PFU feat ────────────────────────────────────────────────
    inserted = 0
    updated = 0
    matched_no_change = 0
    source_dist: dict[str, int] = {}
    type_dist: dict[str, int] = {}

    for pfu_id, pf in sorted(pfu_feats.items()):
        # Resolve fields
        tc_name = title_case(pf['name'])
        feat_type = resolve_type(pf['type_raw'])
        pfu_source = resolve_source(pf['source_gen'])
        source_id = source_map.get(pfu_source) if pfu_source else None

        # Strip markup from text fields
        benefit = strip_pfu_markup(pf['benefit'])
        prerequisites = strip_pfu_markup(pf['prerequisites'])
        normal = strip_pfu_markup(pf['normal'])
        description = strip_pfu_markup(pf['description'])

        # Special field: append story feat data if present
        special = strip_pfu_markup(pf['special'])
        goal = strip_pfu_markup(pf['goal'])
        completion = strip_pfu_markup(pf['completion'])
        if goal or completion:
            parts = []
            if special:
                parts.append(special)
            if goal:
                parts.append(f"Goal: {goal}")
            if completion:
                parts.append(f"Completion Benefit: {completion}")
            special = ' '.join(parts)

        # Resolve prerequisite feat IDs to names
        prereq_feats = resolve_prereq_feats(pf['pre_feat'], id_to_name)

        # Track distributions
        type_dist[feat_type] = type_dist.get(feat_type, 0) + 1
        if pfu_source:
            source_dist[pfu_source] = source_dist.get(pfu_source, 0) + 1

        # ── Match against existing DB feats ──────────────────────────────────
        key = tc_name.strip().lower()
        existing = db_feats.get(key)

        # Mythic feats: PFU uses same name + type 24; our DB uses ", Mythic" suffix
        if existing is None and feat_type == 'Mythic':
            mythic_key = f"{key}, mythic"
            existing = db_feats.get(mythic_key)
            if existing:
                tc_name = f"{tc_name}, Mythic"
                key = mythic_key

        if existing is None:
            # ── INSERT new feat ──────────────────────────────────────────────
            if args.dry_run:
                inserted += 1
            else:
                cur.execute(
                    """INSERT INTO feats
                      (name, source_id, feat_type, prerequisites, prerequisite_feats,
                       benefit, normal, special, description, is_paizo_official)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (tc_name,
                     source_id,
                     feat_type,
                     prerequisites or None,
                     prereq_feats or None,
                     benefit or None,
                     normal or None,
                     special or None,
                     description or None),
                )
                inserted += 1
        else:
            # ── UPDATE existing feat ─────────────────────────────────────────
            updates: dict[str, str | int] = {}

            # Columns to conditionally fill
            for col, new_val in [
                ('feat_type',          feat_type),
                ('prerequisites',      prerequisites),
                ('prerequisite_feats', prereq_feats),
                ('benefit',            benefit),
                ('normal',             normal),
                ('special',            special),
                ('description',        description),
            ]:
                if not new_val:
                    continue
                existing_val = existing[col] if col in existing.keys() else None
                if args.overwrite or not existing_val:
                    updates[col] = new_val

            # Set is_paizo_official=1 if it was 0
            if existing['is_paizo_official'] == 0:
                updates['is_paizo_official'] = 1

            if updates:
                if args.dry_run:
                    updated += 1
                else:
                    set_clause = ', '.join(f'{c} = ?' for c in updates)
                    cur.execute(
                        f"UPDATE feats SET {set_clause} WHERE id = ?",
                        (*updates.values(), existing['id']),
                    )
                    updated += 1
            else:
                matched_no_change += 1

    if not args.dry_run:
        conn.commit()

    # ── Report ───────────────────────────────────────────────────────────────
    total_matched = updated + matched_no_change
    print(f"\n  Results:")
    print(f"    PFU feats parsed:    {len(pfu_feats):,}")
    print(f"    Matched existing:    {total_matched:,} ({updated:,} updated, {matched_no_change:,} unchanged)")
    print(f"    New feats inserted:  {inserted:,}")

    print(f"\n  PFU type distribution:")
    for t, c in sorted(type_dist.items(), key=lambda x: -x[1]):
        print(f"    {t:30s} {c:>5}")

    print(f"\n  PFU source distribution (top 15):")
    for s, c in sorted(source_dist.items(), key=lambda x: -x[1])[:15]:
        print(f"    {s:6s} {c:>5}")

    conn.close()

    # ── Verification ─────────────────────────────────────────────────────────
    if not args.dry_run:
        print("\n  Verification:")
        conn2 = sqlite3.connect(DB_PATH)
        conn2.row_factory = sqlite3.Row
        cur2 = conn2.cursor()

        cur2.execute("SELECT COUNT(*) as cnt FROM feats")
        total = cur2.fetchone()['cnt']
        cur2.execute("SELECT COUNT(*) as cnt FROM feats WHERE benefit IS NOT NULL AND benefit <> ''")
        with_benefit = cur2.fetchone()['cnt']
        cur2.execute("SELECT COUNT(*) as cnt FROM feats WHERE prerequisite_feats IS NOT NULL AND prerequisite_feats <> ''")
        with_prereqs = cur2.fetchone()['cnt']
        cur2.execute("SELECT COUNT(*) as cnt FROM feats WHERE is_paizo_official = 1")
        paizo = cur2.fetchone()['cnt']

        print(f"    Total feats:           {total:,}")
        print(f"    With benefit text:     {with_benefit:,} ({with_benefit*100//total}%)")
        print(f"    With prerequisite_feats: {with_prereqs:,}")
        print(f"    Paizo official:        {paizo:,}")

        conn2.close()

    print("\nDone.")


if __name__ == '__main__':
    main()
