from __future__ import annotations

from pathlib import Path


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_v2_router_mounts_character_domain_routes():
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


def test_contract_models_include_character_and_derived_stats_v2():
    contracts_file = _backend_root() / "app" / "models" / "contracts.py"
    text = contracts_file.read_text(encoding="utf-8")
    for model_name in (
        "class CharacterV2(",
        "class DerivedStatsV2(",
        "class DeriveResponseV2(",
        "class CharacterValidationResponseV2(",
        "class ContentFeatV2(",
        "class ContentRaceV2(",
        "class PolicySummaryV2(",
    ):
        assert model_name in text


def test_openapi_doc_includes_examples_and_curl_calls():
    docs_file = _backend_root() / "docs" / "api_v2.md"
    text = docs_file.read_text(encoding="utf-8")
    assert "/openapi.json" in text
    assert "/api/v2/characters/validate" in text
    assert "/api/v2/rules/derive" in text
    assert "/api/v2/campaigns" in text
    assert "/api/v2/parties" in text
    assert "/api/v2/sessions" in text
    assert "curl -sS -X POST" in text


def test_campaign_contract_models_exist():
    contracts_file = _backend_root() / "app" / "models" / "campaigns_v1.py"
    text = contracts_file.read_text(encoding="utf-8")
    for model_name in (
        "class CampaignV1(",
        "class PartyV1(",
        "class PartyMemberV1(",
        "class SessionV1(",
        "class EncounterV1(",
        "class RuleOverrideRecordV1(",
        "class RuleOverrideResolutionV1(",
    ):
        assert model_name in text
