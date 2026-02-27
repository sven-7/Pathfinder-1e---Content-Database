"""CRUD for saved characters — JSON file storage in characters/."""

from __future__ import annotations

import json
import pathlib
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse

ROOT = pathlib.Path(__file__).parent.parent.parent.parent
CHARS_DIR = ROOT / "characters"

router = APIRouter(tags=["characters"])


def _char_path(char_id: str) -> pathlib.Path:
    return CHARS_DIR / f"{char_id}.json"


def _load_char(char_id: str) -> dict:
    path = _char_path(char_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Character '{char_id}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _char_summary(char: dict) -> dict:
    class_levels = char.get("class_levels", [])
    class_str = ", ".join(
        f"{cl['class_name']} {cl['level']}" for cl in class_levels
    )
    return {
        "id": char.get("id", ""),
        "name": char.get("name", "Unnamed"),
        "player_name": char.get("player_name", ""),
        "race": char.get("race", ""),
        "class_str": class_str,
        "total_level": sum(cl["level"] for cl in class_levels),
        "modified_at": char.get("modified_at", ""),
    }


@router.get("/characters")
async def list_characters():
    CHARS_DIR.mkdir(exist_ok=True)
    chars = []
    for path in sorted(CHARS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            chars.append(_char_summary(data))
        except Exception:
            continue
    return chars


@router.post("/characters", status_code=201)
async def create_character(request: Request, char: dict = Body(...)):
    CHARS_DIR.mkdir(exist_ok=True)
    db = request.app.state.db

    # Assign an ID if missing
    if "id" not in char or not char["id"]:
        char["id"] = str(uuid.uuid4())
    char["created_at"] = datetime.utcnow().isoformat()
    char["modified_at"] = char["created_at"]

    path = _char_path(char["id"])
    path.write_text(json.dumps(char, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"id": char["id"], "name": char.get("name", "Unnamed")}


@router.get("/characters/{char_id}")
async def get_character(char_id: str):
    return _load_char(char_id)


@router.put("/characters/{char_id}")
async def update_character(char_id: str, char: dict = Body(...)):
    existing = _load_char(char_id)
    char["id"] = char_id
    char["created_at"] = existing.get("created_at", datetime.utcnow().isoformat())
    char["modified_at"] = datetime.utcnow().isoformat()
    path = _char_path(char_id)
    path.write_text(json.dumps(char, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"id": char_id, "name": char.get("name", "Unnamed")}


@router.delete("/characters/{char_id}", status_code=204)
async def delete_character(char_id: str):
    path = _char_path(char_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Character '{char_id}' not found")
    path.unlink()
    return None


@router.get("/characters/{char_id}/sheet", response_class=HTMLResponse)
async def get_character_sheet(char_id: str, request: Request):
    """Return a standalone HTML character sheet for this character."""
    db = request.app.state.db
    char = _load_char(char_id)
    from src.character_creator.exporter import generate_sheet_html
    html = generate_sheet_html(char, db)
    return HTMLResponse(content=html)


@router.post("/characters/{char_id}/derive")
async def derive_stats(char_id: str, request: Request):
    """Return derived stats for a character."""
    db = request.app.state.db
    char = _load_char(char_id)
    from src.character_creator.exporter import _compute_derived
    return _compute_derived(char, db)
