#!/usr/bin/env python3
"""
spell_parser.py — Parse d20pfsrd.com spell pages into structured data.

d20pfsrd spell page structure:
  # Spell Name
  **School** school (subschool) [descriptors]; **Level** class1 N, class2 N, ...
  CASTING
  **Casting Time** ...
  **Components** ...
  EFFECT
  **Range** ...
  **Effect|Area|Target** ...
  **Duration** ...
  **Saving Throw** ...; **Spell Resistance** ...
  DESCRIPTION
  <description text>

Output: JSON dict matching our schema's spells + spell_class_levels tables.
"""

import re
from .base import (
    fetch_page, parse_html, get_article_content,
    extract_text, clean_text, is_paizo_content,
)


def parse_spell_page(url: str, html: str = None) -> dict | None:
    """Parse a single spell page into structured data.

    Args:
        url: The spell page URL
        html: Pre-fetched HTML (optional; will fetch if not provided)

    Returns:
        Dict with spell data, or None on failure
    """
    if html is None:
        html = fetch_page(url)
    if not html:
        return None

    soup = parse_html(html)
    content = get_article_content(soup)
    if not content:
        return None

    # Get spell name from h1
    h1 = content.find('h1') or soup.find('h1')
    if not h1:
        return None
    name = clean_text(extract_text(h1))
    if not name:
        return None

    # Get the full text content for parsing
    full_text = extract_text(content)

    # Initialize result
    spell = {
        "name": name,
        "url": url,
        "school": "",
        "subschool": "",
        "descriptors": "",
        "casting_time": "",
        "components": "",
        "range": "",
        "area": "",
        "effect": "",
        "target": "",
        "duration": "",
        "saving_throw": "",
        "spell_resistance": "",
        "description": "",
        "class_levels": [],  # [{"class": "wizard", "level": 3}, ...]
        "source": "",
    }

    # --- Parse using bold-label pattern ---
    # d20pfsrd uses <b> or <strong> tags for labels

    # Extract all text segments keyed by their bold label
    parsed_fields = extract_bold_fields(content)

    # School line: "conjuration (creation) [acid]"
    school_text = parsed_fields.get('school', '')
    if school_text:
        spell["school"], spell["subschool"], spell["descriptors"] = parse_school_line(school_text)

    # Level line: "bloodrager 2, magus 2, sorcerer/wizard 2"
    level_text = parsed_fields.get('level', '')
    if level_text:
        spell["class_levels"] = parse_level_line(level_text)

    # Simple field mappings
    spell["casting_time"] = clean_text(parsed_fields.get('casting time', ''))
    spell["components"] = clean_text(parsed_fields.get('components', parsed_fields.get('component', '')))
    spell["range"] = clean_text(parsed_fields.get('range', ''))
    spell["area"] = clean_text(parsed_fields.get('area', ''))
    spell["effect"] = clean_text(parsed_fields.get('effect', ''))
    spell["target"] = clean_text(parsed_fields.get('target', parsed_fields.get('targets', '')))
    spell["duration"] = clean_text(parsed_fields.get('duration', ''))
    spell["saving_throw"] = clean_text(parsed_fields.get('saving throw', ''))
    spell["spell_resistance"] = clean_text(parsed_fields.get('spell resistance', ''))

    # Description: everything after the stat block
    spell["description"] = extract_spell_description(content, full_text)

    # Source attribution
    source_text = parsed_fields.get('source', '')
    if source_text:
        spell["source"] = clean_text(source_text)

    # Validation: must have a name and at least school or class levels
    if not spell["name"]:
        return None

    return spell


def extract_bold_fields(content) -> dict:
    """Extract field:value pairs from bold-labeled content.

    Handles patterns like:
      <b>School</b> conjuration; <b>Level</b> wizard 3
      <strong>Casting Time</strong> 1 standard action

    Returns dict mapping lowercase field names to their text values.
    """
    fields = {}

    # Get all bold/strong tags
    bold_tags = content.find_all(['b', 'strong'])

    for bold in bold_tags:
        label = extract_text(bold).strip().rstrip(':').lower()
        if not label or len(label) > 30:
            continue

        # Skip labels that are clearly not spell fields
        skip_labels = ['source', 'note', 'section', 'table', 'mythic',
                        'augmented', 'description']
        if label in skip_labels and label != 'source':
            continue

        # Get the text between this bold tag and the next bold tag (or end)
        value_parts = []
        sibling = bold.next_sibling
        while sibling:
            if hasattr(sibling, 'name') and sibling.name in ('b', 'strong'):
                break
            if hasattr(sibling, 'name') and sibling.name in ('h1', 'h2', 'h3', 'h4', 'hr'):
                break
            text = extract_text(sibling) if hasattr(sibling, 'name') else str(sibling)
            # Stop at semicolons that separate field pairs on the same line
            # e.g., "none; **Spell Resistance** no"
            if ';' in text:
                value_parts.append(text.split(';')[0])
                break
            value_parts.append(text)
            sibling = sibling.next_sibling

        value = ' '.join(value_parts).strip().lstrip(':').strip()

        if label and value:
            fields[label] = value

    return fields


def parse_school_line(text: str) -> tuple[str, str, str]:
    """Parse school text like 'conjuration (creation) [acid]'.

    Returns: (school, subschool, descriptors)
    """
    school = ""
    subschool = ""
    descriptors = ""

    text = clean_text(text)

    # Remove leading "school" label if present
    text = re.sub(r'^school\s*', '', text, flags=re.IGNORECASE).strip()

    # Extract subschool in parentheses
    subschool_match = re.search(r'\(([^)]+)\)', text)
    if subschool_match:
        subschool = subschool_match.group(1).strip()
        text = text[:subschool_match.start()] + text[subschool_match.end():]

    # Extract descriptors in brackets
    desc_match = re.search(r'\[([^\]]+)\]', text)
    if desc_match:
        descriptors = desc_match.group(1).strip()
        text = text[:desc_match.start()] + text[desc_match.end():]

    # What remains is the school name
    school = clean_text(text).rstrip(';').strip()

    return school, subschool, descriptors


def parse_level_line(text: str) -> list[dict]:
    """Parse level text like 'bloodrager 2, magus 2, sorcerer/wizard 2'.

    Returns: [{"class": "bloodrager", "level": 2}, ...]
    """
    levels = []
    text = clean_text(text)

    # Remove leading "level" label
    text = re.sub(r'^level\s*', '', text, flags=re.IGNORECASE).strip()

    # Split by comma, then parse each "class N" pair
    # Handle "sorcerer/wizard 2" as a combined entry
    entries = re.split(r',\s*', text)

    for entry in entries:
        entry = entry.strip().rstrip(';').strip()
        if not entry:
            continue

        # Match pattern: "class_name N" where N is the level number
        match = re.match(r'^(.+?)\s+(\d+)\s*$', entry)
        if match:
            class_name = match.group(1).strip().lower()
            level = int(match.group(2))

            # Handle combined classes like "sorcerer/wizard"
            if '/' in class_name:
                for cls in class_name.split('/'):
                    cls = cls.strip()
                    if cls:
                        levels.append({"class": cls, "level": level})
            else:
                levels.append({"class": class_name, "level": level})

    return levels


def extract_spell_description(content, full_text: str) -> str:
    """Extract the spell description text (after the stat block).

    The description is typically the last major text block on the page,
    after all the bold-labeled fields.
    """
    # Strategy: Find the last bold field (usually Spell Resistance),
    # and get all text after it until the page footer/sidebar.

    # Find all paragraphs in content
    paragraphs = content.find_all(['p', 'div'], recursive=False)

    description_parts = []
    in_description = False

    for p in paragraphs:
        text = extract_text(p)
        if not text:
            continue

        # Check if this paragraph contains stat block fields
        has_bold = p.find(['b', 'strong'])
        bold_text = extract_text(has_bold) if has_bold else ""

        stat_labels = ['school', 'level', 'casting time', 'components',
                       'range', 'area', 'effect', 'target', 'duration',
                       'saving throw', 'spell resistance']

        is_stat_line = any(lbl in bold_text.lower() for lbl in stat_labels) if bold_text else False

        # Skip headers like "CASTING", "EFFECT", "DESCRIPTION"
        if text.strip().upper() in ('CASTING', 'EFFECT', 'DESCRIPTION', 'STATISTICS'):
            in_description = (text.strip().upper() == 'DESCRIPTION')
            continue

        if is_stat_line:
            in_description = False
            continue

        # After all stat block content, collect description
        if not is_stat_line and not text.strip().upper() in ('CASTING', 'EFFECT'):
            # Heuristic: description paragraphs are typically longer
            # and don't start with bold labels
            if len(text) > 20 and not is_stat_line:
                description_parts.append(text)

    # If we didn't get much, fall back to a regex approach on full_text
    if not description_parts or sum(len(p) for p in description_parts) < 30:
        # Try to find description after "Spell Resistance" line
        sr_match = re.search(
            r'(?:Spell Resistance|SR)\s*[:\s]*(?:yes|no)[^.]*\.\s*(.+)',
            full_text, re.DOTALL | re.IGNORECASE
        )
        if sr_match:
            desc = sr_match.group(1).strip()
            # Trim at known footer patterns
            for stop in ['Discuss!', 'Join Our Discord', 'Shop the Open Gaming',
                         'Latest Pathfinder', 'Section 15', 'scroll to top']:
                idx = desc.find(stop)
                if idx > 0:
                    desc = desc[:idx].strip()
            return clean_text(desc)

    # Clean and join description parts
    description = '\n\n'.join(description_parts)

    # Trim footer content
    for stop in ['Discuss!', 'Join Our Discord', 'Shop the Open Gaming',
                 'Latest Pathfinder', 'Section 15', 'scroll to top',
                 'Become an Editor', 'Patreon Supporters']:
        idx = description.find(stop)
        if idx > 0:
            description = description[:idx].strip()

    return clean_text(description)


def parse_spell_batch(urls: list[str], progress_callback=None) -> list[dict]:
    """Parse multiple spell pages.

    Args:
        urls: List of spell page URLs to parse
        progress_callback: Optional function(current, total, name) for progress

    Returns:
        List of parsed spell dicts
    """
    results = []
    total = len(urls)

    for i, url in enumerate(urls):
        try:
            spell = parse_spell_page(url)
            if spell:
                results.append(spell)
                if progress_callback:
                    progress_callback(i + 1, total, spell["name"])
            else:
                if progress_callback:
                    progress_callback(i + 1, total, f"SKIP: {url}")
        except Exception as e:
            print(f"    ⚠ Error parsing {url}: {e}")

    return results
