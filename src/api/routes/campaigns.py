"""Campaign CRUD + party overview — PostgreSQL with JWT auth."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_user
from src.api.models import Campaign, CampaignMember, Character, User
from src.api.pg_database import get_db

router = APIRouter(tags=["campaigns"])


# ── Helpers ─────────────────────────────────────────────────────────────── #

async def _get_campaign(campaign_id: str, db: AsyncSession) -> Campaign:
    """Fetch a campaign by ID. Raises 404 if not found."""
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Campaign not found")
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.members).selectinload(CampaignMember.user))
        .where(Campaign.id == cid)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _require_gm(campaign: Campaign, user: User) -> None:
    """Raise 403 if the user is not the campaign's GM."""
    if campaign.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the GM can do this")


def _is_member(campaign: Campaign, user: User) -> bool:
    """Check if a user is a member (GM or player) of the campaign."""
    if campaign.gm_user_id == user.id:
        return True
    return any(m.user_id == user.id for m in campaign.members)


def _require_member(campaign: Campaign, user: User) -> None:
    """Raise 403 if the user is not a member of the campaign."""
    if not _is_member(campaign, user):
        raise HTTPException(status_code=403, detail="Not a member of this campaign")


def _campaign_summary(campaign: Campaign) -> dict:
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "gm_user_id": str(campaign.gm_user_id),
        "gm_username": campaign.gm.username if hasattr(campaign, "gm") and campaign.gm else None,
        "member_count": len(campaign.members) if campaign.members else 0,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else "",
    }


def _char_party_summary(char: Character) -> dict:
    """Compact character summary for party overview."""
    data = char.data or {}
    class_levels = data.get("class_levels", [])
    class_str = ", ".join(
        f"{cl['class_name']} {cl['level']}" for cl in class_levels
    )
    ability_scores = data.get("ability_scores", {})
    return {
        "id": str(char.id),
        "user_id": str(char.user_id),
        "name": char.name,
        "race": data.get("race", ""),
        "class_str": class_str,
        "total_level": sum(cl["level"] for cl in class_levels),
        "hp_max": data.get("hp_max", 0),
        "ability_scores": ability_scores,
    }


# ── Create Campaign ────────────────────────────────────────────────────── #

@router.post("/campaigns", status_code=201)
async def create_campaign(
    body: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Campaign name is required")

    campaign = Campaign(name=name, gm_user_id=current_user.id)
    db.add(campaign)
    await db.flush()

    # GM is automatically a member with role 'gm'
    gm_member = CampaignMember(
        campaign_id=campaign.id, user_id=current_user.id, role="gm"
    )
    db.add(gm_member)
    await db.commit()
    await db.refresh(campaign)
    return {"id": str(campaign.id), "name": campaign.name}


# ── List Campaigns ──────────────────────────────────────────────────────── #

@router.get("/campaigns")
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all campaigns the user belongs to (as GM or player)."""
    result = await db.execute(
        select(Campaign)
        .join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .options(
            selectinload(Campaign.members),
            selectinload(Campaign.gm),
        )
        .where(CampaignMember.user_id == current_user.id)
        .order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().unique().all()
    return [_campaign_summary(c) for c in campaigns]


# ── Get Campaign Detail ─────────────────────────────────────────────────── #

@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(campaign_id, db)
    _require_member(campaign, current_user)

    # Eagerly load GM username
    gm_result = await db.execute(select(User).where(User.id == campaign.gm_user_id))
    gm = gm_result.scalar_one_or_none()

    members = []
    for m in campaign.members:
        members.append({
            "user_id": str(m.user_id),
            "username": m.user.username if m.user else "Unknown",
            "role": m.role,
            "joined_at": m.joined_at.isoformat() if m.joined_at else "",
        })

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "gm_user_id": str(campaign.gm_user_id),
        "gm_username": gm.username if gm else "Unknown",
        "is_gm": campaign.gm_user_id == current_user.id,
        "members": members,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else "",
    }


# ── Add Member ──────────────────────────────────────────────────────────── #

@router.post("/campaigns/{campaign_id}/members", status_code=201)
async def add_member(
    campaign_id: str,
    body: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(campaign_id, db)
    _require_gm(campaign, current_user)

    username = body.get("username", "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    # Find the user by username
    result = await db.execute(select(User).where(User.username == username))
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    # Check if already a member
    if any(m.user_id == target_user.id for m in campaign.members):
        raise HTTPException(status_code=409, detail=f"'{username}' is already in this campaign")

    member = CampaignMember(
        campaign_id=campaign.id, user_id=target_user.id, role="player"
    )
    db.add(member)
    await db.commit()
    return {"user_id": str(target_user.id), "username": target_user.username, "role": "player"}


# ── Remove Member ───────────────────────────────────────────────────────── #

@router.delete("/campaigns/{campaign_id}/members/{user_id}", status_code=204)
async def remove_member(
    campaign_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(campaign_id, db)
    _require_gm(campaign, current_user)

    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    # Cannot remove the GM
    if target_uuid == campaign.gm_user_id:
        raise HTTPException(status_code=400, detail="Cannot remove the GM from their own campaign")

    result = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.user_id == target_uuid,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found in campaign")

    await db.delete(member)
    await db.commit()
    return None


# ── Party Overview ──────────────────────────────────────────────────────── #

@router.get("/campaigns/{campaign_id}/party")
async def get_party(
    campaign_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Party overview: all characters belonging to campaign members."""
    campaign = await _get_campaign(campaign_id, db)
    _require_member(campaign, current_user)

    # Get all member user IDs
    member_user_ids = [m.user_id for m in campaign.members]

    # Fetch all characters belonging to campaign members
    result = await db.execute(
        select(Character)
        .where(Character.user_id.in_(member_user_ids))
        .order_by(Character.name)
    )
    characters = result.scalars().all()

    # Build username lookup
    username_map = {m.user_id: m.user.username for m in campaign.members if m.user}

    # Compute derived stats for each character
    rules_db = request.app.state.db
    from src.character_creator.exporter import _compute_derived

    party = []
    for char in characters:
        summary = _char_party_summary(char)
        summary["player_username"] = username_map.get(char.user_id, "Unknown")
        try:
            derived = _compute_derived(char.data, rules_db)
            summary["hp_max"] = derived.get("hp", summary["hp_max"])
            summary["ac"] = derived.get("ac", {}).get("total", 10)
            summary["initiative"] = derived.get("initiative", 0)
            summary["saves"] = {
                "fort": derived.get("saves", {}).get("fort", 0),
                "ref": derived.get("saves", {}).get("ref", 0),
                "will": derived.get("saves", {}).get("will", 0),
            }
        except Exception:
            summary["ac"] = 10
            summary["initiative"] = 0
            summary["saves"] = {"fort": 0, "ref": 0, "will": 0}
        party.append(summary)

    return party


# ── GM View Character Sheet ─────────────────────────────────────────────── #

@router.get("/campaigns/{campaign_id}/characters/{char_id}/sheet", response_class=HTMLResponse)
async def gm_view_character_sheet(
    campaign_id: str,
    char_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GM can view any character sheet belonging to a campaign member."""
    campaign = await _get_campaign(campaign_id, db)
    _require_member(campaign, current_user)

    try:
        char_uuid = uuid.UUID(char_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Character not found")

    result = await db.execute(select(Character).where(Character.id == char_uuid))
    char = result.scalar_one_or_none()
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")

    # Verify the character belongs to a campaign member
    member_user_ids = {m.user_id for m in campaign.members}
    if char.user_id not in member_user_ids:
        raise HTTPException(status_code=403, detail="Character does not belong to a campaign member")

    rules_db = request.app.state.db
    from src.character_creator.exporter import generate_sheet_html
    html = generate_sheet_html(char.data, rules_db)
    return HTMLResponse(content=html)


# ── Delete Campaign ─────────────────────────────────────────────────────── #

@router.delete("/campaigns/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(campaign_id, db)
    _require_gm(campaign, current_user)
    await db.delete(campaign)
    await db.commit()
    return None
