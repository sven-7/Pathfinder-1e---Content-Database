from __future__ import annotations

from pathlib import Path


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_v2_router_mounts_character_and_campaign_domain_routes():
    router_file = _backend_root() / "app" / "api" / "v2" / "router.py"
    text = router_file.read_text(encoding="utf-8")
    assert "content_router" in text
    assert "characters_router" in text
    assert "rules_router" in text
    assert "campaigns_router" in text
    assert "parties_router" in text
    assert "sessions_router" in text
    assert 'prefix="/api/v2"' in text


def test_route_handlers_do_not_embed_sql():
    route_dir = _backend_root() / "app" / "api" / "v2"
    for route_file in ("content.py", "characters.py", "rules.py", "campaigns.py", "parties.py", "sessions.py"):
        text = (route_dir / route_file).read_text(encoding="utf-8").lower()
        assert "sqlite3" not in text
        assert "select " not in text
        assert "insert " not in text
        assert "update " not in text
        assert "delete " not in text


def test_contract_models_include_character_campaign_and_content_types():
    contracts_file = _backend_root() / "app" / "models" / "contracts.py"
    contracts_text = contracts_file.read_text(encoding="utf-8")
    for model_name in (
        "class CharacterV2(",
        "class CharacterValidationResponseV2(",
        "class DerivedStatsV2(",
        "class DeriveResponseV2(",
        "class ContentFeatV2(",
        "class ContentRaceV2(",
        "class PolicySummaryV2(",
    ):
        assert model_name in contracts_text

    campaign_file = _backend_root() / "app" / "models" / "campaigns_v1.py"
    campaign_text = campaign_file.read_text(encoding="utf-8")
    for model_name in (
        "class CampaignV1(",
        "class PartyV1(",
        "class PartyMemberV1(",
        "class SessionV1(",
        "class EncounterV1(",
        "class RuleOverrideRecordV1(",
        "class RuleOverrideResolutionV1(",
    ):
        assert model_name in campaign_text

