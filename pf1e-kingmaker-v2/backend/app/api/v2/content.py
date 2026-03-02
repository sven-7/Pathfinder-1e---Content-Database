"""Content API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.config import settings
from app.models.contracts import ContentFeatV2, ContentRaceV2, PolicySummaryV2
from app.repositories.content_v2 import ContentRepositoryV2
from app.services.content_v2 import ContentServiceV2

router = APIRouter(prefix="/content", tags=["content-v2"])


def get_content_service() -> ContentServiceV2:
    return ContentServiceV2(ContentRepositoryV2(settings.database_url))


@router.get("/feats", response_model=list[ContentFeatV2], response_model_exclude_none=True)
def list_feats(
    _: Request,
    include_deferred: bool = Query(default=False, description="Include deferred content rows with policy metadata."),
    service: ContentServiceV2 = Depends(get_content_service),
) -> list[ContentFeatV2]:
    return service.list_feats(include_deferred=include_deferred)


@router.get("/races", response_model=list[ContentRaceV2], response_model_exclude_none=True)
def list_races(
    _: Request,
    include_deferred: bool = Query(default=False, description="Include deferred content rows with policy metadata."),
    service: ContentServiceV2 = Depends(get_content_service),
) -> list[ContentRaceV2]:
    return service.list_races(include_deferred=include_deferred)


@router.get("/policy-summary", response_model=PolicySummaryV2)
def policy_summary(_: Request, service: ContentServiceV2 = Depends(get_content_service)) -> PolicySummaryV2:
    return service.policy_summary()
