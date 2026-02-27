#!/usr/bin/env python3
"""
manifest.py — Phase 1: Build the complete content manifest.

Crawls d20pfsrd.com index pages to discover every piece of content,
organized by type. The manifest is the source of truth for what exists
and drives the parsing phase.

Output: data/d20pfsrd/manifest/manifest.json
"""

import re
from pathlib import Path

from .base import (
    BASE_URL, MANIFEST_DIR,
    fetch_page, parse_html, normalize_url,
    is_paizo_content, is_valid_content_url,
    save_json, load_json, extract_text,
    ensure_dirs,
)


# ============================================================
# INDEX PAGE DEFINITIONS
# ============================================================
# Each content type has known index pages on d20pfsrd.com.
# The crawler fetches these pages and extracts all content links.

CONTENT_INDEXES = {
    # --- TIER 1: Character Building (must-have) ---

    "spells": {
        "description": "All Paizo spells A-Z",
        "index_url": f"{BASE_URL}/magic/all-spells",
        "url_prefix": f"{BASE_URL}/magic/all-spells/",
        "tier": 1,
    },

    "classes_core": {
        "description": "Core classes (CRB)",
        "index_url": f"{BASE_URL}/classes/core-classes",
        "url_prefix": f"{BASE_URL}/classes/core-classes/",
        "tier": 1,
        "merge_into": "classes",
    },
    "classes_base": {
        "description": "Base classes (APG, UM, UC, ACG, etc.)",
        "index_url": f"{BASE_URL}/classes/base-classes",
        "url_prefix": f"{BASE_URL}/classes/base-classes/",
        "tier": 1,
        "merge_into": "classes",
    },
    "classes_hybrid": {
        "description": "Hybrid classes (ACG)",
        "index_url": f"{BASE_URL}/classes/hybrid-classes",
        "url_prefix": f"{BASE_URL}/classes/hybrid-classes/",
        "tier": 1,
        "merge_into": "classes",
    },
    "classes_alternate": {
        "description": "Alternate classes (Antipaladin, Ninja, Samurai)",
        "index_url": f"{BASE_URL}/classes/alternate-classes",
        "url_prefix": f"{BASE_URL}/classes/alternate-classes/",
        "tier": 1,
        "merge_into": "classes",
    },
    "classes_unchained": {
        "description": "Unchained classes",
        "index_url": f"{BASE_URL}/classes/unchained-classes",
        "url_prefix": f"{BASE_URL}/classes/unchained-classes/",
        "tier": 1,
        "merge_into": "classes",
    },
    "classes_occult": {
        "description": "Occult classes (OA)",
        "index_url": f"{BASE_URL}/alternative-rule-systems/paizo-rules-systems/occult-adventures/occult-classes",
        "url_prefix": f"{BASE_URL}/alternative-rule-systems/",
        "tier": 1,
        "merge_into": "classes",
    },
    "classes_prestige": {
        "description": "Prestige classes",
        "index_url": f"{BASE_URL}/classes/prestige-classes",
        "url_prefix": f"{BASE_URL}/classes/prestige-classes/",
        "tier": 1,
        "merge_into": "classes",
    },

    "feats_combat": {
        "description": "Combat feats",
        "index_url": f"{BASE_URL}/feats/combat-feats",
        "url_prefix": f"{BASE_URL}/feats/",
        "tier": 1,
        "merge_into": "feats",
    },
    "feats_general": {
        "description": "General feats",
        "index_url": f"{BASE_URL}/feats/general-feats",
        "url_prefix": f"{BASE_URL}/feats/",
        "tier": 1,
        "merge_into": "feats",
    },
    "feats_metamagic": {
        "description": "Metamagic feats",
        "index_url": f"{BASE_URL}/feats/metamagic-feats",
        "url_prefix": f"{BASE_URL}/feats/",
        "tier": 1,
        "merge_into": "feats",
    },
    "feats_item_creation": {
        "description": "Item creation feats",
        "index_url": f"{BASE_URL}/feats/item-creation-feats",
        "url_prefix": f"{BASE_URL}/feats/",
        "tier": 1,
        "merge_into": "feats",
    },
    "feats_style": {
        "description": "Style feats",
        "index_url": f"{BASE_URL}/feats/style-feats",
        "url_prefix": f"{BASE_URL}/feats/",
        "tier": 1,
        "merge_into": "feats",
    },
    "feats_conduit": {
        "description": "Conduit feats",
        "index_url": f"{BASE_URL}/feats/conduit-feats",
        "url_prefix": f"{BASE_URL}/feats/",
        "tier": 1,
        "merge_into": "feats",
    },
    "feats_other": {
        "description": "Other/uncategorized feats (teamwork, critical, etc.)",
        "index_url": f"{BASE_URL}/feats/other-feats",
        "url_prefix": f"{BASE_URL}/feats/",
        "tier": 1,
        "merge_into": "feats",
    },

    "races": {
        "description": "All races",
        "index_url": f"{BASE_URL}/races",
        "url_prefix": f"{BASE_URL}/races/",
        "tier": 1,
    },

    "traits_combat": {
        "description": "Combat traits",
        "index_url": f"{BASE_URL}/traits/combat-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_faith": {
        "description": "Faith traits",
        "index_url": f"{BASE_URL}/traits/faith-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_magic": {
        "description": "Magic traits",
        "index_url": f"{BASE_URL}/traits/magic-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_social": {
        "description": "Social traits",
        "index_url": f"{BASE_URL}/traits/social-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_race": {
        "description": "Race traits",
        "index_url": f"{BASE_URL}/traits/race-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_regional": {
        "description": "Regional traits",
        "index_url": f"{BASE_URL}/traits/regional-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_religion": {
        "description": "Religion traits",
        "index_url": f"{BASE_URL}/traits/religion-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_equipment": {
        "description": "Equipment traits",
        "index_url": f"{BASE_URL}/traits/equipment-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_family": {
        "description": "Family traits",
        "index_url": f"{BASE_URL}/traits/family-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },
    "traits_campaign": {
        "description": "Campaign traits",
        "index_url": f"{BASE_URL}/traits/campaign-traits",
        "url_prefix": f"{BASE_URL}/traits/",
        "tier": 1,
        "merge_into": "traits",
    },

    # --- TIER 2: Equipment ---

    "equipment": {
        "description": "Mundane equipment, weapons, armor",
        "index_url": f"{BASE_URL}/equipment",
        "url_prefix": f"{BASE_URL}/equipment/",
        "tier": 2,
    },

    "magic_items": {
        "description": "Magic items (wondrous, rings, rods, etc.)",
        "index_url": f"{BASE_URL}/magic-items",
        "url_prefix": f"{BASE_URL}/magic-items/",
        "tier": 2,
    },
}


def crawl_index_page(config: dict) -> list[str]:
    """Crawl a single index page and extract all content URLs.

    Args:
        config: Entry from CONTENT_INDEXES

    Returns:
        List of discovered content URLs
    """
    url = config["index_url"]
    print(f"  Fetching index: {url}")

    html = fetch_page(url)
    if not html:
        print(f"    ✗ Failed to fetch {url}")
        return []

    soup = parse_html(html)

    # Extract all links from the page content
    urls = set()

    # Find the main content area
    content = (
        soup.select_one('article .article-content')
        or soup.select_one('div.article-content')
        or soup.select_one('article')
        or soup.find('body')
    )

    if not content:
        print(f"    ✗ No content area found")
        return []

    for a_tag in content.find_all('a', href=True):
        raw_url = normalize_url(a_tag['href'])

        # Must be on d20pfsrd.com
        if 'd20pfsrd.com' not in raw_url:
            continue

        # Must be valid content
        if not is_valid_content_url(raw_url):
            continue

        # Must be Paizo content (no 3pp)
        if not is_paizo_content(raw_url):
            continue

        urls.add(raw_url)

    return sorted(urls)


def crawl_spell_index() -> list[str]:
    """Specially handle the spell index which uses A-Z sub-pages.

    The main spell index page has links like /magic/all-spells/a/, /magic/all-spells/b/, etc.
    Each letter page lists all spells starting with that letter.
    """
    base_url = f"{BASE_URL}/magic/all-spells"
    print(f"  Fetching spell master index: {base_url}")

    html = fetch_page(base_url)
    if not html:
        return []

    soup = parse_html(html)

    # The main page lists ALL spells with links — it's one massive page
    # Extract all spell links (they go to /magic/all-spells/X/spell-name/)
    spell_urls = set()

    content = (
        soup.select_one('article .article-content')
        or soup.select_one('div.article-content')
        or soup.select_one('article')
        or soup.find('body')
    )

    if not content:
        return []

    for a_tag in content.find_all('a', href=True):
        raw_url = normalize_url(a_tag['href'])

        # Must be a spell detail page
        if '/magic/all-spells/' not in raw_url:
            continue
        if not is_valid_content_url(raw_url):
            continue
        if not is_paizo_content(raw_url):
            continue

        # Filter: must have at least 4 path segments (magic/all-spells/letter/name)
        path = urlparse_path(raw_url)
        parts = [p for p in path.split('/') if p]
        if len(parts) >= 4:  # magic, all-spells, letter, spell-name
            spell_urls.add(raw_url)

    print(f"    Found {len(spell_urls)} spell URLs from master index")
    return sorted(spell_urls)


def urlparse_path(url: str) -> str:
    """Extract just the path from a URL."""
    from urllib.parse import urlparse
    return urlparse(url).path


def crawl_class_detail_pages(class_urls: list[str]) -> dict:
    """For each class URL, discover archetype sub-pages.

    Returns dict mapping class_url -> list of archetype URLs.
    """
    # Only process URLs that look like actual class pages
    # Skip: mythic, bestiary, bloodline-disciples, bare /archetypes, etc.
    VALID_CLASS_PREFIXES = [
        '/classes/core-classes/',
        '/classes/base-classes/',
        '/classes/hybrid-classes/',
        '/classes/alternate-classes/',
        '/classes/unchained-classes/',
        '/classes/prestige-classes/',
        '/occult-adventures/occult-classes/',
    ]
    SKIP_SEGMENTS = [
        'mythic', 'bestiary', 'monster', 'bloodline-disciples',
        'mythic-heroes', 'mythic-magic', 'mythic-feats',
    ]

    archetypes = {}

    for class_url in class_urls:
        # Filter: must match a valid class URL pattern
        url_lower = class_url.lower()
        is_valid = any(prefix in url_lower for prefix in VALID_CLASS_PREFIXES)
        has_skip = any(seg in url_lower for seg in SKIP_SEGMENTS)

        if not is_valid or has_skip:
            continue

        # Skip sub-pages (rage-powers, arcana, etc.) — only top-level class pages
        # These have structure: /classes/<category>/<class-name>/
        # Sub-pages have deeper paths: /classes/<category>/<class-name>/<sub-feature>/
        from urllib.parse import urlparse
        path = urlparse(class_url).path.rstrip('/')
        parts = [p for p in path.split('/') if p]
        # For standard classes: ['classes', 'core-classes', 'barbarian'] = 3 parts
        # For prestige: ['classes', 'prestige-classes', 'other-paizo', 'a-b', 'arcane-archer'] = 5 parts
        # For occult: ['alternative-rule-systems', 'paizo-rules-systems', 'occult-adventures', 'occult-classes', 'kineticist'] = 5 parts
        # Sub-features: ['classes', 'core-classes', 'barbarian', 'rage-powers'] = 4+ parts (skip for standard)
        # We want the class root page, so for standard classes exactly 3 parts
        # For prestige/occult it's deeper but still a class page
        # Simplest filter: skip if last segment is a known sub-feature name
        FEATURE_SEGMENTS = {
            'rage-powers', 'rogue-talents', 'archetypes', 'discoveries',
            'magus-arcana', 'hexes', 'bloodlines', 'domains', 'mysteries',
            'orders', 'deeds', 'talents', 'arcane-schools', 'spirits',
            'blessings', 'ki-powers', 'mercy', 'masterpieces',
            'bardic-masterpieces', 'animal-companions', 'eidolons',
            'witch-patrons', 'inquisitions', 'ninja-tricks',
            'slayer-talents', 'investigator-talents', 'arcanist-exploits',
            'kineticist-elements', 'kineticist-wild-talents',
            'wild-talents', 'infusion-wild-talents', 'utility-wild-talents',
            'mesmerist-tricks', 'implement-schools', 'psychic-disciplines',
            'ranger-combat-styles', 'swashbuckler-deeds',
            'fighter-bravery-alternative-options',
            'thematic-channeling', 'variant-channeling',
            'example-paladin-codes',
        }
        last_segment = parts[-1] if parts else ''
        if last_segment in FEATURE_SEGMENTS:
            continue

        # Check for /archetypes/ sub-page
        archetype_index_url = class_url.rstrip('/') + '/archetypes'
        html = fetch_page(archetype_index_url)

        if html:
            soup = parse_html(html)
            content = (
                soup.select_one('article .article-content')
                or soup.select_one('div.article-content')
                or soup.select_one('article')
                or soup.find('body')
            )

            if content:
                arch_urls = set()
                for a_tag in content.find_all('a', href=True):
                    raw_url = normalize_url(a_tag['href'])
                    if is_paizo_content(raw_url) and is_valid_content_url(raw_url):
                        if '/archetypes/' in raw_url or '/archetype' in raw_url:
                            arch_urls.add(raw_url)

                if arch_urls:
                    archetypes[class_url] = sorted(arch_urls)
                    # Extract class name for display
                    class_name = parts[-1] if parts else 'unknown'
                    print(f"    {class_name}: {len(arch_urls)} archetypes")

    return archetypes


def build_manifest(tiers: list[int] | None = None) -> dict:
    """Build the complete content manifest.

    Args:
        tiers: Which tiers to include (default: [1] for character building)

    Returns:
        Manifest dict with URLs organized by content type
    """
    if tiers is None:
        tiers = [1]  # Character building only by default

    print("=" * 60)
    print("Phase 1: Building Content Manifest")
    print("=" * 60)

    manifest = {
        "metadata": {
            "source": "d20pfsrd.com",
            "tiers_included": tiers,
            "content_types": {},
        },
        "urls": {},
    }

    # --- Spells (special handling) ---
    if 1 in tiers:
        print("\n[Spells]")
        spell_urls = crawl_spell_index()
        manifest["urls"]["spells"] = spell_urls
        manifest["metadata"]["content_types"]["spells"] = len(spell_urls)
        print(f"  Total: {len(spell_urls)} spells")

    # --- All other content types ---
    for key, config in CONTENT_INDEXES.items():
        if config["tier"] not in tiers:
            continue
        if key == "spells":
            continue  # Already handled

        merge_target = config.get("merge_into", key)

        print(f"\n[{config['description']}]")
        urls = crawl_index_page(config)
        print(f"  Found: {len(urls)} URLs")

        # Merge into target category
        if merge_target not in manifest["urls"]:
            manifest["urls"][merge_target] = []
        manifest["urls"][merge_target].extend(urls)

    # Deduplicate merged categories
    for category in manifest["urls"]:
        original_count = len(manifest["urls"][category])
        manifest["urls"][category] = sorted(set(manifest["urls"][category]))
        deduped_count = len(manifest["urls"][category])
        manifest["metadata"]["content_types"][category] = deduped_count
        if original_count != deduped_count:
            print(f"  [{category}] Deduped: {original_count} → {deduped_count}")

    # --- Archetype discovery (follow class pages to find archetype sub-pages) ---
    if 1 in tiers and "classes" in manifest["urls"]:
        print("\n[Archetype Discovery]")
        print("  Scanning class pages for archetype links...")
        archetypes_map = crawl_class_detail_pages(manifest["urls"]["classes"])
        all_archetype_urls = []
        for arch_list in archetypes_map.values():
            all_archetype_urls.extend(arch_list)
        all_archetype_urls = sorted(set(all_archetype_urls))
        manifest["urls"]["archetypes"] = all_archetype_urls
        manifest["metadata"]["content_types"]["archetypes"] = len(all_archetype_urls)
        print(f"  Total: {len(all_archetype_urls)} archetype URLs")

    # Save manifest
    ensure_dirs()
    manifest_path = MANIFEST_DIR / "manifest.json"
    save_json(manifest, manifest_path)
    print(f"\n{'=' * 60}")
    print(f"Manifest saved: {manifest_path}")
    print(f"\nContent Summary:")
    for ctype, count in sorted(manifest["metadata"]["content_types"].items()):
        print(f"  {ctype:20s}: {count:,} URLs")
    total = sum(manifest["metadata"]["content_types"].values())
    print(f"  {'TOTAL':20s}: {total:,} URLs")
    print(f"{'=' * 60}")

    return manifest


def load_manifest() -> dict | None:
    """Load existing manifest from disk."""
    return load_json(MANIFEST_DIR / "manifest.json")
