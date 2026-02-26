#!/usr/bin/env python3
"""
race_parser.py — Parse d20pfsrd.com race pages into structured data.

Race pages typically include:
  - Name, type, size
  - Ability score modifiers
  - Base speed
  - Languages
  - Standard and alternate racial traits
  - Favored class options
"""

import re
from .base import (
    fetch_page, parse_html, get_article_content,
    extract_text, clean_text,
)


# Size detection
SIZE_KEYWORDS = ['Fine', 'Diminutive', 'Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan', 'Colossal']


def parse_race_page(url: str, html: str = None) -> dict | None:
    """Parse a single race page into structured data."""
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

    full_text = extract_text(content)

    race = {
        "name": name,
        "url": url,
        "race_type": "other",
        "size": "Medium",
        "base_speed": 30,
        "ability_modifiers": "",
        "type": "Humanoid",
        "subtypes": "",
        "languages": "",
        "bonus_languages": "",
        "description": "",
        "racial_traits": [],
        "source": "",
    }

    # Core races
    core_races = {'dwarf', 'elf', 'gnome', 'half-elf', 'half-orc', 'halfling', 'human'}
    if name.lower() in core_races:
        race["race_type"] = "core"

    # Parse size
    for size in SIZE_KEYWORDS:
        if re.search(rf'\b{size}\b', full_text):
            race["size"] = size
            break

    # Parse speed
    speed_match = re.search(r'(?:base|land)\s*speed[:\s]*(\d+)\s*(?:ft|feet)', full_text, re.IGNORECASE)
    if speed_match:
        race["base_speed"] = int(speed_match.group(1))

    # Parse ability modifiers
    ability_match = re.search(
        r'(?:Ability Score|Racial) (?:Modifiers?|Adjustments?)[:\s]*([^.]+)',
        full_text, re.IGNORECASE
    )
    if ability_match:
        race["ability_modifiers"] = clean_text(ability_match.group(1))

    # Parse type
    type_match = re.search(r'Type[:\s]*([\w]+)', full_text, re.IGNORECASE)
    if type_match:
        race["type"] = type_match.group(1)

    # Parse languages
    lang_match = re.search(r'Languages?[:\s]*([^.]+?)(?:\.|$)', full_text, re.IGNORECASE)
    if lang_match:
        race["languages"] = clean_text(lang_match.group(1))

    # Parse description
    race["description"] = extract_race_description(content)

    # Parse racial traits
    race["racial_traits"] = parse_racial_traits(content)

    return race


def extract_race_description(content) -> str:
    """Get the first paragraph of race description."""
    h1 = content.find('h1')
    if not h1:
        return ""

    parts = []
    sib = h1.next_sibling
    while sib:
        if hasattr(sib, 'name') and sib.name in ('h2', 'h3', 'table'):
            break
        text = extract_text(sib) if hasattr(sib, 'name') else str(sib).strip()
        if text and len(text) > 20:
            parts.append(text)
        if sum(len(p) for p in parts) > 500:
            break
        sib = sib.next_sibling

    return clean_text(' '.join(parts))[:1000]


def parse_racial_traits(content) -> list[dict]:
    """Extract racial traits from the page."""
    traits = []

    for heading in content.find_all(['h3', 'h4', 'b', 'strong']):
        name = clean_text(extract_text(heading))
        if not name or len(name) > 60:
            continue

        # Look for trait-like patterns
        trait_keywords = ['racial trait', 'defense', 'offense', 'movement',
                          'senses', 'feat and skill', 'weapon familiarity',
                          'darkvision', 'low-light', 'keen senses']
        is_trait_heading = any(kw in name.lower() for kw in trait_keywords)

        if not is_trait_heading:
            # Check if it's in a "Racial Traits" section
            parent = heading.parent
            while parent:
                parent_text = extract_text(parent)[:100].lower() if parent else ''
                if 'racial trait' in parent_text or 'standard racial trait' in parent_text:
                    is_trait_heading = True
                    break
                parent = parent.parent if hasattr(parent, 'parent') else None

        # Get trait description
        desc_parts = []
        sib = heading.next_sibling
        while sib:
            if hasattr(sib, 'name') and sib.name in ('h2', 'h3', 'h4'):
                break
            if hasattr(sib, 'name') and sib.name in ('b', 'strong'):
                next_text = extract_text(sib)
                if next_text and len(next_text) > 3:
                    break
            text = extract_text(sib) if hasattr(sib, 'name') else str(sib).strip()
            if text:
                desc_parts.append(text)
            sib = sib.next_sibling

        description = clean_text(' '.join(desc_parts))
        if name and description and len(description) > 5:
            traits.append({
                "name": name,
                "trait_type": categorize_racial_trait(name),
                "description": description[:2000],
                "replaces": "",  # filled in for alternate racial traits
            })

    return traits


def categorize_racial_trait(name: str) -> str:
    """Categorize a racial trait by type."""
    name_lower = name.lower()
    if any(kw in name_lower for kw in ['darkvision', 'low-light', 'keen senses', 'perception']):
        return 'senses'
    if any(kw in name_lower for kw in ['weapon', 'hatred', 'offensive', 'ferocity']):
        return 'offense'
    if any(kw in name_lower for kw in ['armor', 'defense', 'hardy', 'resist', 'stability']):
        return 'defense'
    if any(kw in name_lower for kw in ['skill', 'feat', 'bonus feat', 'skilled']):
        return 'feat_and_skill'
    if any(kw in name_lower for kw in ['speed', 'movement', 'slow', 'fleet']):
        return 'movement'
    if any(kw in name_lower for kw in ['language', 'linguist']):
        return 'language'
    if any(kw in name_lower for kw in ['magic', 'spell', 'gnome magic', 'elven magic']):
        return 'magical'
    return 'other'


def parse_race_batch(urls: list[str], progress_callback=None) -> list[dict]:
    """Parse multiple race pages."""
    results = []
    total = len(urls)

    for i, url in enumerate(urls):
        try:
            race = parse_race_page(url)
            if race:
                results.append(race)
                if progress_callback:
                    progress_callback(i + 1, total, race["name"])
        except Exception as e:
            print(f"    ⚠ Error parsing {url}: {e}")

    return results
