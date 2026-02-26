#!/usr/bin/env python3
"""
setup.py — One-command project setup.
Fetches data sources and builds the SQLite database.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def run_script(name, description):
    """Run a Python script and report results."""
    script_path = SCRIPTS / name
    print(f"\n{'─' * 50}")
    print(f"Step: {description}")
    print(f"{'─' * 50}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT)
    )

    if result.returncode != 0:
        print(f"\n✗ {name} failed with exit code {result.returncode}")
        return False
    return True


def main():
    print("╔" + "═" * 58 + "╗")
    print("║   Pathfinder 1e Content Database — Full Setup            ║")
    print("╚" + "═" * 58 + "╝")

    steps = [
        ("fetch_sources.py", "Downloading data source repositories"),
        ("import_psrd.py",   "Importing PSRD-Data into SQLite"),
        ("query_test.py",    "Verifying database with sample queries"),
    ]

    for script_name, description in steps:
        if not run_script(script_name, description):
            print(f"\n⚠ Setup stopped at: {description}")
            print(f"  Fix the issue above and re-run: python scripts/setup.py")
            sys.exit(1)

    print(f"\n╔" + "═" * 58 + "╗")
    print(f"║   ✓ Setup Complete!                                      ║")
    print(f"║                                                          ║")
    print(f"║   Database: db/pf1e.db                                   ║")
    print(f"║   Test queries: python scripts/query_test.py             ║")
    print(f"╚" + "═" * 58 + "╝")


if __name__ == "__main__":
    main()
