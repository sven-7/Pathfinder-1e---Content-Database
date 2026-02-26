#!/usr/bin/env python3
"""
class_parser.py — Parse d20pfsrd.com class pages into structured data.

Class pages are the most complex content type. A full class page includes:
  - Class description and flavor
  - Role description
  - Hit Die, BAB, saves, skill ranks per level
  - Class skills list
  - Class features (gained at specific levels)
  - Spells per day table (for casters)
  - Progression table (level / BAB / Fort / Ref / Will / Special)

The parser also detects class_type (base, hybrid, prestige, etc.) from URL.
"""

import re
from .base import (
    fetch_page, parse_html, get_article_content,
    extract_text, clean_text,
)


# Class type detection from URL
CLASS_TYPE_MAP = {
    '/core-classes/': 'base',
    '/base-classes/': 'base',
    '/hybrid-classes/': 'hybrid',
    '/alternate-classes/': 'base',
    '/unchained-classes/': 'unchained',
    '/prestige-classes/': 'prestige',
    '/npc-classes/': 'npc',
    '/occult-classes/': 'occult',
}

# Known class metadata (for validation / filling gaps the parser might miss)
KNOWN_CLASSES = {
    # Core (CRB)
    'barbarian': {'hit_die': 'd12', 'bab': 'full', 'fort': 'good', 'ref': 'poor', 'will': 'poor', 'skills_per_level': 4},
    'bard': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'good', 'will': 'good', 'skills_per_level': 6, 'casting': 'arcane', 'style': 'spontaneous', 'max_spell': 6},
    'cleric': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'divine', 'style': 'prepared', 'max_spell': 9},
    'druid': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 4, 'casting': 'divine', 'style': 'prepared', 'max_spell': 9},
    'fighter': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'poor', 'will': 'poor', 'skills_per_level': 2},
    'monk': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'good', 'will': 'good', 'skills_per_level': 4},
    'paladin': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'divine', 'style': 'prepared', 'max_spell': 4},
    'ranger': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'good', 'will': 'poor', 'skills_per_level': 6, 'casting': 'divine', 'style': 'prepared', 'max_spell': 4},
    'rogue': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'good', 'will': 'poor', 'skills_per_level': 8},
    'sorcerer': {'hit_die': 'd6', 'bab': 'half', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'arcane', 'style': 'spontaneous', 'max_spell': 9},
    'wizard': {'hit_die': 'd6', 'bab': 'half', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'arcane', 'style': 'prepared', 'max_spell': 9},
    # Hybrid (ACG)
    'arcanist': {'hit_die': 'd6', 'bab': 'half', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'arcane', 'style': 'prepared', 'max_spell': 9},
    'bloodrager': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'poor', 'will': 'poor', 'skills_per_level': 4, 'casting': 'arcane', 'style': 'spontaneous', 'max_spell': 4},
    'brawler': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'good', 'will': 'poor', 'skills_per_level': 4},
    'hunter': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'good', 'will': 'poor', 'skills_per_level': 6, 'casting': 'divine', 'style': 'spontaneous', 'max_spell': 6},
    'investigator': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'good', 'will': 'good', 'skills_per_level': 6, 'casting': 'alchemical', 'style': 'prepared', 'max_spell': 6},
    'shaman': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 4, 'casting': 'divine', 'style': 'prepared', 'max_spell': 9},
    'skald': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 4, 'casting': 'arcane', 'style': 'spontaneous', 'max_spell': 6},
    'slayer': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'good', 'will': 'poor', 'skills_per_level': 6},
    'swashbuckler': {'hit_die': 'd10', 'bab': 'full', 'fort': 'poor', 'ref': 'good', 'will': 'poor', 'skills_per_level': 4},
    'warpriest': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'divine', 'style': 'prepared', 'max_spell': 6},
    # Occult (OA)
    'kineticist': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'good', 'will': 'poor', 'skills_per_level': 4},
    'medium': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 4, 'casting': 'psychic', 'style': 'spontaneous', 'max_spell': 4},
    'mesmerist': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'good', 'will': 'good', 'skills_per_level': 6, 'casting': 'psychic', 'style': 'spontaneous', 'max_spell': 6},
    'occultist': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 4, 'casting': 'psychic', 'style': 'spontaneous', 'max_spell': 6},
    'psychic': {'hit_die': 'd6', 'bab': 'half', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'psychic', 'style': 'spontaneous', 'max_spell': 9},
    'spiritualist': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 4, 'casting': 'psychic', 'style': 'spontaneous', 'max_spell': 6},
    # APG base classes
    'alchemist': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'good', 'will': 'poor', 'skills_per_level': 4, 'casting': 'alchemical', 'style': 'prepared', 'max_spell': 6},
    'cavalier': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'poor', 'will': 'poor', 'skills_per_level': 4},
    'inquisitor': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 6, 'casting': 'divine', 'style': 'spontaneous', 'max_spell': 6},
    'oracle': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 4, 'casting': 'divine', 'style': 'spontaneous', 'max_spell': 9},
    'summoner': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'arcane', 'style': 'spontaneous', 'max_spell': 6},
    'witch': {'hit_die': 'd6', 'bab': 'half', 'fort': 'poor', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'arcane', 'style': 'prepared', 'max_spell': 9},
    # UM/UC
    'gunslinger': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'good', 'will': 'poor', 'skills_per_level': 4},
    'magus': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'good', 'ref': 'poor', 'will': 'good', 'skills_per_level': 2, 'casting': 'arcane', 'style': 'prepared', 'max_spell': 6},
    'ninja': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'good', 'will': 'poor', 'skills_per_level': 8},
    'samurai': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'poor', 'will': 'poor', 'skills_per_level': 4},
    # UI
    'vigilante': {'hit_die': 'd8', 'bab': 'three_quarter', 'fort': 'poor', 'ref': 'good', 'will': 'good', 'skills_per_level': 6},
    # UW
    'shifter': {'hit_die': 'd10', 'bab': 'full', 'fort': 'good', 'ref': 'good', 'will': 'poor', 'skills_per_level': 4},
}


def detect_class_type(url: str) -> str:
    """Detect class type from URL path."""
    for path_fragment, class_type in CLASS_TYPE_MAP.items():
        if path_fragment in url:
            return class_type
    return 'base'


def parse_class_page(url: str, html: str = None) -> dict | None:
    """Parse a single class page into structured data.

    Returns a dict with all class metadata, features, progression, etc.
    """
    if html is None:
        html = fetch_page(url)
    if not html:
        return None

    soup = parse_html(html)
    content = get_article_content(soup)
    if not content:
        return None

    h1 = content.find('h1') or soup.find('h1')
    if not h1:
        return None

    name = clean_text(extract_text(h1))
    if not name:
        return None

    name_lower = name.lower()
    class_type = detect_class_type(url)

    # Start with known metadata if available
    known = KNOWN_CLASSES.get(name_lower, {})

    cls = {
        "name": name,
        "url": url,
        "class_type": class_type,
        "hit_die": known.get('hit_die', ''),
        "skill_ranks_per_level": known.get('skills_per_level'),
        "bab_progression": known.get('bab', ''),
        "fort_progression": known.get('fort', ''),
        "ref_progression": known.get('ref', ''),
        "will_progression": known.get('will', ''),
        "spellcasting_type": known.get('casting'),
        "spellcasting_style": known.get('style'),
        "max_spell_level": known.get('max_spell'),
        "alignment_restriction": "",
        "description": "",
        "class_skills": [],
        "class_features": [],
        "progression": [],
        "source": "",
    }

    full_text = extract_text(content)

    # Parse hit die from page text
    hd_match = re.search(r'Hit (?:Die|Dice)[:\s]*(d\d+)', full_text, re.IGNORECASE)
    if hd_match:
        cls["hit_die"] = hd_match.group(1)

    # Parse skill ranks
    skills_match = re.search(r'Skill Ranks? (?:per|each) Level[:\s]*(\d+)', full_text, re.IGNORECASE)
    if skills_match:
        cls["skill_ranks_per_level"] = int(skills_match.group(1))

    # Parse alignment
    align_match = re.search(r'Alignment[:\s]*([^\n.]+)', full_text, re.IGNORECASE)
    if align_match:
        cls["alignment_restriction"] = clean_text(align_match.group(1))

    # Parse class skills
    cls["class_skills"] = parse_class_skills(full_text)

    # Parse description (first substantial paragraph)
    cls["description"] = extract_class_description(content)

    # Parse class features from page
    cls["class_features"] = parse_class_features(content)

    # Parse progression table if present
    cls["progression"] = parse_progression_table(content)

    return cls


def parse_class_skills(text: str) -> list[str]:
    """Extract class skill names from text.

    Looks for patterns like:
    "Class Skills: Acrobatics (Dex), Bluff (Cha), Climb (Str), ..."
    """
    match = re.search(
        r'Class Skills?\s*(?:are\s*)?[:\s]*(.+?)(?:\.|Skill Ranks|Hit Die|$)',
        text, re.IGNORECASE | re.DOTALL
    )
    if not match:
        return []

    skills_text = match.group(1)
    # Extract skill names (word before parenthesized ability)
    skills = re.findall(r'([\w\s]+?)\s*\(\w+\)', skills_text)
    return [clean_text(s) for s in skills if s.strip()]


def extract_class_description(content) -> str:
    """Extract the class description/flavor text."""
    h1 = content.find('h1')
    if not h1:
        return ""

    desc_parts = []
    sibling = h1.next_sibling

    # Collect text until we hit a structural element
    while sibling:
        if hasattr(sibling, 'name') and sibling.name in ('table', 'h2', 'h3'):
            break

        text = extract_text(sibling) if hasattr(sibling, 'name') else str(sibling).strip()
        if text and len(text) > 20:
            desc_parts.append(text)

        # Stop after ~500 chars of description
        if sum(len(p) for p in desc_parts) > 500:
            break

        sibling = sibling.next_sibling

    return clean_text(' '.join(desc_parts))[:1000]


def parse_class_features(content) -> list[dict]:
    """Extract class features from the page.

    Features are typically under h3/h4 headings within the class page,
    with their gained level mentioned in text.
    """
    features = []

    # Look for feature headings (h2, h3, h4 with feature-like names)
    for heading in content.find_all(['h2', 'h3', 'h4']):
        name = clean_text(extract_text(heading))
        if not name or len(name) > 80:
            continue

        # Skip non-feature headings
        skip = ['class skills', 'table', 'spells per day', 'spell list',
                'starting wealth', 'favored class', 'ex-', 'subpages',
                'discuss', 'archetypes']
        if any(s in name.lower() for s in skip):
            continue

        # Extract level from heading or following text
        level = 1  # default
        level_match = re.search(r'\((\d+)(?:st|nd|rd|th)\)', name)
        if level_match:
            level = int(level_match.group(1))
        else:
            # Check text following the heading
            sibling = heading.next_sibling
            if sibling:
                sibling_text = extract_text(sibling) if hasattr(sibling, 'name') else str(sibling)
                lvl_match = re.search(r'At (\d+)(?:st|nd|rd|th) level', sibling_text[:200])
                if lvl_match:
                    level = int(lvl_match.group(1))

        # Get description (text after heading until next heading)
        desc_parts = []
        sib = heading.next_sibling
        while sib:
            if hasattr(sib, 'name') and sib.name in ('h2', 'h3', 'h4'):
                break
            text = extract_text(sib) if hasattr(sib, 'name') else str(sib).strip()
            if text:
                desc_parts.append(text)
            sib = sib.next_sibling

        description = clean_text(' '.join(desc_parts))[:2000]

        if name and description:
            # Determine feature type
            feature_type = 'class_feature'
            name_lower = name.lower()
            if 'ex ' in name_lower or '(ex)' in name_lower:
                feature_type = 'extraordinary'
            elif 'su ' in name_lower or '(su)' in name_lower:
                feature_type = 'supernatural'
            elif 'sp ' in name_lower or '(sp)' in name_lower:
                feature_type = 'spell_like'

            features.append({
                "name": re.sub(r'\s*\((Ex|Su|Sp)\)\s*', '', name).strip(),
                "level": level,
                "feature_type": feature_type,
                "description": description,
            })

    return features


def parse_progression_table(content) -> list[dict]:
    """Parse the class progression table (Level / BAB / Fort / Ref / Will / Special).

    Returns list of dicts with level, bab, fort, ref, will, special.
    """
    tables = content.find_all('table')
    progression = []

    for table in tables:
        # Check if this looks like a progression table
        headers = [clean_text(extract_text(th)).lower() for th in table.find_all('th')]
        if not any('level' in h for h in headers):
            continue
        if not any('base attack' in h or 'bab' in h for h in headers):
            continue

        # This is likely a progression table
        rows = table.find_all('tr')
        for row in rows:
            cells = [clean_text(extract_text(td)) for td in row.find_all(['td', 'th'])]
            if len(cells) < 5:
                continue

            # First cell should be level number
            try:
                level = int(re.search(r'\d+', cells[0]).group())
            except (AttributeError, ValueError):
                continue

            if level < 1 or level > 20:
                continue

            # Parse BAB (may be like "+1" or "+6/+1")
            bab_text = cells[1] if len(cells) > 1 else ''
            bab_match = re.search(r'\+?(\d+)', bab_text)
            bab = int(bab_match.group(1)) if bab_match else 0

            # Parse saves
            def parse_save(text):
                m = re.search(r'\+?(\d+)', text)
                return int(m.group(1)) if m else 0

            fort = parse_save(cells[2]) if len(cells) > 2 else 0
            ref = parse_save(cells[3]) if len(cells) > 3 else 0
            will = parse_save(cells[4]) if len(cells) > 4 else 0

            # Special column (may be index 5 or last)
            special = cells[5] if len(cells) > 5 else ''

            progression.append({
                "level": level,
                "bab": bab,
                "fort_save": fort,
                "ref_save": ref,
                "will_save": will,
                "special": special,
            })

        if progression:
            break  # Use first matching table

    return progression


def parse_class_batch(urls: list[str], progress_callback=None) -> list[dict]:
    """Parse multiple class pages."""
    results = []
    total = len(urls)

    for i, url in enumerate(urls):
        try:
            cls = parse_class_page(url)
            if cls:
                results.append(cls)
                if progress_callback:
                    progress_callback(i + 1, total, cls["name"])
            else:
                if progress_callback:
                    progress_callback(i + 1, total, f"SKIP: {url}")
        except Exception as e:
            print(f"    ⚠ Error parsing {url}: {e}")

    return results
