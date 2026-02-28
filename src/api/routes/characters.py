"""CRUD for saved characters — PostgreSQL storage with JWT ownership."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.api.models import Character, User
from src.api.pg_database import get_db

router = APIRouter(tags=["characters"])


def _char_summary(char: Character) -> dict:
    data = char.data or {}
    class_levels = data.get("class_levels", [])
    class_str = ", ".join(
        f"{cl['class_name']} {cl['level']}" for cl in class_levels
    )
    return {
        "id": str(char.id),
        "name": char.name,
        "player_name": data.get("player_name", ""),
        "race": data.get("race", ""),
        "class_str": class_str,
        "total_level": sum(cl["level"] for cl in class_levels),
        "modified_at": char.modified_at.isoformat() if char.modified_at else "",
    }


# ── List ─────────────────────────────────────────────────────────────────── #

@router.get("/characters")
async def list_characters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Character)
        .where(Character.user_id == current_user.id)
        .order_by(Character.modified_at.desc())
    )
    return [_char_summary(c) for c in result.scalars().all()]


# ── Create ───────────────────────────────────────────────────────────────── #

@router.post("/characters", status_code=201)
async def create_character(
    request: Request,
    char: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(tz=timezone.utc)
    char_id = char.get("id") or str(uuid.uuid4())
    char["id"] = char_id
    char.setdefault("created_at", now.isoformat())
    char["modified_at"] = now.isoformat()

    db_char = Character(
        id=uuid.UUID(char_id),
        user_id=current_user.id,
        name=char.get("name", "Unnamed"),
        data=char,
    )
    db.add(db_char)
    await db.commit()
    await db.refresh(db_char)
    return {"id": char_id, "name": db_char.name}


# ── Read ─────────────────────────────────────────────────────────────────── #

@router.get("/characters/{char_id}")
async def get_character(
    char_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = await _get_owned_char(char_id, current_user, db)
    return char.data


# ── Update ───────────────────────────────────────────────────────────────── #

@router.put("/characters/{char_id}")
async def update_character(
    char_id: str,
    char: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_char = await _get_owned_char(char_id, current_user, db)

    now = datetime.now(tz=timezone.utc)
    char["id"] = char_id
    char.setdefault("created_at", db_char.data.get("created_at", now.isoformat()))
    char["modified_at"] = now.isoformat()

    db_char.name = char.get("name", db_char.name)
    db_char.data = char
    db_char.modified_at = now

    await db.commit()
    return {"id": char_id, "name": db_char.name}


# ── Delete ───────────────────────────────────────────────────────────────── #

@router.delete("/characters/{char_id}", status_code=204)
async def delete_character(
    char_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_char = await _get_owned_char(char_id, current_user, db)
    await db.delete(db_char)
    await db.commit()
    return None


# ── Sheet HTML ───────────────────────────────────────────────────────────── #

@router.get("/characters/{char_id}/sheet", response_class=HTMLResponse)
async def get_character_sheet(
    char_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_char = await _get_owned_char(char_id, current_user, db)
    rules_db = request.app.state.db
    from src.character_creator.exporter import generate_sheet_html
    html = generate_sheet_html(db_char.data, rules_db)
    return HTMLResponse(content=html)


# ── Derive stats ─────────────────────────────────────────────────────────── #

@router.post("/characters/{char_id}/derive")
async def derive_stats(
    char_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_char = await _get_owned_char(char_id, current_user, db)
    rules_db = request.app.state.db
    from src.character_creator.exporter import _compute_derived
    return _compute_derived(db_char.data, rules_db)


# ── Helper ───────────────────────────────────────────────────────────────── #

async def _get_owned_char(char_id: str, user: User, db: AsyncSession) -> Character:
    """Fetch a character by ID and verify ownership. Raises 404/403."""
    try:
        char_uuid = uuid.UUID(char_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Character '{char_id}' not found")

    result = await db.execute(select(Character).where(Character.id == char_uuid))
    char = result.scalar_one_or_none()
    if char is None:
        raise HTTPException(status_code=404, detail=f"Character '{char_id}' not found")
    if char.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your character")
    return char
