#!/usr/bin/env python3
"""Discover and scrape archetypes for classes missing from parsed data.

Workflow:
  1. Fetch index pages for missing classes → discover individual archetype URLs
  2. Scrape each discovered URL using the archetype parser
  3. Merge into data/d20pfsrd/parsed/archetypes.json
  4. Import all unimported archetypes into the DB

Run:
    python scripts/scrape_missing_archetypes.py
"""

import json, os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.scrapers.base import fetch_page, parse_html, is_paizo_content
from src.scrapers.archetype_parser import parse_archetype_page

PARSED_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'd20pfsrd', 'parsed', 'archetypes.json')
MANIFEST_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'd20pfsrd', 'manifest', 'manifest.json')

# Index pages for classes whose individual archetypes weren't discovered
MISSING_INDEX_URLS = [
    # Shaman
    'https://www.d20pfsrd.com/classes/hybrid-classes/shaman/archetypes/paizo-shaman-archetypes',
    # Skald
    'https://www.d20pfsrd.com/classes/hybrid-classes/skald/archetypes/paizo-skald-archetypes',
    # Slayer
    'https://www.d20pfsrd.com/classes/hybrid-classes/slayer/archetypes/paizo-slayer-archetypes',
    # Swashbuckler
    'https://www.d20pfsrd.com/classes/hybrid-classes/swashbuckler/archetypes/paizo-swashbuckler-archetypes',
    # Mesmerist
    'https://www.d20pfsrd.com/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/mesmerist/archetypes/paizo-llc-mesmerist-archetypes',
    # Medium
    'https://www.d20pfsrd.com/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/medium/archetypes/paizo-llc-medium-archetypes',
    # Occultist
    'https://www.d20pfsrd.com/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/occultist/archetypes/paizo-llc-occultist-archetypes',
    # Psychic
    'https://www.d20pfsrd.com/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/psychic/archetypes/paizo-llc-psychic-archetypes',
    # Spiritualist
    'https://www.d20pfsrd.com/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes/spiritualist/archetypes/paizo-llc-spiritualist-archetypes',
    # Unchained Monk
    'https://www.d20pfsrd.com/classes/unchained-classes/monk-unchained/archetypes/archetypes-paizo',
    # Unchained Rogue
    'https://www.d20pfsrd.com/classes/unchained-classes/rogue-unchained/archetypes/paizo-archetypes',
    # Unchained Barbarian — no dedicated index page, individual archetypes at manifest depth-6
]

# Some unchained summoner archetypes are already at individual-page depth in the manifest
DIRECT_URLS = [
    'https://www.d20pfsrd.com/classes/unchained-classes/summoner-unchained/archetypes/construct-caller-unchained-summoner-archetype',
    'https://www.d20pfsrd.com/classes/unchained-classes/summoner-unchained/archetypes/devil-binder-unchained-summoner-archetype',
    'https://www.d20pfsrd.com/classes/unchained-classes/summoner-unchained/archetypes/devil-impostor-unchained-summoner-archetype',
    'https://www.d20pfsrd.com/classes/unchained-classes/summoner-unchained/archetypes/fey-caller-unchained-summoner-archetype',
    'https://www.d20pfsrd.com/classes/unchained-classes/summoner-unchained/archetypes/soulbound-summoner-unchained-summoner-archetype',
    'https://www.d20pfsrd.com/classes/unchained-classes/summoner-unchained/archetypes/twinned-summoner-unchained-summoner-archetype',
]


def discover_archetype_links(index_url: str) -> list[str]:
    """Fetch an archetype index page and return links to individual archetype pages."""
    print(f'  Discovering: {index_url}')
    html = fetch_page(index_url)
    if not html:
        print(f'    FAILED to fetch')
        return []

    soup = parse_html(html)
    base = index_url.rstrip('/')
    links = []
    seen = set()

    for a in soup.find_all('a', href=True):
        href = a['href']
        # Normalise to absolute
        if href.startswith('/'):
            href = 'https://www.d20pfsrd.com' + href
        elif not href.startswith('http'):
            continue

        # Must be a child of the index URL
        if not href.startswith(base + '/'):
            continue

        # Skip anchors and query strings
        href = href.split('#')[0].split('?')[0].rstrip('/')
        if href in seen or href == base:
            continue
        seen.add(href)

        # Must look like an individual archetype (one more path segment than index)
        index_depth = len(base.split('/'))
        link_depth  = len(href.split('/'))
        if link_depth == index_depth + 1:
            links.append(href)

    print(f'    Found {len(links)} archetype links')
    return links


def main():
    # Load existing parsed archetypes
    with open(PARSED_FILE) as f:
        existing = json.load(f)
    existing_urls = {a['url'] for a in existing}
    print(f'Existing parsed archetypes: {len(existing)}')

    # Step 1: discover individual URLs from index pages
    to_scrape = list(DIRECT_URLS)
    for idx_url in MISSING_INDEX_URLS:
        links = discover_archetype_links(idx_url)
        to_scrape.extend(links)
        time.sleep(1)

    # Deduplicate and skip already-parsed
    to_scrape = list(dict.fromkeys(to_scrape))  # preserve order, dedup
    to_scrape = [u for u in to_scrape if u not in existing_urls and is_paizo_content(u)]
    print(f'\nNew URLs to scrape: {len(to_scrape)}')

    # Step 2: scrape each individual archetype page
    new_archetypes = []
    for i, url in enumerate(to_scrape, 1):
        print(f'  [{i}/{len(to_scrape)}] {url}')
        try:
            result = parse_archetype_page(url)
            if result:
                new_archetypes.append(result)
                print(f'    OK: {result["name"]} ({result["parent_class"]})')
            else:
                print(f'    SKIP (not parseable as archetype)')
        except Exception as e:
            print(f'    ERROR: {e}')
        if i < len(to_scrape):
            time.sleep(1)

    print(f'\nParsed {len(new_archetypes)} new archetypes')

    # Step 3: merge and save
    merged = existing + new_archetypes
    with open(PARSED_FILE, 'w') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f'Saved {len(merged)} total archetypes to {PARSED_FILE}')

    return new_archetypes


if __name__ == '__main__':
    main()
