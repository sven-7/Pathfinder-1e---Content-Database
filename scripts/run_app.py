#!/usr/bin/env python3
"""Launch the PF1e Character Creator web app.

Usage:
    python scripts/run_app.py
"""

import os
import pathlib
import sys
import threading
import webbrowser

# Add project root to Python path so 'src' is importable
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402 (must come after sys.path manipulation)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _open_browser():
    webbrowser.open(URL)


if __name__ == "__main__":
    print(f"\n  PF1e Character Creator")
    print(f"  ─────────────────────────────────")
    print(f"  Opening browser at {URL}")
    print(f"  Press Ctrl+C to stop\n")

    threading.Timer(1.2, _open_browser).start()
    uvicorn.run(
        "src.api.app:app",
        host=HOST,
        port=PORT,
        reload=True,
        reload_dirs=[str(ROOT / "src")],
    )
