"""Service layer for API V2 content endpoints."""

from __future__ import annotations

from app.models.contracts import ContentFeatV2, ContentRaceV2, PolicySummaryV2
from app.repositories.content_v2 import ContentRepositoryV2


class ContentServiceV2:
    """Typed content service for API V2 routes."""

    def __init__(self, repository: ContentRepositoryV2):
        self._repository = repository

    def list_feats(self, *, include_deferred: bool) -> list[ContentFeatV2]:
        rows = self._repository.list_feats(include_deferred=include_deferred)
        return [ContentFeatV2.model_validate(row) for row in rows]

    def list_races(self, *, include_deferred: bool) -> list[ContentRaceV2]:
        rows = self._repository.list_races(include_deferred=include_deferred)
        return [ContentRaceV2.model_validate(row) for row in rows]

    def policy_summary(self) -> PolicySummaryV2:
        row = self._repository.policy_summary()
        return PolicySummaryV2.model_validate(row)

