#!/usr/bin/env python3
"""
trait_parser.py — Parse Pathfinder 1e character traits from d20pfsrd.com.

Handles all trait categories:
  - Combat, Faith, Magic, Social (basic traits)
  - Race, Regional, Religion (restricted traits)
  - Equipment, Family, Mount, Campaign (other traits)

Each trait page follows a simple pattern:
  URL:  /traits/<category>-traits/<trait-name>/
  Body: Flavor text → "Benefit(s):" → mechanical effect
  Some include prerequisites or race/class requirements in the title.

Output schema per trait:
{
    "name": "Reactionary",
    "url": "https://...",
    "trait_type": "Combat",
    "benefit": "You gain a +2 trait bonus on initiative checks.",
    "description": "You were bullied often as a child...",
    "prerequisites": "Elf",          # race/class requirement if any
    "source": "Ultimate Campaign"
}
"""

import re
from pathlib import Path

from .base import (
    fetch_page, parse_html, extract_text, save_json,
    is_paizo_content, normalize_url,
)

# ============================================================
# TRAIT TYPE DETECTION
# ============================================================

# Map URL path segments to trait category names
TRAIT_TYPE_MAP = {
    'combat-traits': 'Combat',
    'faith-traits': 'Faith',
    'magic-traits': 'Magic',
    'social-traits': 'Social',
    'race-traits': 'Race',
    'regional-traits': 'Regional',
    'religion-traits': 'Religion',
    'equipment-traits': 'Equipment',
    'family-traits': 'Family',
    'mount-traits': 'Mount',
    'campaign-traits': 'Campaign',
}


def _detect_trait_type(url: str) -> str:
    """Detect trait category from URL path.

    Examples:
        /traits/combat-traits/reactionary/ → "Combat"
        /traits/race-traits/warrior-of-old/ → "Race"
    """
    for segment, trait_type in TRAIT_TYPE_MAP.items():
        if segment in url:
            return trait_type
    return "Unknown"


# ============================================================
# PREREQUISITE / RESTRICTION EXTRACTION
# ============================================================

# Pattern: trait name followed by race/class in parentheses
# e.g., "Warrior of Old (Elf)", "Defender of the Society (Fighter, Society)"
TITLE_RESTRICTION_PATTERN = re.compile(
    r'^(.+?)\s*\(([^)]+)\)\s*$'
)

# Patterns in body text for prerequisites
PREREQ_PATTERNS = [
    re.compile(r'Prerequisite\(?s?\)?[:\s]+(.+?)(?:\.|$)', re.IGNORECASE),
    re.compile(r'Requirements?[:\s]+(.+?)(?:\.|$)', re.IGNORECASE),
    re.compile(r'Restriction[:\s]+(.+?)(?:\.|$)', re.IGNORECASE),
]


def _extract_prerequisites(name: str, text: str) -> tuple[str, str]:
    """Extract prerequisites/restrictions from title and body.

    Returns:
        (clean_name, prerequisites_string)
    """
    prereqs = []
    clean_name = name

    # Check title for parenthetical restriction
    m = TITLE_RESTRICTION_PATTERN.match(name)
    if m:
        clean_name = m.group(1).strip()
        restriction = m.group(2).strip()
        # Filter out non-restriction parentheticals like "(Combat)" type labels
        lower = restriction.lower()
        if lower not in ('combat', 'faith', 'magic', 'social', 'campaign'):
            prereqs.append(restriction)

    # Check body text for prerequisite lines
    for pattern in PREREQ_PATTERNS:
        m = pattern.search(text)
        if m:
            prereq_text = m.group(1).strip().rstrip('.')
            if prereq_text and len(prereq_text) < 200:
                prereqs.append(prereq_text)
            break  # Take first match only

    return clean_name, '; '.join(prereqs) if prereqs else ''


# ============================================================
# BENEFIT EXTRACTION
# ============================================================

BENEFIT_PATTERNS = [
    # "Benefit:" or "Benefit(s):" or "Benefits:"
    re.compile(
        r'Benefits?\s*\(?s?\)?[:\s]+(.+)',
        re.IGNORECASE | re.DOTALL,
    ),
]


def _extract_benefit(text: str) -> str:
    """Extract the mechanical benefit text from the trait description."""
    for pattern in BENEFIT_PATTERNS:
        m = pattern.search(text)
        if m:
            benefit = m.group(1).strip()
            # Clean up: remove trailing source/copyright cruft
            # Stop at "Section 15" or "Source" or similar
            for cutoff in ['Section 15:', 'Source:', 'Source PZO',
                           'Pathfinder Roleplaying Game',
                           'Pathfinder Player Companion',
                           'Pathfinder Campaign Setting',
                           'Pathfinder Chronicles',
                           'Pathfinder Companion']:
                idx = benefit.find(cutoff)
                if idx > 0:
                    benefit = benefit[:idx].strip()

            return benefit.strip().rstrip('.')

    return ''


# ============================================================
# SOURCE EXTRACTION
# ============================================================

SOURCE_PATTERNS = [
    re.compile(r'Source\s+(?:PZO\S+\s+)?(.+?)(?:\.|©)', re.IGNORECASE),
    re.compile(
        r'(?:Pathfinder (?:Roleplaying Game|Player Companion|Campaign Setting|Chronicles|Companion))[:\s]*'
        r'([^.©]+)',
        re.IGNORECASE,
    ),
]


def _extract_source(text: str) -> str:
    """Extract the source book name."""
    for pattern in SOURCE_PATTERNS:
        m = pattern.search(text)
        if m:
            source = m.group(1).strip().rstrip('.')
            # Clean up copyright years and authors
            source = re.sub(r'\s*©.*$', '', source)
            source = re.sub(r'\s*Copyright.*$', '', source, flags=re.IGNORECASE)
            if len(source) < 100:
                return source

    return ''


# ============================================================
# MAIN PARSE FUNCTION
# ============================================================

def parse_trait_page(url: str, html: str | None = None) -> dict | None:
    """Parse a single trait page.

    Args:
        url: The trait page URL.
        html: Pre-fetched HTML (optional; fetches if None).

    Returns:
        Parsed trait dict or None if page is invalid/3pp.
    """
    if html is None:
        html = fetch_page(url)
    if not html:
        return None

    soup = parse_html(html)

    # Find main content area
    content = (
        soup.select_one('article .article-content')
        or soup.select_one('div.article-content')
        or soup.select_one('article')
    )
    if not content:
        return None

    # Extract trait name from h1
    h1 = content.select_one('h1') or soup.select_one('h1')
    if not h1:
        return None

    raw_name = extract_text(h1).strip()
    if not raw_name:
        return None

    # Get full text content
    full_text = extract_text(content)

    # Detect trait type from URL
    trait_type = _detect_trait_type(url)

    # Extract prerequisites from title parenthetical and body text
    clean_name, prerequisites = _extract_prerequisites(raw_name, full_text)

    # Extract benefit
    benefit = _extract_benefit(full_text)

    # Extract description (text before "Benefit")
    description = ''
    benefit_idx = re.search(r'Benefits?\s*\(?s?\)?:', full_text, re.IGNORECASE)
    if benefit_idx:
        desc_text = full_text[:benefit_idx.start()].strip()
        # Remove the trait name from the start if present
        if desc_text.lower().startswith(clean_name.lower()):
            desc_text = desc_text[len(clean_name):].strip()
        # Remove prerequisite lines from description
        for pattern in PREREQ_PATTERNS:
            desc_text = pattern.sub('', desc_text).strip()
        description = desc_text[:500]

    # Extract source
    source = _extract_source(full_text)

    # Skip 3pp content
    if not is_paizo_content(url):
        return None

    # Validate: must have a benefit to be a real trait
    if not benefit and not description:
        return None

    return {
        'name': clean_name,
        'url': url,
        'trait_type': trait_type,
        'prerequisites': prerequisites,
        'benefit': benefit,
        'description': description[:500],
        'source': source,
    }


# ============================================================
# BATCH PARSE
# ============================================================

def parse_trait_batch(
    urls: list[str],
    cache_dir: Path | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Parse a batch of trait URLs.

    Args:
        urls: List of trait page URLs.
        cache_dir: Directory containing cached HTML files.
        limit: Maximum number to parse.

    Returns:
        List of parsed trait dicts.
    """
    if limit:
        urls = urls[:limit]

    results = []
    for url in urls:
        # Try loading from cache
        html = None
        if cache_dir:
            from .base import url_to_cache_path
            cache_path = url_to_cache_path(url, cache_dir)
            if cache_path.exists():
                html = cache_path.read_text(encoding='utf-8', errors='replace')

        parsed = parse_trait_page(url, html=html)
        if parsed:
            results.append(parsed)

    return results
