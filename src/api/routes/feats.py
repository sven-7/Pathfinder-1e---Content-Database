"""GET /api/feats — feat listing with optional prerequisite filtering."""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["feats"])

# Feat types excluded from character creation by default
_NON_PLAYER_TYPES = {"monster", "mythic", "mythic path ability", "item (invalid)"}


@router.get("/feats")
async def list_feats(
    request: Request,
    available_for: str | None = Query(default=None, description="Base64-encoded character JSON"),
    feat_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    include_all: bool = Query(default=False, description="Include monster/mythic/invalid feats"),
    paizo_only: bool = Query(default=True, description="Exclude 3pp content"),
):
    db = request.app.state.db
    rows = db.get_all_feats()

    # Exclude non-player feat types by default
    if not include_all:
        rows = [r for r in rows if (r.get("feat_type") or "").lower() not in _NON_PLAYER_TYPES]

    # Exclude 3pp content
    if paizo_only:
        rows = [r for r in rows if r.get("is_paizo_official", 1)]

    # Filter by type
    if feat_type:
        rows = [r for r in rows if (r.get("feat_type") or "").lower() == feat_type.lower()]

    # Filter by search
    if search:
        s = search.lower()
        rows = [r for r in rows if s in r["name"].lower() or s in (r.get("benefit") or "").lower()]

    # Filter by character prerequisites
    if available_for:
        try:
            char_json = base64.b64decode(available_for).decode("utf-8")
            char_data = json.loads(char_json)
            from src.rules_engine import Character, ClassLevel, check_prerequisites
            char = Character(
                name=char_data.get("name", ""),
                race=char_data.get("race", ""),
                alignment=char_data.get("alignment", ""),
                ability_scores=char_data.get("ability_scores", {}),
                class_levels=[ClassLevel.from_dict(cl) for cl in char_data.get("class_levels", [])],
                feats=char_data.get("feats", []),
                traits=char_data.get("traits", []),
                skills=char_data.get("skills", {}),
                equipment=char_data.get("equipment", []),
                conditions=char_data.get("conditions", []),
            )
            filtered = []
            for feat in rows:
                prereqs = feat.get("prerequisites") or ""
                if not prereqs or prereqs.strip() in ("—", "-", "None", ""):
                    filtered.append(feat)
                    continue
                result = check_prerequisites(prereqs, char, db)
                if result.met:
                    filtered.append(feat)
            rows = filtered
        except Exception:
            pass  # If decoding fails, return all feats

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "feat_type": r.get("feat_type") or "General",
            "prerequisites": r.get("prerequisites") or "",
            "benefit": r.get("benefit") or "",
            "description": r.get("description") or "",
        }
        for r in rows
    ]
