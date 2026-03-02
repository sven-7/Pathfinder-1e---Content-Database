from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from app.models.campaigns_v1 import CampaignCreateV1, RuleOverrideCreateV1
from app.repositories.campaigns_v1 import CampaignRepositoryV1
from app.services.campaigns_v1 import CampaignServiceV1


def test_override_precedence_is_global_then_campaign_then_character() -> None:
    repo = CampaignRepositoryV1()
    service = CampaignServiceV1(repo)

    campaign = service.create_campaign(CampaignCreateV1(name="Test Campaign", owner_id="owner-a"))

    service.create_global_override(
        RuleOverrideCreateV1(key="ac_total", operation="add", value=1, source="global-ac")
    )
    service.create_campaign_override(
        campaign.id,
        RuleOverrideCreateV1(key="ac_total", operation="set", value=15, source="campaign-ac"),
    )
    service.create_campaign_override(
        campaign.id,
        RuleOverrideCreateV1(
            key="ac_total",
            operation="add",
            value=3,
            source="character-ac",
            character_id="char-1",
        ),
    )

    without_character = service.resolve_overrides(campaign.id)
    assert without_character.effective_values["ac_total"] == 15
    assert [row.scope for row in without_character.ordered_overrides] == ["global", "campaign"]

    with_character = service.resolve_overrides(campaign.id, character_id="char-1")
    assert with_character.effective_values["ac_total"] == 18
    assert [row.scope for row in with_character.ordered_overrides] == ["global", "campaign", "character"]


def test_override_merge_is_deterministic_with_multiple_keys() -> None:
    repo = CampaignRepositoryV1()
    service = CampaignServiceV1(repo)
    campaign = service.create_campaign(CampaignCreateV1(name="Deterministic", owner_id="owner-a"))

    service.create_global_override(RuleOverrideCreateV1(key="hp_max", operation="add", value=2, source="g1"))
    service.create_global_override(RuleOverrideCreateV1(key="hp_max", operation="add", value=3, source="g2"))
    service.create_campaign_override(campaign.id, RuleOverrideCreateV1(key="hp_max", operation="set", value=20, source="c1"))
    service.create_campaign_override(campaign.id, RuleOverrideCreateV1(key="initiative", operation="add", value=1, source="c2"))
    service.create_campaign_override(
        campaign.id,
        RuleOverrideCreateV1(
            key="initiative",
            operation="add",
            value=2,
            source="char-init",
            character_id="char-2",
        ),
    )

    resolved = service.resolve_overrides(campaign.id, character_id="char-2")
    assert resolved.effective_values == {"hp_max": 20, "initiative": 3}
