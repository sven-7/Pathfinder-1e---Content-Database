from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import app.api.v2.content as content_api
from app.main import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_derive_kairon_slice_baseline():
    client = TestClient(app)

    payload = {
        "name": "Kairon",
        "race": "Tiefling",
        "alignment": "Lawful Neutral",
        "ability_scores": {
            "str": 12,
            "dex": 18,
            "con": 12,
            "int": 17,
            "wis": 18,
            "cha": 14,
        },
        "class_levels": [{"class_name": "Investigator", "level": 9}],
        "feats": [
            {"name": "Weapon Finesse", "level_gained": 1, "method": "general"},
            {"name": "Weapon Focus", "level_gained": 3, "method": "general"},
            {"name": "Rapid Shot", "level_gained": 5, "method": "general"},
        ],
        "traits": [
            {
                "name": "Reactionary",
                "category": "Combat",
                "effects": [{"key": "initiative", "delta": 2, "bonus_type": "trait", "source": "Reactionary"}],
            }
        ],
        "skills": {"Perception": 9},
        "equipment": [
            {"name": "Rapier", "kind": "weapon", "quantity": 1},
            {"name": "Studded Leather", "kind": "armor", "quantity": 1},
        ],
        "conditions": [],
    }

    response = client.post("/api/v2/rules/derive", json=payload)
    assert response.status_code == 200

    derived = response.json()["derived"]
    assert derived["total_level"] == 9
    assert derived["bab"] == 6
    assert derived["fort"] == 4
    assert derived["ref"] == 10
    assert derived["will"] == 10
    assert derived["hp_max"] == 57
    assert derived["ac_total"] == 17
    assert derived["ac_touch"] == 14
    assert derived["ac_flat_footed"] == 13
    assert derived["cmb"] == 7
    assert derived["cmd"] == 21
    assert derived["initiative"] == 6
    assert derived["spell_slots"] == {"1": 5, "2": 4, "3": 3}
    assert derived["skill_totals"]["Perception"] == 16
    assert derived["attack_lines"][0]["name"] == "Rapier"
    assert derived["attack_lines"][0]["attack_bonus"] == 11
    assert len(derived["breakdown"]) > 0
    assert any(line["key"] == "AC(total)" for line in derived["breakdown"])
    assert all(line["source"] for line in derived["breakdown"])

    feat_results = {item["feat_name"]: item for item in derived["feat_prereq_results"]}
    assert feat_results["Weapon Finesse"]["valid"] is True
    assert feat_results["Weapon Focus"]["valid"] is True
    assert feat_results["Rapid Shot"]["valid"] is False
    assert "Point-Blank Shot" in feat_results["Rapid Shot"]["missing"]


def test_character_validate_reports_invalid_feat_chain():
    client = TestClient(app)

    payload = {
        "name": "Kairon",
        "race": "Tiefling",
        "ability_scores": {"str": 12, "dex": 18, "con": 12, "int": 17, "wis": 18, "cha": 14},
        "class_levels": [{"class_name": "Investigator", "level": 9}],
        "feats": [
            {"name": "Rapid Shot", "level_gained": 5, "method": "general"},
        ],
        "traits": [],
        "skills": {},
        "equipment": [{"name": "Rapier", "kind": "weapon", "quantity": 1}],
        "conditions": [],
    }

    response = client.post("/api/v2/characters/validate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["invalid_feats"][0]["feat_name"] == "Rapid Shot"
    assert "Point-Blank Shot" in body["invalid_feats"][0]["missing"]


def test_content_endpoints_filter_deferred_by_default(tmp_path: "Path", monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "content.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE source_records (
              id INTEGER PRIMARY KEY,
              ui_enabled INTEGER NOT NULL,
              ui_tier TEXT NOT NULL,
              policy_reason TEXT NOT NULL
            );
            CREATE TABLE feats (
              id INTEGER PRIMARY KEY,
              name TEXT,
              feat_type TEXT,
              prerequisites TEXT,
              benefit TEXT,
              source_book TEXT,
              source_record_id INTEGER
            );
            CREATE TABLE races (
              id INTEGER PRIMARY KEY,
              name TEXT,
              race_type TEXT,
              size TEXT,
              base_speed INTEGER,
              source_book TEXT,
              source_record_id INTEGER
            );
            """
        )
        conn.execute("INSERT INTO source_records (id, ui_enabled, ui_tier, policy_reason) VALUES (1, 1, 'active', 'allowlisted')")
        conn.execute("INSERT INTO source_records (id, ui_enabled, ui_tier, policy_reason) VALUES (2, 0, 'deferred', 'book_not_in_allowlist')")
        conn.execute(
            "INSERT INTO feats (id, name, feat_type, prerequisites, benefit, source_book, source_record_id) VALUES (1, 'Power Attack', 'combat', '', '', 'Core Rulebook', 1)"
        )
        conn.execute(
            "INSERT INTO feats (id, name, feat_type, prerequisites, benefit, source_book, source_record_id) VALUES (2, 'Psionic Focus', 'general', '', '', 'Occult Adventures', 2)"
        )
        conn.execute(
            "INSERT INTO races (id, name, race_type, size, base_speed, source_book, source_record_id) VALUES (1, 'Human', 'featured', 'Medium', 30, 'Core Rulebook', 1)"
        )
        conn.execute(
            "INSERT INTO races (id, name, race_type, size, base_speed, source_book, source_record_id) VALUES (2, 'Aasimar', 'featured', 'Medium', 30, 'Blood of Angels', 2)"
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(content_api, "settings", SimpleNamespace(database_url=f"sqlite:///{db_path}"))

    client = TestClient(app)

    feats_default = client.get("/api/v2/content/feats")
    assert feats_default.status_code == 200
    assert [r["name"] for r in feats_default.json()] == ["Power Attack"]
    assert "ui_enabled" not in feats_default.json()[0]

    races_default = client.get("/api/v2/content/races")
    assert races_default.status_code == 200
    assert [r["name"] for r in races_default.json()] == ["Human"]


def test_content_endpoints_include_deferred_with_policy_metadata(tmp_path: "Path", monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "content_with_deferred.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE source_records (
              id INTEGER PRIMARY KEY,
              ui_enabled INTEGER NOT NULL,
              ui_tier TEXT NOT NULL,
              policy_reason TEXT NOT NULL
            );
            CREATE TABLE feats (
              id INTEGER PRIMARY KEY,
              name TEXT,
              feat_type TEXT,
              prerequisites TEXT,
              benefit TEXT,
              source_book TEXT,
              source_record_id INTEGER
            );
            """
        )
        conn.execute("INSERT INTO source_records (id, ui_enabled, ui_tier, policy_reason) VALUES (1, 1, 'active', 'allowlisted')")
        conn.execute("INSERT INTO source_records (id, ui_enabled, ui_tier, policy_reason) VALUES (2, 0, 'deferred', 'book_not_in_allowlist')")
        conn.execute(
            "INSERT INTO feats (id, name, feat_type, prerequisites, benefit, source_book, source_record_id) VALUES (1, 'Power Attack', 'combat', '', '', 'Core Rulebook', 1)"
        )
        conn.execute(
            "INSERT INTO feats (id, name, feat_type, prerequisites, benefit, source_book, source_record_id) VALUES (2, 'Psionic Focus', 'general', '', '', 'Occult Adventures', 2)"
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(content_api, "settings", SimpleNamespace(database_url=f"sqlite:///{db_path}"))

    client = TestClient(app)
    feats = client.get("/api/v2/content/feats?include_deferred=true")
    assert feats.status_code == 200
    body = feats.json()
    assert [row["name"] for row in body] == ["Power Attack", "Psionic Focus"]
    deferred = next(row for row in body if row["name"] == "Psionic Focus")
    assert deferred["ui_enabled"] == 0
    assert deferred["ui_tier"] == "deferred"
    assert deferred["policy_reason"] == "book_not_in_allowlist"


def test_content_policy_summary_endpoint(tmp_path: "Path", monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "content_summary.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE source_records (
              id INTEGER PRIMARY KEY,
              parse_status TEXT,
              ui_enabled INTEGER NOT NULL,
              ui_tier TEXT NOT NULL,
              policy_reason TEXT NOT NULL
            );
            """
        )
        conn.execute("INSERT INTO source_records (id, parse_status, ui_enabled, ui_tier, policy_reason) VALUES (1, 'accepted', 1, 'active', 'allowlisted')")
        conn.execute("INSERT INTO source_records (id, parse_status, ui_enabled, ui_tier, policy_reason) VALUES (2, 'accepted', 0, 'deferred', 'book_not_in_allowlist')")
        conn.execute("INSERT INTO source_records (id, parse_status, ui_enabled, ui_tier, policy_reason) VALUES (3, 'accepted', 0, 'deferred', 'book_not_in_allowlist')")
        conn.execute("INSERT INTO source_records (id, parse_status, ui_enabled, ui_tier, policy_reason) VALUES (4, 'rejected', 0, 'deferred', 'class_not_in_allowlist')")
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(content_api, "settings", SimpleNamespace(database_url=f"sqlite:///{db_path}"))

    client = TestClient(app)
    response = client.get("/api/v2/content/policy-summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_total"] == 3
    assert payload["active_total"] == 1
    assert payload["deferred_total"] == 2
    assert payload["tier_counts"]["active"] == 1
    assert payload["tier_counts"]["deferred"] == 2
    assert payload["reason_counts"]["book_not_in_allowlist"] == 2
    assert payload["reason_counts"]["allowlisted"] == 1
    assert "class_not_in_allowlist" not in payload["reason_counts"]


def test_openapi_exposes_v2_paths_and_contract_schemas():
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()

    assert "/api/v2/content/feats" in payload["paths"]
    assert "/api/v2/content/races" in payload["paths"]
    assert "/api/v2/content/policy-summary" in payload["paths"]
    assert "/api/v2/characters/validate" in payload["paths"]
    assert "/api/v2/rules/derive" in payload["paths"]
    assert "/api/v2/campaigns" in payload["paths"]
    assert "/api/v2/parties" in payload["paths"]
    assert "/api/v2/sessions" in payload["paths"]

    schemas = payload["components"]["schemas"]
    for expected in (
        "CharacterV2",
        "DerivedStatsV2",
        "DeriveResponseV2",
        "CharacterValidationResponseV2",
        "ContentFeatV2",
        "ContentRaceV2",
        "PolicySummaryV2",
        "CampaignV1",
        "PartyV1",
        "SessionV1",
        "EncounterV1",
        "RuleOverrideRecordV1",
        "RuleOverrideResolutionV1",
    ):
        assert expected in schemas

    derive_post = payload["paths"]["/api/v2/rules/derive"]["post"]
    derive_examples = derive_post["requestBody"]["content"]["application/json"]["examples"]
    assert "kairon" in derive_examples
    assert derive_examples["kairon"]["value"]["name"] == "Kairon"

    validate_post = payload["paths"]["/api/v2/characters/validate"]["post"]
    validate_examples = validate_post["requestBody"]["content"]["application/json"]["examples"]
    assert "kairon" in validate_examples
    assert validate_examples["kairon"]["value"]["race"] == "Tiefling"


def test_route_handlers_do_not_contain_sql_literals():
    route_dir = Path(__file__).resolve().parents[1] / "app" / "api" / "v2"
    for route_file in ("content.py", "characters.py", "rules.py"):
        text = (route_dir / route_file).read_text(encoding="utf-8").lower()
        assert "sqlite3" not in text
        assert "select " not in text
        assert "insert " not in text
        assert "update " not in text
        assert "delete " not in text
