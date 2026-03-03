from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import app.pipeline.extract as extract_module
from app.pipeline.extract import run_extract
from app.pipeline.load import run_load
from app.pipeline.parse import run_parse
from app.pipeline.utils import read_json, read_jsonl
from app.pipeline.validate import run_validate


def test_extract_is_deterministic(tmp_path: Path):
    run_dir = tmp_path / "runs"

    run_a = run_extract(source="psrd", run_dir=run_dir, run_key="run_a")
    run_b = run_extract(source="psrd", run_dir=run_dir, run_key="run_b")

    rows_a = read_jsonl(run_a / "raw" / "source_records.jsonl")
    rows_b = read_jsonl(run_b / "raw" / "source_records.jsonl")

    hashes_a = sorted(r["raw_hash"] for r in rows_a)
    hashes_b = sorted(r["raw_hash"] for r in rows_b)

    assert hashes_a == hashes_b


def test_validation_rejects_junk_feats(tmp_path: Path):
    run_dir = tmp_path / "runs"
    input_path = tmp_path / "records.json"

    records = [
        {
            "content_type": "race",
            "source_url": "https://example/race",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"name": "Tiefling", "race_type": "featured", "size": "Medium", "base_speed": 30},
        },
        {
            "content_type": "racial_trait",
            "source_url": "https://example/race",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"race_name": "Tiefling", "name": "Darkvision", "trait_type": "senses"},
        },
        {
            "content_type": "feat",
            "source_url": "https://example/feat",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"name": "Feat Name", "feat_type": "general"},
        },
    ]
    input_path.write_text(json.dumps(records), encoding="utf-8")

    run = run_extract(source="psrd", run_dir=run_dir, input_path=input_path, run_key="junk_run")
    run_parse(run)
    run_validate(run)

    rejected = read_jsonl(run / "validation" / "rejected_records.jsonl")
    reasons = [r.get("reject_reason", "") for r in rejected]
    assert any("junk feat" in reason for reason in reasons)


def test_validation_rejects_non_allowlisted_class_rows(tmp_path: Path):
    run_dir = tmp_path / "runs"
    input_path = tmp_path / "records_bad_class.json"

    records = [
        {
            "content_type": "class",
            "source_url": "https://example/class",
            "source_book": "Unknown",
            "license_tag": "OGL",
            "payload": {
                "name": "Archives of Nethys",
                "class_type": "base",
                "hit_die": "d8",
                "skill_ranks_per_level": 4,
                "bab_progression": "three_quarter",
                "fort_progression": "good",
                "ref_progression": "good",
                "will_progression": "poor",
            },
        },
        {
            "content_type": "class_progression",
            "source_url": "https://example/class",
            "source_book": "Unknown",
            "license_tag": "OGL",
            "payload": {
                "class_name": "Archives of Nethys",
                "level": 1,
                "bab": 0,
                "fort_save": 2,
                "ref_save": 2,
                "will_save": 0,
            },
        },
    ]
    input_path.write_text(json.dumps(records), encoding="utf-8")

    run = run_extract(source="psrd", run_dir=run_dir, input_path=input_path, run_key="bad_class_gate")
    run_parse(run)
    run_validate(run)

    rejected = read_jsonl(run / "validation" / "rejected_records.jsonl")
    reasons = [str(r.get("reject_reason", "")) for r in rejected]
    assert any("class not approved: Archives of Nethys" in reason for reason in reasons)


def test_load_populates_canonical_tables(tmp_path: Path):
    run_dir = tmp_path / "runs"
    run = run_extract(source="psrd", run_dir=run_dir, run_key="load_run")
    run_parse(run)
    run_validate(run)

    dsn = f"sqlite:///{tmp_path / 'v2.db'}"
    result = run_load(run, dsn)

    assert result["inserted_records"] > 0

    conn = sqlite3.connect(str(tmp_path / "v2.db"))
    try:
        feat_count = conn.execute("SELECT COUNT(*) FROM feats").fetchone()[0]
        race_trait_count = conn.execute("SELECT COUNT(*) FROM racial_traits").fetchone()[0]
        assert feat_count >= 3
        assert race_trait_count >= 1
    finally:
        conn.close()


def test_validation_requires_required_entities(tmp_path: Path):
    run_dir = tmp_path / "runs"
    input_path = tmp_path / "records_missing_feat.json"

    records = [
        {
            "content_type": "class",
            "source_url": "https://example/class",
            "source_book": "Advanced Class Guide",
            "license_tag": "OGL",
            "payload": {
                "name": "Investigator",
                "class_type": "hybrid",
                "hit_die": "d8",
                "skill_ranks_per_level": 6,
                "bab_progression": "three_quarter",
                "fort_progression": "poor",
                "ref_progression": "good",
                "will_progression": "good",
            },
        },
        {
            "content_type": "class_progression",
            "source_url": "https://example/class",
            "source_book": "Advanced Class Guide",
            "license_tag": "OGL",
            "payload": {
                "class_name": "Investigator",
                "level": 9,
                "bab": 6,
                "fort_save": 3,
                "ref_save": 6,
                "will_save": 6,
            },
        },
        {
            "content_type": "race",
            "source_url": "https://example/race",
            "source_book": "Advanced Race Guide",
            "license_tag": "OGL",
            "payload": {"name": "Tiefling", "race_type": "featured", "size": "Medium", "base_speed": 30},
        },
        {
            "content_type": "racial_trait",
            "source_url": "https://example/race",
            "source_book": "Advanced Race Guide",
            "license_tag": "OGL",
            "payload": {"race_name": "Tiefling", "name": "Darkvision", "trait_type": "senses"},
        },
        {
            "content_type": "feat",
            "source_url": "https://example/feat",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"name": "Weapon Finesse", "feat_type": "combat"},
        },
        {
            "content_type": "feat",
            "source_url": "https://example/feat",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"name": "Weapon Focus", "feat_type": "combat"},
        },
        {
            "content_type": "trait",
            "source_url": "https://example/trait",
            "source_book": "Ultimate Campaign",
            "license_tag": "OGL",
            "payload": {"name": "Reactionary", "trait_type": "combat"},
        },
        {
            "content_type": "spell",
            "source_url": "https://example/spell",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"name": "Haste"},
        },
        {
            "content_type": "spell_class_level",
            "source_url": "https://example/spell",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"spell_name": "Haste", "class_name": "Investigator", "level": 3},
        },
        {
            "content_type": "equipment",
            "source_url": "https://example/equipment",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"name": "Rapier", "equipment_type": "weapon"},
        },
        {
            "content_type": "weapon",
            "source_url": "https://example/equipment",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"equipment_name": "Rapier", "damage_medium": "1d6"},
        },
        {
            "content_type": "equipment",
            "source_url": "https://example/equipment",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"name": "Studded Leather", "equipment_type": "armor"},
        },
        {
            "content_type": "armor",
            "source_url": "https://example/equipment",
            "source_book": "Core Rulebook",
            "license_tag": "OGL",
            "payload": {"equipment_name": "Studded Leather", "armor_bonus": 3},
        },
    ]
    input_path.write_text(json.dumps(records), encoding="utf-8")

    run = run_extract(source="psrd", run_dir=run_dir, input_path=input_path, run_key="required_gate")
    run_parse(run)
    run_validate(run)

    rejected = read_jsonl(run / "validation" / "rejected_records.jsonl")
    reasons = [str(r.get("reject_reason", "")) for r in rejected]
    assert any("missing required feat: rapid shot" in reason for reason in reasons)


def test_extract_kairon_slice_from_psrd_if_available(tmp_path: Path):
    workspace_root = Path(__file__).resolve().parents[3]
    psrd_root = workspace_root / "data" / "psrd"
    if not psrd_root.exists():
        pytest.skip("PSRD sqlite sources are not available in this environment")

    run_dir = tmp_path / "runs"
    run = run_extract(
        source="psrd",
        run_dir=run_dir,
        run_key="kairon_psrd",
        mode="kairon_slice",
        psrd_root=psrd_root,
        d20_root=workspace_root / "data" / "d20pfsrd",
    )
    run_parse(run)
    run_validate(run)

    accepted = read_jsonl(run / "validation" / "accepted_records.jsonl")
    rejected = read_jsonl(run / "validation" / "rejected_records.jsonl")

    feat_names = {str(r["data"]["name"]).lower() for r in accepted if r.get("content_type") == "feat"}
    class_names = {str(r["data"]["name"]).lower() for r in accepted if r.get("content_type") == "class"}
    race_names = {str(r["data"]["name"]).lower() for r in accepted if r.get("content_type") == "race"}

    assert "investigator" in class_names
    assert "tiefling" in race_names
    assert {"weapon finesse", "weapon focus", "rapid shot"}.issubset(feat_names)
    assert not rejected


def test_extract_aon_live_archives_raw_html_and_short_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fake_fetch(url: str, timeout: int = 20) -> str:
        if "FeatDisplay.aspx?ItemName=Weapon%20Finesse" in url:
            return "<html><h1>Weapon Finesse</h1><p>Prerequisites: Base attack bonus +1.</p><p>Benefit: Use Dexterity for certain attacks.</p></html>"
        if "FeatDisplay.aspx?ItemName=Weapon%20Focus" in url:
            return "<html><h1>Weapon Focus</h1><p>Prerequisite: Proficiency with selected weapon, base attack bonus +1.</p><p>Benefit: +1 bonus on attack rolls.</p></html>"
        if "FeatDisplay.aspx?ItemName=Rapid%20Shot" in url:
            return "<html><h1>Rapid Shot</h1><p>Prerequisites: Dex 13, Point-Blank Shot.</p><p>Benefit: Make one additional ranged attack.</p></html>"
        if "TraitDisplay.aspx?ItemName=Reactionary" in url:
            return "<html><h1>Reactionary</h1><p>Benefit: You gain a +2 trait bonus on initiative checks.</p></html>"
        if "SpellDisplay.aspx?ItemName=Haste" in url:
            return "<html><h1>Haste</h1><p>The targets move and act more quickly than normal.</p></html>"
        if "Spells.aspx?Class=All" in url:
            return "<html><body>Haste - One creature/level moves faster, +1 on attack rolls, AC, and Reflex saves.</body></html>"
        if "ClassDisplay.aspx?ItemName=Investigator" in url:
            return "<html><title>Archives of Nethys</title><p>Investigators solve mysteries.</p></html>"
        if "RacesDisplay.aspx?ItemName=Tiefling" in url:
            return "<html><title>Archives of Nethys</title><p>Tieflings are native outsiders.</p></html>"
        return "<html><body>ok</body></html>"

    monkeypatch.setattr(extract_module, "_fetch_url_text", fake_fetch)

    run = run_extract(
        source="aon",
        run_dir=tmp_path / "runs",
        run_key="aon_live",
        mode="aon_live",
        ai_short_fallback=True,
    )
    run_parse(run)
    run_validate(run)

    fetch_log = read_jsonl(run / "raw" / "aon_fetch_log.jsonl")
    assert fetch_log
    assert all(row["status"] in {"fetched", "offline"} for row in fetch_log)

    html_files = list((run / "raw" / "html").glob("*.html"))
    assert len(html_files) >= 5

    accepted = read_jsonl(run / "validation" / "accepted_records.jsonl")
    spell_rows = [r for r in accepted if r.get("content_type") == "spell" and r["data"].get("name") == "Haste"]
    assert spell_rows
    assert spell_rows[0]["data"].get("short_description")
    race_rows = [r for r in accepted if r.get("content_type") == "race"]
    assert race_rows
    assert race_rows[0]["data"]["name"] == "Tiefling"
    class_rows = [r for r in accepted if r.get("content_type") == "class"]
    assert class_rows
    assert any(row["data"].get("name") == "Investigator" for row in class_rows)

    manifest = read_json(run / "manifest.json")
    assert manifest["source"] == "aon"
    assert manifest["mode"] == "aon_live"
    assert manifest["aon"]["failed_pages"] == 0


def test_extract_aon_catalog_adds_index_discovered_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fake_fetch(url: str, timeout: int = 20) -> str:
        if "Feats.aspx" in url:
            return (
                '<html><body>'
                '<a href="FeatDisplay.aspx?ItemName=Power%20Attack">Power Attack</a> - Trade melee accuracy for damage.'
                '</body></html>'
            )
        if "Spells.aspx?Class=All" in url:
            return (
                '<html><body>'
                '<a href="SpellDisplay.aspx?ItemName=Fireball">Fireball</a> - A burst of fire that deals 1d6/level.'
                '</body></html>'
            )
        if "FeatDisplay.aspx?ItemName=Power%20Attack" in url:
            return (
                "<html><h1>Power Attack</h1>"
                "<p>Prerequisite: Str 13.</p>"
                "<p>Benefit: Take a penalty on melee attacks for bonus damage.</p>"
                "</html>"
            )
        if "SpellDisplay.aspx?ItemName=Fireball" in url:
            return (
                "<html><h1>Fireball</h1>"
                "<p>School evocation [fire]; Level sorcerer/wizard 3.</p>"
                "<p>A fireball deals 1d6 points of fire damage per caster level.</p>"
                "</html>"
            )
        if "ClassDisplay.aspx?ItemName=Alchemist" in url:
            return "<html><h1>Alchemist</h1><p>Hit Die d8.</p></html>"
        if "FeatDisplay.aspx?ItemName=Weapon%20Finesse" in url:
            return "<html><h1>Weapon Finesse</h1><p>Prerequisites: Base attack bonus +1.</p><p>Benefit: Use Dexterity.</p></html>"
        if "FeatDisplay.aspx?ItemName=Weapon%20Focus" in url:
            return "<html><h1>Weapon Focus</h1><p>Prerequisite: Base attack bonus +1.</p><p>Benefit: +1 attack.</p></html>"
        if "FeatDisplay.aspx?ItemName=Rapid%20Shot" in url:
            return "<html><h1>Rapid Shot</h1><p>Prerequisites: Dex 13, Point-Blank Shot.</p><p>Benefit: extra attack.</p></html>"
        if "TraitDisplay.aspx?ItemName=Reactionary" in url:
            return "<html><h1>Reactionary</h1><p>Benefit: +2 initiative.</p></html>"
        if "SpellDisplay.aspx?ItemName=Haste" in url:
            return "<html><h1>Haste</h1><p>School transmutation; Level alchemist 3.</p></html>"
        if "ClassDisplay.aspx?ItemName=Investigator" in url:
            return "<html><h1>Investigator</h1><p>Hit Die d8.</p></html>"
        if "RacesDisplay.aspx?ItemName=Tiefling" in url:
            return "<html><h1>Tiefling</h1><p>Darkvision.</p></html>"
        return "<html><body>ok</body></html>"

    monkeypatch.setattr(extract_module, "_fetch_url_text", fake_fetch)

    run = run_extract(
        source="aon",
        run_dir=tmp_path / "runs",
        run_key="aon_catalog",
        mode="aon_catalog",
        catalog_kind="all",
        catalog_limit=1,
    )
    run_parse(run)
    run_validate(run)

    accepted = read_jsonl(run / "validation" / "accepted_records.jsonl")
    feat_names = {r["data"]["name"] for r in accepted if r.get("content_type") == "feat"}
    spell_names = {r["data"]["name"] for r in accepted if r.get("content_type") == "spell"}
    assert "Power Attack" in feat_names
    assert "Fireball" in spell_names

    resolution = read_jsonl(run / "raw" / "aon_source_resolution.jsonl")
    assert resolution
    coverage = read_json(run / "raw" / "aon_coverage_report.json")
    assert "missing_classes" in coverage
    assert "missing_books" in coverage


def test_aon_url_normalization_handles_spaces_and_apostrophes():
    raw_href = "/SpellDisplay.aspx?ItemName=Abadar's Truthtelling"
    normalized = extract_module._aon_absolute_url(raw_href)
    assert normalized == "https://aonprd.com/SpellDisplay.aspx?ItemName=Abadar%27s%20Truthtelling"


def test_aon_catalog_d20_fallback_fills_unknown_source_book(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    d20_root = tmp_path / "d20"
    parsed = d20_root / "parsed"
    parsed.mkdir(parents=True)
    (parsed / "classes.json").write_text(
        json.dumps(
            [
                {
                    "name": "Alchemist",
                    "source": "Advanced Player's Guide",
                    "hit_die": "d8",
                    "skill_ranks_per_level": 4,
                    "description": "Alchemy class description.",
                }
            ]
        ),
        encoding="utf-8",
    )
    (parsed / "traits.json").write_text("[]", encoding="utf-8")

    def fake_fetch(url: str, timeout: int = 20) -> str:
        if "ClassDisplay.aspx?ItemName=Alchemist" in url:
            return "<html><h1>Alchemist</h1><p>Hit Die d8.</p></html>"
        if "ClassDisplay.aspx?ItemName=Investigator" in url:
            return "<html><h1>Investigator</h1><p>Hit Die d8.</p></html>"
        if "RacesDisplay.aspx?ItemName=Tiefling" in url:
            return "<html><h1>Tiefling</h1></html>"
        if "FeatDisplay.aspx?ItemName=Weapon%20Finesse" in url:
            return "<html><h1>Weapon Finesse</h1><p>Prerequisites: Base attack bonus +1.</p><p>Benefit: Use Dexterity.</p></html>"
        if "FeatDisplay.aspx?ItemName=Weapon%20Focus" in url:
            return "<html><h1>Weapon Focus</h1><p>Prerequisite: Base attack bonus +1.</p><p>Benefit: +1 attack.</p></html>"
        if "FeatDisplay.aspx?ItemName=Rapid%20Shot" in url:
            return "<html><h1>Rapid Shot</h1><p>Prerequisites: Dex 13, Point-Blank Shot.</p><p>Benefit: extra attack.</p></html>"
        if "TraitDisplay.aspx?ItemName=Reactionary" in url:
            return "<html><h1>Reactionary</h1><p>Benefit: +2 initiative.</p></html>"
        if "SpellDisplay.aspx?ItemName=Haste" in url:
            return "<html><h1>Haste</h1><p>School transmutation; Level alchemist 3.</p></html>"
        return "<html><body>ok</body></html>"

    monkeypatch.setattr(extract_module, "_fetch_url_text", fake_fetch)

    run = run_extract(
        source="aon",
        run_dir=tmp_path / "runs",
        run_key="aon_d20_fallback",
        mode="aon_catalog",
        catalog_kind="classes",
        catalog_limit=1,
        d20_root=d20_root,
    )
    run_parse(run)
    run_validate(run)

    accepted = read_jsonl(run / "validation" / "accepted_records.jsonl")
    alchemist = next((r for r in accepted if r.get("content_type") == "class" and r["data"].get("name") == "Alchemist"), None)
    assert alchemist is not None
    assert alchemist.get("source_book") == "Advanced Player's Guide"

    coverage = read_json(run / "raw" / "aon_coverage_report.json")
    assert "d20_fallback_counts" in coverage
    assert coverage["d20_fallback_counts"]["class"] >= 0


def test_allowlist_keeps_approved_class_scope_rows_with_non_allowlist_book():
    rows = [
        {
            "content_type": "class",
            "source_url": "https://aonprd.com/ClassDisplay.aspx?ItemName=Psychic",
            "source_book": "Occult Adventures",
            "payload": {"name": "Psychic"},
        },
        {
            "content_type": "class_progression",
            "source_url": "https://aonprd.com/ClassDisplay.aspx?ItemName=Psychic",
            "source_book": "Occult Adventures",
            "payload": {"class_name": "Psychic", "level": 1},
        },
        {
            "content_type": "feat",
            "source_url": "https://aonprd.com/FeatDisplay.aspx?ItemName=Psychic%20Sensitivity",
            "source_book": "Occult Adventures",
            "payload": {"name": "Psychic Sensitivity"},
        },
    ]

    filtered, policy_logs, coverage = extract_module._apply_allowlist_filters(rows)
    by_type = {row["content_type"]: row for row in filtered}

    assert set(by_type.keys()) == {"class", "class_progression", "feat"}
    assert by_type["class"]["ui_enabled"] is True
    assert by_type["class"]["ui_tier"] == "active"
    assert by_type["class_progression"]["ui_enabled"] is True
    assert by_type["feat"]["ui_enabled"] is False
    assert by_type["feat"]["ui_tier"] == "deferred"
    assert "book_not_in_allowlist" in by_type["feat"]["policy_reason"]
    assert coverage["policy_counts"]["ui_enabled"] >= 2
    assert coverage["policy_counts"]["ui_deferred"] >= 1
    assert coverage["dropped_counts"]["book_not_approved"] == 0
    assert any(row.get("ui_tier") == "deferred" for row in policy_logs)


def test_source_book_normalization_strips_page_suffix_and_noise():
    assert extract_module._canonical_book_name("Advanced Player's Guide pg. 28") == "Advanced Player's Guide"
    assert extract_module._canonical_book_name("Source: Core Rulebook, pg 131") == "Core Rulebook"
    assert extract_module._canonical_book_name("Pathfinder RPG Core Rulebook pg. 131") == "Core Rulebook"
    assert extract_module._canonical_book_name("PRPG Advanced Class Guide p. 10") == "Advanced Class Guide"
    assert extract_module._canonical_book_name("Pathfinder Roleplaying Game Ultimate Combat") == "Ultimate Combat"
    assert (
        extract_module._canonical_book_name("Pathfinder #102: Breaking the Bones of Hell pg")
        == "Pathfinder #102: Breaking the Bones of Hell"
    )
    assert extract_module._canonical_book_name(" , it takes an additional 1d6 points of fire damage as its flesh burns") is None


def test_load_persists_ui_policy_flags(tmp_path: Path):
    run_dir = tmp_path / "runs"
    input_path = tmp_path / "policy_records.json"
    records = [
        {
            "content_type": "class",
            "source_url": "https://example/class",
            "source_book": "Occult Adventures",
            "license_tag": "OGL",
            "ui_enabled": False,
            "ui_tier": "deferred",
            "policy_reason": "book_not_in_allowlist",
            "payload": {
                "name": "Psychic Adept",
                "class_type": "base",
                "hit_die": "d6",
                "skill_ranks_per_level": 2,
                "bab_progression": "half",
                "fort_progression": "poor",
                "ref_progression": "poor",
                "will_progression": "good",
            },
        },
    ]
    input_path.write_text(json.dumps(records), encoding="utf-8")

    run = run_extract(source="psrd", run_dir=run_dir, input_path=input_path, run_key="policy_load")
    run_parse(run)
    run_validate(run)
    dsn = f"sqlite:///{tmp_path / 'policy.db'}"
    run_load(run, dsn)

    conn = sqlite3.connect(str(tmp_path / "policy.db"))
    try:
        row = conn.execute(
            "SELECT ui_enabled, ui_tier, policy_reason FROM source_records WHERE content_type = 'class' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert int(row[0]) == 0
        assert row[1] == "deferred"
        assert row[2] == "book_not_in_allowlist"
    finally:
        conn.close()


def test_baseline_summary_fixture_is_present_and_well_formed():
    baseline_path = Path(__file__).resolve().parents[1] / "baselines" / "aon_catalog_live_v1_summary.json"
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))

    assert payload["baseline_name"] == "aon_catalog_live_v1"
    assert payload["source"] == "aon"
    assert payload["mode"] == "aon_catalog"
    assert payload["validation"]["passed"] is True
    assert payload["validation"]["accepted_count"] >= 3000
    assert payload["coverage"]["approved_classes_total"] == 44
    assert payload["coverage"]["ingested_classes_total"] >= 44
