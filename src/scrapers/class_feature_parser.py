#!/usr/bin/env python3
"""
class_feature_parser.py — Parse class features/options from d20pfsrd.com.

Handles two patterns of class sub-features:

TYPE A — Individual pickable features (selected at level-up):
  Rage Powers, Rogue Talents, Investigator Talents, Alchemist Discoveries,
  Magus Arcana, Arcanist Exploits, Witch Hexes, Ninja Tricks, Slayer Talents,
  Gunslinger Deeds, Swashbuckler Deeds, Warpriest Blessings, etc.

  Schema:
    { "name", "parent_class", "feature_category", "feature_type",
      "prerequisites", "benefit", "description", "source" }

TYPE B — Package selections (chosen once, grants a bundle of abilities):
  Sorcerer Bloodlines, Bloodrager Bloodlines, Cleric Domains, Oracle Mysteries,
  Wizard Schools, Shaman Spirits, Cavalier/Samurai Orders,
  Ranger Combat Styles, etc.

  Schema:
    { "name", "parent_class", "feature_category", "class_skill",
      "bonus_spells", "bonus_feats", "description", "powers", "source" }

Discovery: The manifest phase crawls known index pages for each class's
feature type, collecting individual sub-page URLs.
"""

import re
from pathlib import Path

from .base import (
    BASE_URL, fetch_page, parse_html, extract_text,
    save_json, is_paizo_content, is_valid_content_url,
    normalize_url,
)

# ============================================================
# CLASS FEATURE INDEX DEFINITIONS
# ============================================================
# Each entry maps a class to its feature sub-page index URL(s)
# and metadata about what kind of features live there.

CLASS_FEATURE_INDEXES = {
    # --- Core Classes ---
    'barbarian_rage_powers': {
        'parent_class': 'Barbarian',
        'feature_category': 'Rage Power',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/barbarian/rage-powers/',
        ],
        'type': 'A',  # individual pickable
    },
    'bard_masterpieces': {
        'parent_class': 'Bard',
        'feature_category': 'Bardic Masterpiece',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/bard/bardic-masterpieces/',
        ],
        'type': 'A',
    },
    'cleric_domains': {
        'parent_class': 'Cleric',
        'feature_category': 'Domain',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/cleric/domains/',
        ],
        'type': 'B',  # package selection
    },
    'druid_companions': {
        'parent_class': 'Druid',
        'feature_category': 'Animal Companion',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/druid/animal-companions/',
        ],
        'type': 'B',
    },
    'monk_ki_powers': {
        'parent_class': 'Monk (Unchained)',
        'feature_category': 'Ki Power',
        'index_urls': [
            f'{BASE_URL}/classes/unchained-classes/monk/ki-powers/',
        ],
        'type': 'A',
    },
    'paladin_mercies': {
        'parent_class': 'Paladin',
        'feature_category': 'Mercy',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/paladin/mercy/',
        ],
        'type': 'A',
    },
    'ranger_combat_styles': {
        'parent_class': 'Ranger',
        'feature_category': 'Combat Style',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/ranger/ranger-combat-styles/',
        ],
        'type': 'B',
    },
    'rogue_talents': {
        'parent_class': 'Rogue',
        'feature_category': 'Rogue Talent',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/rogue/rogue-talents/',
        ],
        'type': 'A',
    },
    'sorcerer_bloodlines': {
        'parent_class': 'Sorcerer',
        'feature_category': 'Bloodline',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/sorcerer/bloodlines/',
        ],
        'type': 'B',
    },
    'wizard_schools': {
        'parent_class': 'Wizard',
        'feature_category': 'Arcane School',
        'index_urls': [
            f'{BASE_URL}/classes/core-classes/wizard/arcane-schools/',
        ],
        'type': 'B',
    },

    # --- Base Classes ---
    'alchemist_discoveries': {
        'parent_class': 'Alchemist',
        'feature_category': 'Discovery',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/alchemist/discoveries/',
        ],
        'type': 'A',
    },
    'cavalier_orders': {
        'parent_class': 'Cavalier',
        'feature_category': 'Order',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/cavalier/orders/',
        ],
        'type': 'B',
    },
    'gunslinger_deeds': {
        'parent_class': 'Gunslinger',
        'feature_category': 'Deed',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/gunslinger/deeds/',
        ],
        'type': 'A',
    },
    'inquisitor_inquisitions': {
        'parent_class': 'Inquisitor',
        'feature_category': 'Inquisition',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/inquisitor/inquisitions/',
        ],
        'type': 'B',
    },
    'magus_arcana': {
        'parent_class': 'Magus',
        'feature_category': 'Magus Arcana',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/magus/magus-arcana/',
        ],
        'type': 'A',
    },
    'oracle_mysteries': {
        'parent_class': 'Oracle',
        'feature_category': 'Mystery',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/oracle/oracle-mysteries/',
        ],
        'type': 'B',
    },
    'summoner_evolutions': {
        'parent_class': 'Summoner',
        'feature_category': 'Evolution',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/summoner/eidolons/',
        ],
        'type': 'A',
    },
    'witch_hexes': {
        'parent_class': 'Witch',
        'feature_category': 'Hex',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/witch/hexes/',
        ],
        'type': 'A',
    },
    'witch_patrons': {
        'parent_class': 'Witch',
        'feature_category': 'Patron',
        'index_urls': [
            f'{BASE_URL}/classes/base-classes/witch/witch-patrons/',
        ],
        'type': 'B',
    },

    # --- Hybrid Classes ---
    'arcanist_exploits': {
        'parent_class': 'Arcanist',
        'feature_category': 'Exploit',
        'index_urls': [
            f'{BASE_URL}/classes/hybrid-classes/arcanist/arcanist-exploits/',
        ],
        'type': 'A',
    },
    'bloodrager_bloodlines': {
        'parent_class': 'Bloodrager',
        'feature_category': 'Bloodline',
        'index_urls': [
            f'{BASE_URL}/classes/hybrid-classes/bloodrager/bloodlines/',
        ],
        'type': 'B',
    },
    'investigator_talents': {
        'parent_class': 'Investigator',
        'feature_category': 'Investigator Talent',
        'index_urls': [
            f'{BASE_URL}/classes/hybrid-classes/investigator/investigator-talents/',
        ],
        'type': 'A',
    },
    'shaman_spirits': {
        'parent_class': 'Shaman',
        'feature_category': 'Spirit',
        'index_urls': [
            f'{BASE_URL}/classes/hybrid-classes/shaman/spirits/',
        ],
        'type': 'B',
    },
    'slayer_talents': {
        'parent_class': 'Slayer',
        'feature_category': 'Slayer Talent',
        'index_urls': [
            f'{BASE_URL}/classes/hybrid-classes/slayer/slayer-talents/',
        ],
        'type': 'A',
    },
    'swashbuckler_deeds': {
        'parent_class': 'Swashbuckler',
        'feature_category': 'Deed',
        'index_urls': [
            f'{BASE_URL}/classes/hybrid-classes/swashbuckler/swashbuckler-deeds/',
        ],
        'type': 'A',
    },
    'warpriest_blessings': {
        'parent_class': 'Warpriest',
        'feature_category': 'Blessing',
        'index_urls': [
            f'{BASE_URL}/classes/hybrid-classes/warpriest/blessings/',
        ],
        'type': 'B',
    },

    # --- Alternate Classes ---
    'ninja_tricks': {
        'parent_class': 'Ninja',
        'feature_category': 'Ninja Trick',
        'index_urls': [
            f'{BASE_URL}/classes/alternate-classes/ninja/ninja-tricks/',
        ],
        'type': 'A',
    },
    'samurai_orders': {
        'parent_class': 'Samurai',
        'feature_category': 'Order',
        'index_urls': [
            f'{BASE_URL}/classes/alternate-classes/samurai/orders/',
        ],
        'type': 'B',
    },

    # --- Occult Classes ---
    'kineticist_wild_talents': {
        'parent_class': 'Kineticist',
        'feature_category': 'Wild Talent',
        'index_urls': [
            f'{BASE_URL}/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/kineticist/kineticist-wild-talents/',
        ],
        'type': 'A',
    },
    'mesmerist_tricks': {
        'parent_class': 'Mesmerist',
        'feature_category': 'Mesmerist Trick',
        'index_urls': [
            f'{BASE_URL}/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/mesmerist/mesmerist-tricks/',
        ],
        'type': 'A',
    },
    'medium_spirits': {
        'parent_class': 'Medium',
        'feature_category': 'Spirit',
        'index_urls': [
            f'{BASE_URL}/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/medium/spirits/',
        ],
        'type': 'B',
    },
    'occultist_implement_schools': {
        'parent_class': 'Occultist',
        'feature_category': 'Implement School',
        'index_urls': [
            f'{BASE_URL}/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/occultist/implement-schools/',
        ],
        'type': 'B',
    },
    'psychic_disciplines': {
        'parent_class': 'Psychic',
        'feature_category': 'Discipline',
        'index_urls': [
            f'{BASE_URL}/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/psychic/psychic-disciplines/',
        ],
        'type': 'B',
    },
}


# ============================================================
# FEATURE TYPE DETECTION
# ============================================================

FEATURE_TYPE_PATTERN = re.compile(r'\((Ex|Su|Sp)\)\s*$')


def _extract_feature_type(name: str) -> tuple[str, str]:
    """Extract (Ex), (Su), (Sp) from feature name.

    Returns (clean_name, feature_type).
    """
    m = FEATURE_TYPE_PATTERN.search(name)
    if m:
        return name[:m.start()].strip(), m.group(1)
    return name, ''


# ============================================================
# TYPE A: INDIVIDUAL FEATURE PARSER
# ============================================================

# Benefit extraction (same patterns as traits)
BENEFIT_PATTERN = re.compile(
    r'Benefits?\s*\(?s?\)?[:\s]+(.+)',
    re.IGNORECASE | re.DOTALL,
)

# Prerequisite extraction
PREREQ_PATTERN = re.compile(
    r'Prerequisites?\s*\(?s?\)?[:\s]+(.+?)(?:\s*(?:Benefit|$))',
    re.IGNORECASE | re.DOTALL,
)

# Source extraction
SOURCE_PATTERN = re.compile(
    r'(?:Pathfinder (?:Roleplaying Game|Player Companion|Campaign Setting)[:\s]*)'
    r'([^.©]+)',
    re.IGNORECASE,
)

# Copyright cutoff strings
COPYRIGHT_CUTOFFS = [
    'Section 15:', 'Source:', 'Source PZO',
    'Pathfinder Roleplaying Game',
    'Pathfinder Player Companion',
    'Pathfinder Campaign Setting',
    'Pathfinder Chronicles',
    'Pathfinder Companion',
    'Join Our Discord',
]


def _clean_text_block(text: str) -> str:
    """Remove copyright/ad cruft from the end of text."""
    for cutoff in COPYRIGHT_CUTOFFS:
        idx = text.find(cutoff)
        if idx > 0:
            text = text[:idx]
    return text.strip().rstrip('.')


def parse_feature_type_a(url: str, html: str | None = None,
                         parent_class: str = '',
                         feature_category: str = '') -> dict | None:
    """Parse a single pickable class feature page.

    Structure: Name (type), Prerequisite, Benefit, Source.

    Args:
        url: Feature page URL.
        html: Pre-fetched HTML (optional).
        parent_class: Class this feature belongs to.
        feature_category: Category name (e.g., "Rage Power", "Investigator Talent").

    Returns:
        Parsed feature dict or None.
    """
    if html is None:
        html = fetch_page(url)
    if not html:
        return None

    soup = parse_html(html)

    content = (
        soup.select_one('article .article-content')
        or soup.select_one('div.article-content')
        or soup.select_one('article')
    )
    if not content:
        return None

    # Get name from h1
    h1 = content.select_one('h1') or soup.select_one('h1')
    if not h1:
        return None

    raw_name = extract_text(h1).strip()
    if not raw_name:
        return None

    # Extract feature type (Ex/Su/Sp)
    clean_name, feature_type = _extract_feature_type(raw_name)

    # Get full text
    full_text = extract_text(content)

    # Extract prerequisite
    prerequisites = ''
    m = PREREQ_PATTERN.search(full_text)
    if m:
        prereq_text = m.group(1).strip()
        prereq_text = _clean_text_block(prereq_text)
        # Also stop at "Benefit"
        benefit_idx = re.search(r'Benefits?\s*\(?s?\)?:', prereq_text, re.IGNORECASE)
        if benefit_idx:
            prereq_text = prereq_text[:benefit_idx.start()]
        prerequisites = prereq_text.strip().rstrip('.,;')
        if len(prerequisites) > 300:
            prerequisites = prerequisites[:300]

    # Extract benefit
    benefit = ''
    m = BENEFIT_PATTERN.search(full_text)
    if m:
        benefit = _clean_text_block(m.group(1))

    # Description: text before Prerequisite or Benefit
    description = ''
    first_marker = None
    for pattern_str in [r'Prerequisites?\s*\(?s?\)?:', r'Benefits?\s*\(?s?\)?:',
                        r'Note:']:
        fm = re.search(pattern_str, full_text, re.IGNORECASE)
        if fm:
            if first_marker is None or fm.start() < first_marker:
                first_marker = fm.start()

    if first_marker and first_marker > 0:
        desc = full_text[:first_marker].strip()
        # Remove the feature name from the start
        if desc.lower().startswith(clean_name.lower()):
            desc = desc[len(clean_name):].strip()
        description = desc[:500]

    # Detect parent class from URL if not provided
    if not parent_class:
        parent_class = _detect_parent_class_from_url(url)

    # Detect feature category from URL if not provided
    if not feature_category:
        feature_category = _detect_category_from_url(url)

    # Extract source
    source = ''
    sm = SOURCE_PATTERN.search(full_text)
    if sm:
        source = sm.group(1).strip().rstrip('.')
        source = re.sub(r'\s*©.*$', '', source)
        source = re.sub(r'\s*Copyright.*$', '', source, flags=re.IGNORECASE)
        if len(source) > 80:
            source = source[:80]

    # Skip 3pp
    if not is_paizo_content(url):
        return None

    # Must have some content
    if not benefit and not description:
        return None

    return {
        'name': clean_name,
        'url': url,
        'parent_class': parent_class,
        'feature_category': feature_category,
        'feature_type': feature_type,
        'prerequisites': prerequisites,
        'benefit': benefit[:2000],
        'description': description,
        'source': source,
        'selection_type': 'individual',
    }


# ============================================================
# TYPE B: PACKAGE SELECTION PARSER
# ============================================================

# Structured field patterns for bloodlines, domains, etc.
CLASS_SKILL_PATTERN = re.compile(
    r'Class Skill[s]?[:\s]+(.+?)(?:\.|Bonus)',
    re.IGNORECASE,
)

BONUS_SPELLS_PATTERN = re.compile(
    r'Bonus Spells?[:\s]+(.+?)(?:Bonus Feat|Bloodline Arcana|$)',
    re.IGNORECASE | re.DOTALL,
)

BONUS_FEATS_PATTERN = re.compile(
    r'Bonus Feats?[:\s]+(.+?)(?:Bloodline Arcana|Bloodline Powers?|Domain Powers?|$)',
    re.IGNORECASE | re.DOTALL,
)

BLOODLINE_ARCANA_PATTERN = re.compile(
    r'Bloodline Arcana[:\s]+(.+?)(?:Bloodline Powers?|$)',
    re.IGNORECASE | re.DOTALL,
)


def _parse_bonus_spells(text: str) -> list[dict]:
    """Parse bonus spell list: 'cause fear (3rd), bull's strength (5th), ...'"""
    spells = []
    for m in re.finditer(r'([^,()]+?)\s*\((\d+)(?:st|nd|rd|th)\)', text):
        spell_name = m.group(1).strip().strip(',').strip()
        level = int(m.group(2))
        if spell_name and level:
            spells.append({'spell': spell_name, 'level': level})
    return spells


def _parse_bonus_feat_list(text: str) -> list[str]:
    """Parse comma-separated feat list."""
    text = _clean_text_block(text)
    feats = [f.strip().rstrip('.') for f in text.split(',')]
    return [f for f in feats if f and len(f) < 80]


def parse_feature_type_b(url: str, html: str | None = None,
                         parent_class: str = '',
                         feature_category: str = '') -> dict | None:
    """Parse a package selection page (bloodline, domain, mystery, etc.).

    Args:
        url: Feature page URL.
        html: Pre-fetched HTML (optional).
        parent_class: Class this feature belongs to.
        feature_category: Category name (e.g., "Bloodline", "Domain").

    Returns:
        Parsed feature dict or None.
    """
    if html is None:
        html = fetch_page(url)
    if not html:
        return None

    soup = parse_html(html)

    content = (
        soup.select_one('article .article-content')
        or soup.select_one('div.article-content')
        or soup.select_one('article')
    )
    if not content:
        return None

    # Get name from h1
    h1 = content.select_one('h1') or soup.select_one('h1')
    if not h1:
        return None

    raw_name = extract_text(h1).strip()
    if not raw_name:
        return None

    # Clean name: remove "Bloodline", "Domain" suffix if redundant
    clean_name = raw_name

    # Get full text
    full_text = extract_text(content)

    # Description: first paragraph (flavor text)
    description = ''
    # Find first paragraph of content after the h1
    for p in content.find_all(['p', 'div'], recursive=False):
        text = extract_text(p).strip()
        if text and len(text) > 20 and not text.startswith('Home >'):
            description = text[:500]
            break

    # Detect parent class
    if not parent_class:
        parent_class = _detect_parent_class_from_url(url)
    if not feature_category:
        feature_category = _detect_category_from_url(url)

    # Extract structured data
    class_skill = ''
    m = CLASS_SKILL_PATTERN.search(full_text)
    if m:
        class_skill = m.group(1).strip().rstrip('.')

    bonus_spells = []
    m = BONUS_SPELLS_PATTERN.search(full_text)
    if m:
        bonus_spells = _parse_bonus_spells(m.group(1))

    bonus_feats = []
    m = BONUS_FEATS_PATTERN.search(full_text)
    if m:
        bonus_feats = _parse_bonus_feat_list(m.group(1))

    bloodline_arcana = ''
    m = BLOODLINE_ARCANA_PATTERN.search(full_text)
    if m:
        bloodline_arcana = _clean_text_block(m.group(1))[:500]

    # Extract powers: look for h4/h5 headings within the content
    # that describe individual powers at specific levels
    powers = []
    for heading in content.find_all(['h4', 'h5', 'h3']):
        heading_text = extract_text(heading).strip()
        if not heading_text:
            continue

        # Extract level from text like "At 1st level" or "(1st)"
        level = None
        level_m = re.search(r'(\d+)(?:st|nd|rd|th)', heading_text)
        if level_m:
            level = int(level_m.group(1))

        # Get feature type
        fname, ftype = _extract_feature_type(heading_text)

        # Get description from siblings until next heading
        power_desc = []
        for sib in heading.find_next_siblings():
            if sib.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                break
            sib_text = extract_text(sib).strip()
            if sib_text:
                power_desc.append(sib_text)

        desc = ' '.join(power_desc)[:500]

        if fname:
            powers.append({
                'name': fname,
                'feature_type': ftype,
                'level': level,
                'description': desc,
            })

    # Extract source
    source = ''
    sm = SOURCE_PATTERN.search(full_text)
    if sm:
        source = sm.group(1).strip().rstrip('.')
        source = re.sub(r'\s*©.*$', '', source)
        source = re.sub(r'\s*Copyright.*$', '', source, flags=re.IGNORECASE)

    # Skip 3pp
    if not is_paizo_content(url):
        return None

    # Must have some content
    if not description and not powers and not bonus_spells:
        return None

    result = {
        'name': clean_name,
        'url': url,
        'parent_class': parent_class,
        'feature_category': feature_category,
        'description': description,
        'source': source[:80] if source else '',
        'selection_type': 'package',
    }

    # Add structured fields if present
    if class_skill:
        result['class_skill'] = class_skill
    if bonus_spells:
        result['bonus_spells'] = bonus_spells
    if bonus_feats:
        result['bonus_feats'] = bonus_feats
    if bloodline_arcana:
        result['bloodline_arcana'] = bloodline_arcana
    if powers:
        result['powers'] = powers

    return result


# ============================================================
# URL DETECTION HELPERS
# ============================================================

# Map URL path segments to parent class names
_CLASS_FROM_URL = {
    'barbarian': 'Barbarian', 'bard': 'Bard', 'cleric': 'Cleric',
    'druid': 'Druid', 'fighter': 'Fighter', 'monk': 'Monk',
    'paladin': 'Paladin', 'ranger': 'Ranger', 'rogue': 'Rogue',
    'sorcerer': 'Sorcerer', 'wizard': 'Wizard',
    'alchemist': 'Alchemist', 'cavalier': 'Cavalier',
    'gunslinger': 'Gunslinger', 'inquisitor': 'Inquisitor',
    'magus': 'Magus', 'oracle': 'Oracle', 'summoner': 'Summoner',
    'witch': 'Witch',
    'arcanist': 'Arcanist', 'bloodrager': 'Bloodrager',
    'brawler': 'Brawler', 'hunter': 'Hunter',
    'investigator': 'Investigator', 'shaman': 'Shaman',
    'skald': 'Skald', 'slayer': 'Slayer',
    'swashbuckler': 'Swashbuckler', 'warpriest': 'Warpriest',
    'ninja': 'Ninja', 'samurai': 'Samurai',
    'antipaladin': 'Antipaladin',
    'kineticist': 'Kineticist', 'medium': 'Medium',
    'mesmerist': 'Mesmerist', 'occultist': 'Occultist',
    'psychic': 'Psychic', 'spiritualist': 'Spiritualist',
}

# Map URL segments to feature categories
_CATEGORY_FROM_URL = {
    'rage-powers': 'Rage Power',
    'rogue-talents': 'Rogue Talent',
    'investigator-talents': 'Investigator Talent',
    'discoveries': 'Discovery',
    'magus-arcana': 'Magus Arcana',
    'arcanist-exploits': 'Exploit',
    'hexes': 'Hex',
    'ninja-tricks': 'Ninja Trick',
    'slayer-talents': 'Slayer Talent',
    'deeds': 'Deed',
    'swashbuckler-deeds': 'Deed',
    'gunslinger-deeds': 'Deed',
    'bloodlines': 'Bloodline',
    'domains': 'Domain',
    'mysteries': 'Mystery',
    'oracle-mysteries': 'Mystery',
    'arcane-schools': 'Arcane School',
    'orders': 'Order',
    'spirits': 'Spirit',
    'blessings': 'Blessing',
    'ki-powers': 'Ki Power',
    'mercy': 'Mercy',
    'ranger-combat-styles': 'Combat Style',
    'bardic-masterpieces': 'Bardic Masterpiece',
    'wild-talents': 'Wild Talent',
    'kineticist-wild-talents': 'Wild Talent',
    'inquisitions': 'Inquisition',
    'mesmerist-tricks': 'Mesmerist Trick',
    'implement-schools': 'Implement School',
    'psychic-disciplines': 'Discipline',
    'witch-patrons': 'Patron',
}


def _detect_parent_class_from_url(url: str) -> str:
    """Detect parent class name from URL path."""
    parts = url.lower().split('/')
    for segment in parts:
        if segment in _CLASS_FROM_URL:
            return _CLASS_FROM_URL[segment]
    return ''


def _detect_category_from_url(url: str) -> str:
    """Detect feature category from URL path."""
    parts = url.lower().rstrip('/').split('/')
    for segment in parts:
        if segment in _CATEGORY_FROM_URL:
            return _CATEGORY_FROM_URL[segment]
    return ''


# ============================================================
# DISCOVERY: Find class feature URLs
# ============================================================

def discover_class_feature_urls() -> dict[str, list[str]]:
    """Crawl all class feature index pages to discover individual feature URLs.

    Returns:
        Dict mapping feature_key → list of discovered URLs.
    """
    discovered = {}

    for key, config in CLASS_FEATURE_INDEXES.items():
        feature_urls = set()

        for index_url in config['index_urls']:
            print(f"  [{config['parent_class']}] Crawling {config['feature_category']}...")

            html = fetch_page(index_url)
            if not html:
                print(f"    ✗ Failed to fetch {index_url}")
                continue

            soup = parse_html(html)
            content = (
                soup.select_one('article .article-content')
                or soup.select_one('div.article-content')
                or soup.select_one('article')
                or soup.find('body')
            )
            if not content:
                continue

            # Collect all links within the content
            from urllib.parse import urlparse as _urlparse
            index_path = _urlparse(index_url).path.rstrip('/')

            for a_tag in content.find_all('a', href=True):
                raw_url = normalize_url(a_tag['href'])

                if 'd20pfsrd.com' not in raw_url:
                    continue
                if not is_valid_content_url(raw_url):
                    continue
                if not is_paizo_content(raw_url):
                    continue

                # Must be a sub-page under the index (starts with index path)
                raw_path = _urlparse(raw_url).path.rstrip('/')
                if not raw_path.startswith(index_path + '/'):
                    continue  # Breadcrumb, cross-link, or self-link — skip

                feature_urls.add(raw_url)

        if feature_urls:
            discovered[key] = sorted(feature_urls)
            print(f"    Found {len(feature_urls)} {config['feature_category']} URLs")

    return discovered


# ============================================================
# BATCH PARSE (auto-detects type A vs B)
# ============================================================

def parse_class_feature_batch(
    urls: list[str],
    feature_key: str = '',
    progress_callback=None,
    limit: int | None = None,
) -> list[dict]:
    """Parse a batch of class feature URLs.

    Auto-detects whether to use Type A or Type B parser based on
    the feature_key config, falling back to URL-based detection.

    Args:
        urls: List of feature page URLs.
        feature_key: Key from CLASS_FEATURE_INDEXES (for type detection).
        progress_callback: Optional (current, total, name) callback.
        limit: Max URLs to parse.

    Returns:
        List of parsed feature dicts.
    """
    if limit:
        urls = urls[:limit]

    # Determine feature type and metadata from config
    config = CLASS_FEATURE_INDEXES.get(feature_key, {})
    feature_type = config.get('type', 'A')
    parent_class = config.get('parent_class', '')
    feature_category = config.get('feature_category', '')

    results = []
    total = len(urls)

    for i, url in enumerate(urls):
        if progress_callback:
            # Extract a short name for display
            short = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
            progress_callback(i + 1, total, short[:40])

        html = fetch_page(url)
        if not html:
            continue

        if feature_type == 'B':
            parsed = parse_feature_type_b(
                url, html=html,
                parent_class=parent_class,
                feature_category=feature_category,
            )
        else:
            parsed = parse_feature_type_a(
                url, html=html,
                parent_class=parent_class,
                feature_category=feature_category,
            )

        if parsed:
            results.append(parsed)

    return results


# ============================================================
# FULL DISCOVERY + PARSE PIPELINE
# ============================================================

def discover_and_parse_all(limit_per_category: int | None = None) -> dict:
    """Full pipeline: discover + parse all class features.

    Returns:
        Dict mapping feature_key → list of parsed feature dicts.
    """
    print("\n[Class Feature Discovery]")
    discovered = discover_class_feature_urls()

    all_results = {}

    for key, urls in discovered.items():
        config = CLASS_FEATURE_INDEXES[key]
        print(f"\n[{config['parent_class']} {config['feature_category']}s]"
              f" Parsing {len(urls)} pages...")

        if limit_per_category:
            urls = urls[:limit_per_category]

        results = parse_class_feature_batch(
            urls, feature_key=key, limit=limit_per_category,
        )

        all_results[key] = results
        print(f"  ✓ {len(results)}/{len(urls)} parsed")

    return all_results
