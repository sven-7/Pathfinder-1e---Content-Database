#!/usr/bin/env python3
"""
scrape_d20pfsrd.py — Main scraper orchestrator.

Runs the complete d20pfsrd.com scraping pipeline:
  Phase 1: Build content manifest (discover all URLs)
  Phase 2: Parse content pages (extract structured data)
  Phase 3: Save parsed data as JSON (ready for import)

Usage:
  python scripts/scrape_d20pfsrd.py                   # Full pipeline (Tier 1 only)
  python scripts/scrape_d20pfsrd.py --phase manifest   # Phase 1 only
  python scripts/scrape_d20pfsrd.py --phase parse      # Phase 2 only (needs manifest)
  python scripts/scrape_d20pfsrd.py --type spells      # Parse only spells
  python scripts/scrape_d20pfsrd.py --type feats       # Parse only feats
  python scripts/scrape_d20pfsrd.py --type classes     # Parse only classes
  python scripts/scrape_d20pfsrd.py --type races       # Parse only races
  python scripts/scrape_d20pfsrd.py --tier 1 2         # Include Tier 2 (equipment)
  python scripts/scrape_d20pfsrd.py --limit 50         # Parse only first N URLs per type
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.scrapers.base import PARSED_DIR, save_json, load_json, ensure_dirs
from src.scrapers.manifest import build_manifest, load_manifest
from src.scrapers.spell_parser import parse_spell_batch
from src.scrapers.feat_parser import parse_feat_batch
from src.scrapers.class_parser import parse_class_batch
from src.scrapers.race_parser import parse_race_batch


def progress_printer(current, total, name):
    """Print progress bar."""
    pct = current / total * 100
    bar_len = 30
    filled = int(bar_len * current / total)
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f"\r  [{bar}] {current}/{total} ({pct:.0f}%) {name[:40]:40s}", end='', flush=True)
    if current == total:
        print()  # newline at end


def run_manifest(tiers: list[int]):
    """Phase 1: Build the content manifest."""
    return build_manifest(tiers=tiers)


def run_parse(content_types: list[str] | None, limit: int | None):
    """Phase 2: Parse content from manifest URLs."""
    manifest = load_manifest()
    if not manifest:
        print("✗ No manifest found. Run Phase 1 first: --phase manifest")
        sys.exit(1)

    ensure_dirs()

    # Determine which types to parse
    available_types = list(manifest["urls"].keys())
    if content_types:
        types_to_parse = [t for t in content_types if t in available_types]
    else:
        types_to_parse = available_types

    print(f"Parsing content types: {', '.join(types_to_parse)}")
    print(f"Limit per type: {limit or 'ALL'}")

    results_summary = {}

    for content_type in types_to_parse:
        urls = manifest["urls"].get(content_type, [])
        if limit:
            urls = urls[:limit]

        if not urls:
            print(f"\n[{content_type}] No URLs — skipping")
            continue

        print(f"\n{'=' * 60}")
        print(f"[{content_type.upper()}] Parsing {len(urls)} pages...")
        print(f"{'=' * 60}")

        start_time = time.time()

        if content_type == "spells":
            parsed = parse_spell_batch(urls, progress_callback=progress_printer)
        elif content_type == "feats":
            parsed = parse_feat_batch(urls, progress_callback=progress_printer)
        elif content_type == "classes":
            parsed = parse_class_batch(urls, progress_callback=progress_printer)
        elif content_type == "races":
            parsed = parse_race_batch(urls, progress_callback=progress_printer)
        else:
            print(f"  ⚠ No parser for '{content_type}' yet — skipping")
            continue

        elapsed = time.time() - start_time

        # Save parsed data
        output_path = PARSED_DIR / f"{content_type}.json"
        save_json(parsed, output_path)

        results_summary[content_type] = {
            "urls_attempted": len(urls),
            "successfully_parsed": len(parsed),
            "elapsed_seconds": round(elapsed, 1),
            "output_file": str(output_path),
        }

        print(f"  ✓ {len(parsed)}/{len(urls)} parsed in {elapsed:.1f}s → {output_path.name}")

    return results_summary


def print_status():
    """Print current scraper status: manifest + parsed data counts."""
    manifest = load_manifest()
    if not manifest:
        print("No manifest found. Run Phase 1 first.")
        return

    print("=" * 60)
    print("Scraper Status")
    print("=" * 60)

    print("\n--- Manifest ---")
    for ctype, count in sorted(manifest["metadata"]["content_types"].items()):
        # Check if parsed data exists
        parsed_path = PARSED_DIR / f"{ctype}.json"
        parsed_count = 0
        if parsed_path.exists():
            parsed_data = load_json(parsed_path)
            if parsed_data:
                parsed_count = len(parsed_data)

        status = f"✓ {parsed_count}" if parsed_count > 0 else "○ not parsed"
        print(f"  {ctype:20s}: {count:6,} URLs  →  {status}")

    total_urls = sum(manifest["metadata"]["content_types"].values())
    print(f"\n  Total URLs in manifest: {total_urls:,}")


def main():
    parser = argparse.ArgumentParser(description="d20pfsrd.com content scraper")
    parser.add_argument('--phase', choices=['manifest', 'parse', 'all', 'status'],
                       default='all', help='Which phase to run')
    parser.add_argument('--type', nargs='+', dest='content_types',
                       help='Content types to parse (spells, feats, classes, races)')
    parser.add_argument('--tier', nargs='+', type=int, default=[1],
                       help='Content tiers to include in manifest (1=character building, 2=equipment)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Max URLs to parse per content type (for testing)')
    args = parser.parse_args()

    print("╔" + "═" * 58 + "╗")
    print("║   d20pfsrd.com Content Scraper                           ║")
    print("║   Pathfinder 1e Content Database                         ║")
    print("╚" + "═" * 58 + "╝")

    if args.phase == 'status':
        print_status()
        return

    if args.phase in ('manifest', 'all'):
        print(f"\n{'─' * 60}")
        print(f"Phase 1: Building Content Manifest (Tiers: {args.tier})")
        print(f"{'─' * 60}")
        run_manifest(tiers=args.tier)

    if args.phase in ('parse', 'all'):
        print(f"\n{'─' * 60}")
        print(f"Phase 2: Parsing Content Pages")
        print(f"{'─' * 60}")
        summary = run_parse(content_types=args.content_types, limit=args.limit)

        print(f"\n{'=' * 60}")
        print("Parse Summary")
        print(f"{'=' * 60}")
        for ctype, info in summary.items():
            print(f"  {ctype:15s}: {info['successfully_parsed']:,} / {info['urls_attempted']:,} "
                  f"({info['elapsed_seconds']}s)")
        print(f"\nParsed data saved to: {PARSED_DIR}")
        print(f"\nNext step: python scripts/import_scraped.py")


if __name__ == "__main__":
    main()
