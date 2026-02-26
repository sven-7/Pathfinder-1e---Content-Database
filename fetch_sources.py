#!/usr/bin/env python3
"""
fetch_sources.py — Clone or update data source repositories.
Run this first before importing data.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def clone_or_update(name, repo_url, branch, local_path):
    """Clone a repo if it doesn't exist, or pull updates if it does."""
    full_path = ROOT / local_path

    if full_path.exists() and (full_path / ".git").exists():
        print(f"  ↻ Updating {name}...")
        result = subprocess.run(
            ["git", "-C", str(full_path), "pull", "--ff-only"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"    ✓ Updated: {result.stdout.strip()}")
        else:
            print(f"    ⚠ Pull failed (may need manual resolution): {result.stderr.strip()}")
    else:
        print(f"  ↓ Cloning {name}...")
        full_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--branch", branch, "--depth", "1", repo_url, str(full_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"    ✓ Cloned to {local_path}")
        else:
            print(f"    ✗ Clone failed: {result.stderr.strip()}")
            return False
    return True


def main():
    print("=" * 60)
    print("Pathfinder 1e Content Database — Fetch Sources")
    print("=" * 60)

    config = load_config()
    success = True

    # Clone PSRD-Data (primary source)
    psrd = config["psrd_data"]
    print(f"\n[1/3] PSRD-Data (Primary)")
    if not clone_or_update("PSRD-Data", psrd["repo_url"], psrd["branch"], psrd["local_path"]):
        success = False

    # Clone Foundry PF1e Content (supplementary)
    foundry = config["foundry_pf1e"]
    print(f"\n[2/3] Foundry VTT PF1e Content (Supplementary)")
    if not clone_or_update("PF1e Content", foundry["repo_url"], foundry["branch"], foundry["local_path"]):
        print("    (Non-critical — continuing)")

    # Clone Foundry Archetypes (supplementary)
    archetypes = config["foundry_archetypes"]
    print(f"\n[3/3] Foundry VTT PF1e Archetypes (Supplementary)")
    if not clone_or_update("PF1e Archetypes", archetypes["repo_url"], archetypes["branch"], archetypes["local_path"]):
        print("    (Non-critical — continuing)")

    # Verify primary data
    psrd_path = ROOT / psrd["local_path"]
    if psrd_path.exists():
        book_dirs = [d for d in psrd_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        db_files = list(psrd_path.glob("*.db"))
        json_files = list(psrd_path.rglob("*.json"))
        print(f"\n--- PSRD-Data Summary ---")
        print(f"  Book directories: {len(book_dirs)}")
        print(f"  SQLite databases: {len(db_files)}")
        print(f"  JSON files:       {len(json_files)}")
        print(f"  Books found:      {', '.join(sorted(d.name for d in book_dirs))}")
    else:
        print(f"\n✗ PSRD-Data not found at {psrd_path}")
        print("  Cannot proceed without primary data source.")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    if success:
        print("✓ All sources fetched. Run 'python scripts/import_psrd.py' next.")
    else:
        print("⚠ Some sources failed. Check errors above.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
