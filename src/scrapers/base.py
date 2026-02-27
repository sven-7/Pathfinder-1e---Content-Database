#!/usr/bin/env python3
"""
base.py — Base scraper infrastructure.

Provides:
  - HTTP fetching with rate limiting (1 req/sec default)
  - Disk-based HTML caching (fetch once, re-parse freely)
  - BeautifulSoup HTML parsing utilities
  - URL normalization and filtering
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

# Default paths relative to project root
ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = ROOT / "data" / "d20pfsrd" / "cache"
MANIFEST_DIR = ROOT / "data" / "d20pfsrd" / "manifest"
PARSED_DIR = ROOT / "data" / "d20pfsrd" / "parsed"

BASE_URL = "https://www.d20pfsrd.com"

# Rate limiting
MIN_REQUEST_INTERVAL = 1.0  # seconds between requests
_last_request_time = 0.0


def ensure_dirs():
    """Create data directories if they don't exist."""
    for d in [CACHE_DIR, MANIFEST_DIR, PARSED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def url_to_cache_path(url: str) -> Path:
    """Convert a URL to a deterministic cache file path."""
    # Use URL hash for filename to avoid filesystem issues
    url_hash = hashlib.md5(url.encode()).hexdigest()
    # Also keep a readable prefix from the URL path
    parsed = urlparse(url)
    path_slug = parsed.path.strip('/').replace('/', '_')[:80]
    filename = f"{path_slug}_{url_hash}.html"
    return CACHE_DIR / filename


def fetch_page(url: str, use_cache: bool = True) -> str | None:
    """Fetch a page with rate limiting and caching.

    Args:
        url: Full URL to fetch
        use_cache: If True, return cached version if available

    Returns:
        HTML string, or None on failure
    """
    global _last_request_time

    # Check cache first
    cache_path = url_to_cache_path(url)
    if use_cache and cache_path.exists():
        return cache_path.read_text(encoding='utf-8')

    # Rate limiting
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)

    try:
        headers = {
            'User-Agent': 'PF1e-Content-DB/1.0 (Character building tool; OGL content)',
            'Accept': 'text/html',
        }
        response = requests.get(url, headers=headers, timeout=30)
        _last_request_time = time.time()

        if response.status_code == 200:
            html = response.text
            # Cache to disk
            ensure_dirs()
            cache_path.write_text(html, encoding='utf-8')
            return html
        else:
            print(f"    ⚠ HTTP {response.status_code}: {url}")
            return None

    except requests.RequestException as e:
        print(f"    ⚠ Request failed: {url} — {e}")
        _last_request_time = time.time()
        return None


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML string into BeautifulSoup."""
    return BeautifulSoup(html, 'html.parser')


def get_article_content(soup: BeautifulSoup) -> Tag | None:
    """Extract the main content area from a d20pfsrd page.

    d20pfsrd uses WordPress with content in article or div#article-content.
    """
    # Try common content containers
    for selector in [
        'article .article-content',
        'div.article-content',
        'article',
        '#article-content',
        '.entry-content',
        '#content',
    ]:
        content = soup.select_one(selector)
        if content:
            return content

    # Fallback: find the main h1 and get its parent
    h1 = soup.find('h1')
    if h1:
        return h1.parent

    return soup.find('body')


def extract_text(element) -> str:
    """Extract clean text from a BeautifulSoup element."""
    if element is None:
        return ""
    if isinstance(element, str):
        return element.strip()
    return element.get_text(separator=' ', strip=True)


def normalize_url(url: str, base: str = BASE_URL) -> str:
    """Normalize a URL to absolute form."""
    if not url:
        return ""
    url = url.strip()
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/'):
        url = base + url
    elif not url.startswith('http'):
        url = urljoin(base + '/', url)
    # Remove trailing slashes for consistency (but keep root /)
    if url != base + '/' and url.endswith('/'):
        url = url.rstrip('/')
    return url


def is_paizo_content(url: str) -> bool:
    """Filter out 3rd party content URLs.

    d20pfsrd includes 3rd party publisher content alongside Paizo.
    We only want Paizo (OGL) content.
    """
    url_lower = url.lower()

    # Explicit 3rd party indicators in URL
    third_party_markers = [
        '3rd-party', '3pp', 'third-party',
        'rogue-genius', 'dreamscarred', 'legendary-games',
        'drop-dead-studios', 'orphaned-bookworm', 'samurai-sheepdog',
        'xoth-net', 'necromancers-of-the-northwest', 'frog-god',
        '4-winds', 'ascension-games', 'd20pfsrd-com-publishing',
        'kobold-press', 'super-genius', 'rite-publishing',
        'en-publishing', 'radiance-house', 'purple-duck',
        'open-design', 'alluria-publishing', 'adamant-entertainment',
        'petersen-games', 'michael-mars',
        'jon-brazer', 'everyman-gaming', 'louis-porter',
        'bloodstone-press', 'paizo-fans-united',
    ]

    for marker in third_party_markers:
        if marker in url_lower:
            return False

    return True


def is_valid_content_url(url: str) -> bool:
    """Check if a URL is a valid content page (not navigation/admin/store)."""
    url_lower = url.lower()

    skip_patterns = [
        '/wp-content/', '/wp-admin/', '/wp-includes/',
        'opengamingstore.com', 'opengamingnetwork.com',
        '/extras/', '/new-pages', '/recent-changes',
        '/legal/', '/fan-labs', '/character-sheets',
        '/downloads', '#', 'javascript:',
        '/tools/', '/spell-list-filters/',
        '/gaming-accessories/', '/d20pfsrd-com-publishing',
    ]

    for pattern in skip_patterns:
        if pattern in url_lower:
            return False

    # Must be on d20pfsrd.com
    if 'd20pfsrd.com' not in url_lower:
        return False

    return True


def extract_links(soup: BeautifulSoup, base_url: str = BASE_URL) -> list[str]:
    """Extract all content links from a page."""
    links = []
    for a_tag in soup.find_all('a', href=True):
        url = normalize_url(a_tag['href'], base_url)
        if url and is_valid_content_url(url):
            links.append(url)
    return list(set(links))  # deduplicate


def save_json(data: dict | list, filepath: Path):
    """Save data as formatted JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(filepath: Path) -> dict | list | None:
    """Load data from JSON file."""
    if not filepath.exists():
        return None
    with open(filepath, encoding='utf-8') as f:
        return json.load(f)


def clean_text(text: str) -> str:
    """Clean extracted text: normalize whitespace, remove artifacts."""
    if not text:
        return ""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove common artifacts
    text = text.replace('\xa0', ' ')
    text = text.replace('\u2013', '–')
    text = text.replace('\u2014', '—')
    return text


def parse_source_tag(text: str) -> str:
    """Extract source book name from d20pfsrd source attribution.

    d20pfsrd pages often have "Source: Book Name" or similar.
    """
    if not text:
        return ""
    patterns = [
        r'Source[:\s]+(.+?)(?:\.|$)',
        r'from\s+(?:the\s+)?(.+?)(?:\.|$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    return ""
