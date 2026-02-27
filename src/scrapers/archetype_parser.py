#!/usr/bin/env python3
"""
archetype_parser.py — Parse d20pfsrd.com archetype pages into structured data.

Archetypes are the core customization layer for Pathfinder 1e classes.
Each archetype modifies its parent class by replacing or altering specific
class features. The key data this parser extracts:

  1. Archetype metadata (name, parent class, source)
  2. Features with full text descriptions
  3. Which base class features each archetype feature REPLACES or ALTERS
     — this is the critical data for the rules engine to compute
     character builds (e.g., "Mastermind replaces Swift Alchemy with
     Mastermind Defense at level 4")

Output schema per archetype:
{
    "name": "Mastermind",
    "parent_class": "Investigator",
    "parent_class_url": "https://...investigator",
    "url": "https://...mastermind/",
    "class_type": "hybrid",
    "description": "...",
    "source": "Advanced Class Guide",
    "features": [
        {
            "name": "Mastermind's Inspiration",
            "feature_type": "Ex",
            "level": 1,
            "description": "...",
            "replaces": [],
            "alters": ["Inspiration"]
        },
        ...
    ],
    "all_replaced_features": ["Swift Alchemy", "Investigator Talent (9th)"],
    "all_altered_features": ["Inspiration"]
}
"""

import re
from .base import (
    fetch_page, parse_html, get_article_content,
    extract_text, clean_text, is_paizo_content,
)


# ────────────────────────────────────────────────────────────────
# Parent class detection from URL
# ────────────────────────────────────────────────────────────────

# Map URL category → class_type (matches class_parser.py)
CLASS_TYPE_FROM_URL = {
    '/core-classes/': 'base',
    '/base-classes/': 'base',
    '/hybrid-classes/': 'hybrid',
    '/alternate-classes/': 'base',
    '/unchained-classes/': 'unchained',
    '/prestige-classes/': 'prestige',
    '/npc-classes/': 'npc',
    '/occult-classes/': 'occult',
}

# Regex patterns to extract parent class name from archetype URLs
# e.g. /classes/hybrid-classes/investigator/archetypes/.../mastermind/
PARENT_CLASS_PATTERNS = [
    # Standard: /classes/<category>/<class>/archetypes/...
    re.compile(
        r'/classes/(?:core-classes|base-classes|hybrid-classes|alternate-classes'
        r'|unchained-classes|prestige-classes|npc-classes)'
        r'/([^/]+)/archetypes?/',
        re.IGNORECASE,
    ),
    # Occult: /alternative-rule-systems/.../occult-classes/<class>/archetypes/...
    re.compile(
        r'/occult-classes/([^/]+)/archetypes?/',
        re.IGNORECASE,
    ),
]

# Slug → display name corrections for parent class
PARENT_CLASS_NAMES = {
    'barbarian': 'Barbarian', 'bard': 'Bard', 'cleric': 'Cleric',
    'druid': 'Druid', 'fighter': 'Fighter', 'monk': 'Monk',
    'paladin': 'Paladin', 'ranger': 'Ranger', 'rogue': 'Rogue',
    'sorcerer': 'Sorcerer', 'wizard': 'Wizard',
    'alchemist': 'Alchemist', 'cavalier': 'Cavalier',
    'inquisitor': 'Inquisitor', 'oracle': 'Oracle',
    'summoner': 'Summoner', 'witch': 'Witch',
    'gunslinger': 'Gunslinger', 'magus': 'Magus',
    'ninja': 'Ninja', 'samurai': 'Samurai',
    'arcanist': 'Arcanist', 'bloodrager': 'Bloodrager',
    'brawler': 'Brawler', 'hunter': 'Hunter',
    'investigator': 'Investigator', 'shaman': 'Shaman',
    'skald': 'Skald', 'slayer': 'Slayer',
    'swashbuckler': 'Swashbuckler', 'warpriest': 'Warpriest',
    'kineticist': 'Kineticist', 'medium': 'Medium',
    'mesmerist': 'Mesmerist', 'occultist': 'Occultist',
    'psychic': 'Psychic', 'spiritualist': 'Spiritualist',
    'vigilante': 'Vigilante', 'shifter': 'Shifter',
    'antipaladin': 'Antipaladin',
    'unchained-barbarian': 'Unchained Barbarian',
    'unchained-monk': 'Unchained Monk',
    'unchained-rogue': 'Unchained Rogue',
    'unchained-summoner': 'Unchained Summoner',
}


def detect_parent_class(url: str) -> tuple[str, str, str]:
    """Extract parent class name, URL, and class_type from archetype URL.

    Returns:
        (parent_class_name, parent_class_url, class_type)
    """
    url_lower = url.lower()

    # Detect class_type from URL path
    class_type = 'base'
    for path_frag, ctype in CLASS_TYPE_FROM_URL.items():
        if path_frag in url_lower:
            class_type = ctype
            break

    # Extract parent class slug
    for pattern in PARENT_CLASS_PATTERNS:
        m = pattern.search(url)
        if m:
            slug = m.group(1).lower().rstrip('/')
            display_name = PARENT_CLASS_NAMES.get(
                slug, slug.replace('-', ' ').title()
            )

            # Reconstruct parent class URL (everything before /archetypes/)
            arch_idx = url_lower.find('/archetypes')
            parent_url = url[:arch_idx] if arch_idx > 0 else ''

            return display_name, parent_url, class_type

    return '', '', class_type


# ────────────────────────────────────────────────────────────────
# Replaces / Alters extraction
# ────────────────────────────────────────────────────────────────

# Patterns for "This ability/feature replaces X" and "This ability/feature alters X"
# These appear at the end of feature descriptions and are THE critical data
# for the rules engine.
#
# Examples from real pages:
#   "This ability replaces swift alchemy."
#   "This ability replaces weapon training 1 and 3, and armor mastery."
#   "This ability alters inspiration."
#   "This replaces the bonus feat gained at 1st level, and the weapon training class feature."
#   "This ability replaces the investigator talent gained at 9th level."
#   "This replaces bravery."
#   "This ability replaces poison lore and poison resistance."
#   "This alters the fighter's normal proficiencies."

REPLACES_PATTERN = re.compile(
    r'(?:This|It)\s+(?:ability|class feature|feature)?\s*replaces?\s+'
    r'(.+?)'
    r'(?:\s*(?:,\s*)?(?:and\s+)?(?:it\s+)?alters?\s|\.\s*|$)',
    re.IGNORECASE,
)

# Alters pattern must STOP before "and replaces" / ", replaces" / "it replaces"
# to avoid swallowing combined sentences like "alters burn and replaces internal buffer"
ALTERS_PATTERN = re.compile(
    r'(?:This|It)\s+(?:ability|class feature|feature)?\s*alters?\s+'
    r'(.+?)'
    r'(?:\s*(?:,\s*)?(?:and\s+)?(?:it\s+)?replaces?\s|\.\s*|$)',
    re.IGNORECASE,
)

# Secondary patterns: extract the other verb from combined sentences
# "alters X and replaces Y" → captures Y
COMBINED_REPLACES_PATTERN = re.compile(
    r'(?:and|,)\s*(?:it\s+)?replaces?\s+(.+?)(?:\.|$)',
    re.IGNORECASE,
)
# "replaces X, and alters Y" → captures Y
COMBINED_ALTERS_PATTERN = re.compile(
    r'(?:and|,)\s*(?:it\s+)?alters?\s+(.+?)(?:\.|$)',
    re.IGNORECASE,
)


def extract_replacement_info(text: str) -> tuple[list[str], list[str]]:
    """Extract which base class features are replaced or altered.

    Handles combined sentences like:
      "This ability alters burn and replaces internal buffer."
      "This ability alters kinetic blast and infusions, and replaces metakinesis."
      "This ability replaces basic hydrokinesis, and alters elemental focus."

    Args:
        text: Full description text of an archetype feature.

    Returns:
        (replaces_list, alters_list) — lists of base class feature names.
    """
    replaces = []
    alters = []

    # Search all standalone "This/It replaces" mentions
    for m in REPLACES_PATTERN.finditer(text):
        features = _split_feature_list(m.group(1))
        replaces.extend(features)

    # Search all standalone "This/It alters" mentions
    for m in ALTERS_PATTERN.finditer(text):
        features = _split_feature_list(m.group(1))
        alters.extend(features)

    # Search for "replaces" in combined sentences ("alters X and replaces Y")
    for m in COMBINED_REPLACES_PATTERN.finditer(text):
        features = _split_feature_list(m.group(1))
        replaces.extend(features)

    # Search for "alters" in combined sentences ("replaces X, and alters Y")
    for m in COMBINED_ALTERS_PATTERN.finditer(text):
        features = _split_feature_list(m.group(1))
        alters.extend(features)

    # Deduplicate while preserving order
    replaces = _dedup_preserve_order(replaces)
    alters = _dedup_preserve_order(alters)

    return replaces, alters


def _split_feature_list(raw: str) -> list[str]:
    """Split a comma/and-separated list of feature names.

    Handles patterns like:
      "swift alchemy"
      "weapon training 1 and 3, and armor mastery"
      "the bonus feat gained at 1st level, and the weapon training class feature"
      "the investigator talent gained at 9th level"
      "poison lore and poison resistance"
      "bravery"
    """
    # Clean up
    raw = raw.strip()
    raw = re.sub(r'\s+', ' ', raw)

    # Remove trailing punctuation
    raw = raw.rstrip('.,;:')

    # Remove leading "the"
    raw = re.sub(r'^the\s+', '', raw, flags=re.IGNORECASE)

    # Split on ", and " / " and " / ", " but be careful about numbered series
    # like "weapon training 1 and 3" — these should NOT split
    # Strategy: split on comma first, then split each part on " and "
    # unless it looks like a number range (e.g., "1 and 3")

    parts = _smart_split(raw)

    results = []
    for part in parts:
        cleaned = _clean_feature_name(part)
        if cleaned and len(cleaned) > 1:
            results.append(cleaned)

    return results


def _smart_split(text: str) -> list[str]:
    """Split feature list intelligently on commas and 'and'.

    Preserves numbered/ordinal series like:
      "weapon training 1 and 3" as one unit
      "2nd and 6th level utility wild talents" as one unit
      "5th-, 9th-, and 13th-level infusions" as one unit
    """
    # First split on commas
    comma_parts = [p.strip() for p in text.split(',')]

    results = []
    for part in comma_parts:
        part = part.strip()
        if not part:
            continue

        # Remove leading "and "
        part = re.sub(r'^and\s+', '', part, flags=re.IGNORECASE)

        # Check for " and " in this part
        if ' and ' in part.lower():
            # Split on " and "
            and_parts = re.split(r'\s+and\s+', part, flags=re.IGNORECASE)

            # If the last part(s) after "and" are just numbers or ordinals,
            # this is a numbered series — keep it as one feature
            # e.g., "weapon training 1 and 3", "2nd and 6th level utility wild talents"
            if len(and_parts) >= 2:
                last = and_parts[-1].strip()
                first = and_parts[0].strip()
                # Check if EITHER side is a bare number/ordinal (numbered range)
                is_num = lambda s: bool(re.match(r'^\d+(?:st|nd|rd|th)?(?:-)?$', s.strip()))
                if is_num(last) or is_num(first):
                    results.append(part)
                else:
                    results.extend(and_parts)
            else:
                results.extend(and_parts)
        else:
            results.append(part)

    return [p.strip() for p in results if p.strip()]


def _clean_feature_name(raw: str) -> str:
    """Clean up a single feature name.

    Removes common cruft like:
      "the ... class feature"
      "gained at Nth level"
      Leading/trailing articles and possessives
      Kineticist-style verbose descriptions
    """
    text = raw.strip()

    # Remove leading "the"
    text = re.sub(r'^the\s+', '', text, flags=re.IGNORECASE)

    # Remove "class feature(s)" suffix
    text = re.sub(r'\s+class\s+features?$', '', text, flags=re.IGNORECASE)

    # Remove "gained at Nth level"
    text = re.sub(
        r'\s+gained\s+(?:at\s+)?\d+(?:st|nd|rd|th)\s+level',
        '', text, flags=re.IGNORECASE,
    )

    # Remove "at Nth level" suffix
    text = re.sub(
        r'\s+at\s+\d+(?:st|nd|rd|th)\s+level$',
        '', text, flags=re.IGNORECASE,
    )

    # Remove "ability" suffix if it's just cruft
    text = re.sub(r'\s+ability$', '', text, flags=re.IGNORECASE)

    # Remove class possessives: "the fighter's ...", "investigator's ..."
    text = re.sub(
        r"^(?:fighter|investigator|barbarian|rogue|monk|paladin|ranger|"
        r"cleric|druid|wizard|sorcerer|bard|alchemist|cavalier|gunslinger|"
        r"inquisitor|magus|oracle|summoner|witch|arcanist|bloodrager|"
        r"brawler|hunter|shaman|skald|slayer|swashbuckler|warpriest|"
        r"kineticist|medium|mesmerist|occultist|psychic|spiritualist|"
        r"vigilante|shifter|ninja|samurai|antipaladin)'s\s+",
        '', text, flags=re.IGNORECASE,
    )

    # Remove leading possessive pronouns: "her", "his", "its"
    text = re.sub(r'^(?:her|his|its|their)\s+', '', text, flags=re.IGNORECASE)

    # Remove "normal " prefix
    text = re.sub(r'^normal\s+', '', text, flags=re.IGNORECASE)

    # Kineticist-specific: trim verbose phrases after feature name
    # e.g., "basic hydrokinesis as her basic utility talent" → "basic hydrokinesis"
    text = re.sub(
        r'\s+as\s+(?:her|his|its|their|the)\s+.+$',
        '', text, flags=re.IGNORECASE,
    )

    # "X normally granted by selecting an element" → "X"
    text = re.sub(
        r'\s+normally\s+granted\s+by\s+.+$',
        '', text, flags=re.IGNORECASE,
    )

    # "X granted by the Y element" → "X"
    text = re.sub(
        r'\s+granted\s+by\s+.+$',
        '', text, flags=re.IGNORECASE,
    )

    # "X from elemental defense" → "X" (unless it's the whole name)
    text = re.sub(
        r'\s+from\s+elemental\s+\w+$',
        '', text, flags=re.IGNORECASE,
    )

    # "but the X can still..." → remove trailing but-clause
    text = re.sub(
        r'\s+but\s+.+$',
        '', text, flags=re.IGNORECASE,
    )

    # Title-case for consistency
    text = text.strip()
    if text:
        if text == text.lower():
            text = _title_case_feature(text)

    return text


def _title_case_feature(text: str) -> str:
    """Title-case a feature name, preserving special patterns."""
    # Don't capitalize small words unless they're first
    small_words = {'a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'for', 'at', 'per'}
    words = text.split()
    result = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in small_words:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return ' '.join(result)


def _dedup_preserve_order(items: list[str]) -> list[str]:
    """Deduplicate list while preserving order."""
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ────────────────────────────────────────────────────────────────
# Feature parsing
# ────────────────────────────────────────────────────────────────

# Feature type tags: (Ex), (Su), (Sp)
FEATURE_TYPE_RE = re.compile(r'\((Ex|Su|Sp)\)', re.IGNORECASE)


def parse_archetype_features(content) -> list[dict]:
    """Extract archetype features from the page content.

    Archetype features are under h3/h4 headings. Each has:
      - Name (possibly with (Ex)/(Su)/(Sp) tag)
      - Description text
      - "replaces" / "alters" info at the end
      - Level (sometimes mentioned in text)
    """
    features = []

    for heading in content.find_all(['h3', 'h4']):
        raw_name = clean_text(extract_text(heading))
        if not raw_name or len(raw_name) > 100:
            continue

        # Skip non-feature headings
        skip_words = [
            'table of contents', 'contents', 'subpages', 'discuss',
            'archetypes', 'alternate class', 'favored class',
            'section 15', 'copyright', 'paizo',
        ]
        if any(s in raw_name.lower() for s in skip_words):
            continue

        # Extract feature type (Ex/Su/Sp)
        feature_type = ''
        type_match = FEATURE_TYPE_RE.search(raw_name)
        if type_match:
            feature_type = type_match.group(1).capitalize()
            # Remove the tag from the name
            clean_name = FEATURE_TYPE_RE.sub('', raw_name).strip()
        else:
            clean_name = raw_name

        # Strip trailing punctuation / cruft
        clean_name = clean_name.strip(' :–—-')

        # Get description: all text until next heading
        desc_parts = []
        sib = heading.next_sibling
        while sib:
            if hasattr(sib, 'name') and sib.name in ('h2', 'h3', 'h4'):
                break
            text = extract_text(sib) if hasattr(sib, 'name') else str(sib).strip()
            if text:
                desc_parts.append(text)
            sib = sib.next_sibling

        description = clean_text(' '.join(desc_parts))

        if not clean_name:
            continue

        # Extract level from description
        level = _extract_level(clean_name, description)

        # Extract replaces/alters — THE critical info
        replaces, alters = extract_replacement_info(description)

        # Truncate description for storage (keep full text but cap it)
        description = description[:3000]

        features.append({
            "name": clean_name,
            "feature_type": feature_type,  # "Ex", "Su", "Sp", or ""
            "level": level,
            "description": description,
            "replaces": replaces,
            "alters": alters,
        })

    return features


def _extract_level(name: str, description: str) -> int | None:
    """Extract the level a feature is gained, if mentioned.

    Returns None if no level is mentioned (assumed level 1).
    """
    # Check for "At Nth level" at the start of description
    m = re.match(r'At (\d+)(?:st|nd|rd|th) level', description, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Check name for level: "Improved X (11th)"
    m = re.search(r'\((\d+)(?:st|nd|rd|th)\)', name)
    if m:
        return int(m.group(1))

    return None


# ────────────────────────────────────────────────────────────────
# Main archetype page parser
# ────────────────────────────────────────────────────────────────

def parse_archetype_page(url: str, html: str = None) -> dict | None:
    """Parse a single archetype page into structured data.

    Returns a dict with archetype metadata, features, and replacement info,
    or None if the page doesn't look like an archetype.
    """
    if html is None:
        html = fetch_page(url)
    if not html:
        return None

    soup = parse_html(html)
    content = get_article_content(soup)
    if not content:
        return None

    # Get archetype name from h1
    h1 = content.find('h1') or soup.find('h1')
    if not h1:
        return None

    name = clean_text(extract_text(h1))
    if not name:
        return None

    # Skip if this looks like an index page rather than a specific archetype
    name_lower = name.lower()
    if name_lower in ('archetypes', 'archetype', 'alternate class features'):
        return None
    if name_lower.endswith(' archetypes'):
        return None

    # Detect parent class from URL
    parent_class, parent_class_url, class_type = detect_parent_class(url)

    # Also try to detect parent from breadcrumb or page text
    if not parent_class:
        parent_class, parent_class_url = _detect_parent_from_breadcrumb(soup, url)

    # Skip 3rd party content
    if not is_paizo_content(url):
        return None

    # Extract description (italic intro paragraph, common on archetype pages)
    description = _extract_archetype_description(content, h1)

    # Extract source book
    source = _extract_source(content)

    # Parse features — the meat of it
    features = parse_archetype_features(content)

    # Validate: a real archetype page should have at least one feature
    # with a replaces or alters entry
    has_modification = any(
        f['replaces'] or f['alters'] for f in features
    )
    if not features:
        return None

    # Aggregate all replaced/altered features for quick lookup
    all_replaced = []
    all_altered = []
    for f in features:
        all_replaced.extend(f['replaces'])
        all_altered.extend(f['alters'])
    all_replaced = _dedup_preserve_order(all_replaced)
    all_altered = _dedup_preserve_order(all_altered)

    return {
        "name": name,
        "parent_class": parent_class,
        "parent_class_url": parent_class_url,
        "url": url,
        "class_type": class_type,
        "description": description[:1000],
        "source": source,
        "features": features,
        "all_replaced_features": all_replaced,
        "all_altered_features": all_altered,
        "has_modification_data": has_modification,
    }


def _detect_parent_from_breadcrumb(soup, url: str) -> tuple[str, str]:
    """Fallback: detect parent class from breadcrumb or page text."""
    # Look for breadcrumb links
    breadcrumb = soup.select_one('.breadcrumb') or soup.select_one('nav[aria-label="breadcrumb"]')
    if breadcrumb:
        links = breadcrumb.find_all('a')
        for link in links:
            text = extract_text(link).lower()
            if text in PARENT_CLASS_NAMES:
                href = link.get('href', '')
                return PARENT_CLASS_NAMES[text], href

    # Look for text pattern "Home > Classes > ... > ClassName >"
    # d20pfsrd uses a breadcrumb-like path at the top
    for text_node in soup.find_all(string=re.compile(r'Home\s*>')):
        text = str(text_node)
        for slug, display in PARENT_CLASS_NAMES.items():
            if f'>{display}<' in str(text_node.parent) or f'> {display} <' in str(text_node.parent):
                return display, ''

    return '', ''


def _extract_archetype_description(content, h1) -> str:
    """Extract the intro/flavor text of an archetype.

    Typically the first paragraph after h1, often in italics.
    """
    desc_parts = []
    sib = h1.next_sibling

    while sib:
        if hasattr(sib, 'name'):
            # Stop at structural elements
            if sib.name in ('h2', 'h3', 'h4', 'table'):
                break

            text = extract_text(sib)
            if text and len(text) > 10:
                desc_parts.append(text)

        # Stop after ~500 chars of description
        if sum(len(p) for p in desc_parts) > 500:
            break

        sib = sib.next_sibling

    return clean_text(' '.join(desc_parts))


def _extract_source(content) -> str:
    """Extract source book name from the page.

    d20pfsrd pages often have a section at the bottom with the source.
    Common patterns:
      "Source PPC:ACG" or "Advanced Class Guide"
    """
    full_text = extract_text(content)

    # Look for copyright line at the bottom
    copyright_match = re.search(
        r'(?:Pathfinder Roleplaying Game[:\s]*)?'
        r'(Advanced (?:Class|Player\'s|Race) Guide|'
        r'Ultimate (?:Combat|Magic|Wilderness|Intrigue)|'
        r'Occult Adventures|'
        r'Advanced Player\'s Guide|'
        r'(?:Pathfinder )?Player Companion[:\s]+[^.]+|'
        r'Pathfinder Campaign Setting[:\s]+[^.]+)',
        full_text,
        re.IGNORECASE,
    )
    if copyright_match:
        return clean_text(copyright_match.group(1))

    # Look for "Source" label
    source_match = re.search(
        r'Source[:\s]+([^.]+)',
        full_text,
        re.IGNORECASE,
    )
    if source_match:
        source = clean_text(source_match.group(1))
        if len(source) < 100:
            return source

    return ''


# ────────────────────────────────────────────────────────────────
# Batch processing
# ────────────────────────────────────────────────────────────────

def parse_archetype_batch(urls: list[str], progress_callback=None) -> list[dict]:
    """Parse multiple archetype pages.

    Args:
        urls: List of archetype page URLs from the manifest.
        progress_callback: Optional callback(current, total, name) for progress.

    Returns:
        List of parsed archetype dicts.
    """
    results = []
    total = len(urls)

    for i, url in enumerate(urls):
        try:
            arch = parse_archetype_page(url)
            if arch:
                results.append(arch)
                if progress_callback:
                    progress_callback(i + 1, total, arch["name"])
            else:
                if progress_callback:
                    progress_callback(i + 1, total, f"SKIP: {url[-50:]}")
        except Exception as e:
            print(f"    ⚠ Error parsing {url}: {e}")
            if progress_callback:
                progress_callback(i + 1, total, f"ERROR: {url[-50:]}")

    return results
