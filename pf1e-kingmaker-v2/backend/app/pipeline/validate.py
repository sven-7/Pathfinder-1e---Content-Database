"""Validate step: enforce quality gates and emit accepted/rejected records."""

from __future__ import annotations

from pathlib import Path

from app.pipeline.utils import read_jsonl, write_json, write_jsonl


_BANNED_FEAT_NAMES = {
    "feat name",
    "benefit",
    "table: feats",
    "prerequisite",
    "special",
    "normal",
    "types of feats",
    "metamagic feats",
}


_REQUIRED_FIELDS = {
    "class": ["name"],
    "class_progression": ["class_name", "level", "bab", "fort_save", "ref_save", "will_save"],
    "class_feature": ["class_name", "name"],
    "race": ["name"],
    "racial_trait": ["race_name", "name"],
    "feat": ["name", "feat_type"],
    "trait": ["name", "trait_type"],
    "spell": ["name"],
    "spell_class_level": ["spell_name", "class_name", "level"],
    "equipment": ["name", "equipment_type"],
    "weapon": ["equipment_name", "damage_medium"],
    "armor": ["equipment_name", "armor_bonus"],
}


_REQUIRED_ENTITIES = {
    "class": {"investigator"},
    "race": {"tiefling"},
    "feat": {"weapon finesse", "weapon focus", "rapid shot"},
    "trait": {"reactionary"},
    "spell": {"haste"},
    "equipment": {"rapier", "studded leather"},
}


def run_validate(run_path: Path) -> Path:
    rows = read_jsonl(run_path / "parsed" / "parsed_records.jsonl")

    accepted: list[dict] = []
    rejected: list[dict] = []

    races: set[str] = set()
    race_with_traits: set[str] = set()
    seen_entities: dict[str, set[str]] = {key: set() for key in _REQUIRED_ENTITIES}
    progression_rows: set[tuple[str, int]] = set()

    for row in rows:
        ctype = row.get("content_type", "")
        data = row.get("data", {})

        reason = ""
        for required in _REQUIRED_FIELDS.get(ctype, []):
            if data.get(required) in (None, ""):
                reason = f"missing required field: {required}"
                break

        if not reason and ctype == "feat":
            feat_name = str(data.get("name", "")).strip().lower()
            if feat_name in _BANNED_FEAT_NAMES:
                reason = "junk feat/header row"

        if ctype == "race" and data.get("name"):
            races.add(str(data["name"]).strip())
        if ctype == "racial_trait" and data.get("race_name"):
            race_with_traits.add(str(data["race_name"]).strip())

        if reason:
            rejected.append({**row, "reject_reason": reason})
        else:
            if ctype in seen_entities and data.get("name"):
                seen_entities[ctype].add(str(data["name"]).strip().lower())
            if ctype == "class_progression" and data.get("class_name") and data.get("level") is not None:
                progression_rows.add((str(data["class_name"]).strip().lower(), int(data["level"])))
            accepted.append(row)

    # Global quality gate: all races must have at least one racial trait.
    missing_racial_traits = sorted(races - race_with_traits)
    if missing_racial_traits:
        for race_name in missing_racial_traits:
            rejected.append(
                {
                    "content_type": "race_quality_gate",
                    "data": {"race_name": race_name},
                    "reject_reason": "race missing linked racial_traits",
                }
            )

    missing_required_entities: list[str] = []
    for content_type, required_names in _REQUIRED_ENTITIES.items():
        missing = sorted(required_names - seen_entities[content_type])
        for name in missing:
            missing_required_entities.append(f"{content_type}:{name}")
            rejected.append(
                {
                    "content_type": f"{content_type}_quality_gate",
                    "data": {"name": name},
                    "reject_reason": f"missing required {content_type}: {name}",
                }
            )

    if ("investigator", 9) not in progression_rows:
        missing_required_entities.append("class_progression:investigator@9")
        rejected.append(
            {
                "content_type": "class_progression_quality_gate",
                "data": {"class_name": "Investigator", "level": 9},
                "reject_reason": "missing required class progression row: Investigator level 9",
            }
        )

    validation_dir = run_path / "validation"
    write_jsonl(validation_dir / "accepted_records.jsonl", accepted)
    write_jsonl(validation_dir / "rejected_records.jsonl", rejected)

    report = {
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "missing_racial_traits": missing_racial_traits,
        "missing_required_entities": missing_required_entities,
        "passed": len(rejected) == 0,
    }
    write_json(validation_dir / "validation_report.json", report)
    return validation_dir
