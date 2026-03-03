"""Top-level API v2 router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v2.campaigns import router as campaigns_router
from app.api.v2.characters import router as characters_router
from app.api.v2.content import router as content_router
from app.api.v2.parties import router as parties_router
from app.api.v2.rules import router as rules_router
from app.api.v2.sessions import router as sessions_router

router = APIRouter(prefix="/api/v2")
router.include_router(content_router)
router.include_router(characters_router)
router.include_router(rules_router)
router.include_router(campaigns_router)
router.include_router(parties_router)
router.include_router(sessions_router)

