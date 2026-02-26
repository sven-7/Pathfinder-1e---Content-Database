#!/usr/bin/env python3
"""
feat_parser.py — Parse d20pfsrd.com feat pages into structured data.

d20pfsrd feat page structure varies but generally:
  # Feat Name (Type)
  Source: Book Name
  <flavor text>
  **Prerequisite(s)**: ...
  **Benefit**: ...
  **Normal**: ...
  **Special**: ...

Output: JSON dict matching our schema's feats table.
"""

import re
from .base import (
    fetch_page, parse_html, get_article_content,
    extract_text, clean_text,
)


# Feat type detection from URL path and page content
FEAT_TYPE_MAP = {
    'combat-feats': 'combat',
    'metamagic-feats': 'metamagic',
    'item-creation-feats': 'item_creation',
    'style-feats': 'style',
    'conduit-feats': 'conduit',
    'teamwork-feats': 'teamwork',
    'critical-feats': 'critical',
    'performance-feats': 'performance',
    'general-feats': 'general',
    'mythic-feats': 'mythic',
    'story-feats': 'story',
    'racial-feats': 'racial',
    'grit-feats': 'grit',
    'panache-feats': 'panache',
    'betrayal-feats': 'betrayal',
    'targeting-feats': 'targeting',
    'animal-companion-feats': 'animal_companion',
}


def detect_feat_type(url: str, page_text: str) -> str:
    """Detect feat type from URL and page content."""
    url_lower = url.lower()

    # Check URL path
    for path_fragment, feat_type in FEAT_TYPE_MAP.items():
        if path_fragment in url_lower:
            return feat_type

    # Check page text for type indicators
    text_lower = page_text.lower()
    if '(combat)' in text_lower:
        return 'combat'
    elif '(metamagic)' in text_lower:
        return 'metamagic'
    elif '(item creation)' in text_lower:
        return 'item_creation'
    elif '(teamwork)' in text_lower:
        return 'teamwork'
    elif '(critical)' in text_lower:
        return 'critical'
    elif '(style)' in text_lower:
        return 'style'
    elif '(performance)' in text_lower:
        return 'performance'
    elif '(story)' in text_lower:
        return 'story'
    elif '(mythic)' in text_lower:
        return 'mythic'
    elif '(grit)' in text_lower or '(panache)' in text_lower:
        return 'grit'

    return 'general'


def parse_feat_page(url: str, html: str = None) -> dict | None:
    """Parse a single feat page into structured data.

    Args:
        url: The feat page URL
        html: Pre-fetched HTML (optional)

    Returns:
        Dict with feat data, or None on failure
    """
    if html is None:
        html = fetch_page(url)
    if not html:
        return None

    soup = parse_html(html)
    content = get_article_content(soup)
    if not content:
        return None

    # Get feat name from h1
    h1 = content.find('h1') or soup.find('h1')
    if not h1:
        return None

    raw_name = clean_text(extract_text(h1))
    if not raw_name:
        return None

    # Strip type suffix from name: "Power Attack (Combat)" → "Power Attack"
    name = re.sub(r'\s*\([^)]*\)\s*$', '', raw_name).strip()

    full_text = extract_text(content)

    feat = {
        "name": name,
        "url": url,
        "feat_type": detect_feat_type(url, full_text),
        "prerequisites": "",
        "prerequisite_feats": "",
        "benefit": "",
        "normal": "",
        "special": "",
        "description": "",
        "source": "",
    }

    # Parse bold-labeled sections
    sections = extract_feat_sections(content)

    feat["prerequisites"] = clean_text(sections.get('prerequisites', sections.get('prerequisite', '')))
    feat["benefit"] = clean_text(sections.get('benefit', sections.get('benefits', '')))
    feat["normal"] = clean_text(sections.get('normal', ''))
    feat["special"] = clean_text(sections.get('special', ''))
    feat["source"] = clean_text(sections.get('source', ''))

    # Extract prerequisite feat names from prereq text
    feat["prerequisite_feats"] = extract_prerequisite_feats(feat["prerequisites"])

    # Description: flavor text before the prerequisites section
    feat["description"] = extract_feat_description(content, sections)

    if not feat["name"]:
        return None

    return feat


def extract_feat_sections(content) -> dict:
    """Extract named sections from a feat page.

    Feat pages use bold labels for Prerequisite(s), Benefit, Normal, Special.
    """
    sections = {}

    bold_tags = content.find_all(['b', 'strong'])

    for bold in bold_tags:
        label = extract_text(bold).strip().rstrip(':').rstrip('(s)').lower()

        # Normalize common variants
        if 'prerequisite' in label:
            label = 'prerequisites'
        elif label in ('benefit', 'benefits'):
            label = 'benefit'
        elif label == 'normal':
            label = 'normal'
        elif label == 'special':
            label = 'special'
        elif label == 'source':
            label = 'source'
        else:
            continue

        # Collect text until next bold label or structural element
        value_parts = []
        sibling = bold.next_sibling
        while sibling:
            if hasattr(sibling, 'name') and sibling.name in ('b', 'strong', 'h1', 'h2', 'h3', 'h4', 'hr'):
                # Check if this bold tag is another section label
                if hasattr(sibling, 'name') and sibling.name in ('b', 'strong'):
                    next_label = extract_text(sibling).strip().rstrip(':').lower()
                    if any(kw in next_label for kw in ['prerequisite', 'benefit', 'normal', 'special', 'source']):
                        break
                else:
                    break

            text = extract_text(sibling) if hasattr(sibling, 'name') else str(sibling)
            value_parts.append(text)
            sibling = sibling.next_sibling

        value = ' '.join(value_parts).strip().lstrip(':').strip()
        if value:
            sections[label] = value

    return sections


def extract_prerequisite_feats(prereq_text: str) -> str:
    """Extract feat names from prerequisite text.

    e.g., "Str 13, Power Attack, base attack bonus +1"
    → "Power Attack"

    Returns comma-separated feat names.
    """
    if not prereq_text:
        return ""

    # Known non-feat prerequisites to filter out
    non_feat_patterns = [
        r'\b(?:str|dex|con|int|wis|cha)\s+\d+',  # ability scores
        r'\bbase attack bonus\s+\+?\d+',
        r'\bcaster level\s+\d+',
        r'\bcharacter level\s+\d+',
        r'\b\d+(?:st|nd|rd|th)\s+level',
        r'\bability to\s+',
        r'\bproficiency with\s+',
        r'\bproficient with\s+',
        r'\bclass feature\b',
        r'\bclass level\b',
        r'\bspellcasting\b',
        r'\bsneak attack\b',
        r'\brage\b',
        r'\bki pool\b',
        r'\bbardic performance\b',
    ]

    # Split by comma, identify likely feat names
    parts = re.split(r',\s*', prereq_text)
    feat_names = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Skip if it matches a non-feat pattern
        is_non_feat = False
        for pattern in non_feat_patterns:
            if re.search(pattern, part, re.IGNORECASE):
                is_non_feat = True
                break

        if is_non_feat:
            continue

        # Likely a feat name: starts with capital, no numbers at start
        if part and part[0].isupper() and not re.match(r'^\d', part):
            # Clean up: remove "or" conjunctions, trailing conditions
            feat_name = re.sub(r'\s+or\s+.*', '', part)
            feat_name = re.sub(r'\s*\(.*\)', '', feat_name)
            feat_name = feat_name.strip()
            if feat_name and len(feat_name) > 2:
                feat_names.append(feat_name)

    return ', '.join(feat_names)


def extract_feat_description(content, sections: dict) -> str:
    """Extract the flavor/description text from a feat page.

    This is typically the text between the h1 and the first bold-labeled section.
    """
    h1 = content.find('h1')
    if not h1:
        return ""

    desc_parts = []
    sibling = h1.next_sibling

    while sibling:
        # Stop at first bold-labeled section
        if hasattr(sibling, 'name') and sibling.name in ('b', 'strong'):
            label = extract_text(sibling).strip().lower()
            if any(kw in label for kw in ['prerequisite', 'benefit', 'normal', 'special', 'source']):
                break

        text = extract_text(sibling) if hasattr(sibling, 'name') else str(sibling).strip()
        if text and len(text) > 3:
            # Skip structural markers
            if text.strip() not in ('CASTING', 'EFFECT', 'DESCRIPTION', 'STATISTICS'):
                desc_parts.append(text)

        sibling = sibling.next_sibling

    description = ' '.join(desc_parts).strip()

    # Trim footer/noise
    for stop in ['Discuss!', 'Join Our Discord', 'Shop the Open Gaming']:
        idx = description.find(stop)
        if idx > 0:
            description = description[:idx].strip()

    return clean_text(description)


def parse_feat_batch(urls: list[str], progress_callback=None) -> list[dict]:
    """Parse multiple feat pages."""
    results = []
    total = len(urls)

    for i, url in enumerate(urls):
        try:
            feat = parse_feat_page(url)
            if feat:
                results.append(feat)
                if progress_callback:
                    progress_callback(i + 1, total, feat["name"])
            else:
                if progress_callback:
                    progress_callback(i + 1, total, f"SKIP: {url}")
        except Exception as e:
            print(f"    ⚠ Error parsing {url}: {e}")

    return results
