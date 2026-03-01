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
            return "<html><h1>Investigator</h1><p>Investigators solve mysteries.</p></html>"
        if "RacesDisplay.aspx?ItemName=Tiefling" in url:
            return "<html><h1>Tiefling</h1><p>Tieflings are native outsiders.</p></html>"
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

    manifest = read_json(run / "manifest.json")
    assert manifest["source"] == "aon"
    assert manifest["mode"] == "aon_live"
    assert manifest["aon"]["failed_pages"] == 0
