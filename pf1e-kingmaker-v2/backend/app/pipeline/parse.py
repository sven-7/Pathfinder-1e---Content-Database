"""Parse step: normalize raw records into canonical parsed records."""

from __future__ import annotations

from pathlib import Path

from app.pipeline.utils import read_jsonl, sha256_text, stable_json_dumps, write_json, write_jsonl


_SUPPORTED_TYPES = {
    "class",
    "class_progression",
    "class_feature",
    "race",
    "racial_trait",
    "feat",
    "trait",
    "spell",
    "spell_class_level",
    "equipment",
    "weapon",
    "armor",
}


def _clean_str(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _normalize_payload(content_type: str, payload: dict) -> dict:
    out = {k: v for k, v in payload.items()}

    for key, value in list(out.items()):
        if isinstance(value, str):
            out[key] = value.strip()

    if "name" in out:
        out["name"] = _clean_str(out["name"])

    if content_type == "feat":
        out["feat_type"] = _clean_str(out.get("feat_type", "general")).lower()
    if content_type == "race":
        out["race_type"] = _clean_str(out.get("race_type", "other")).lower()

    return out


def run_parse(run_path: Path) -> Path:
    raw_rows = read_jsonl(run_path / "raw" / "source_records.jsonl")
    parsed_rows: list[dict] = []

    for row in raw_rows:
        content_type = row.get("content_type", "unknown")
        if content_type not in _SUPPORTED_TYPES:
            continue

        parsed_rows.append(
            {
                "record_key": row["record_key"],
                "raw_hash": row["raw_hash"],
                "source_name": row.get("source_name", "unknown"),
                "source_url": row.get("source_url", ""),
                "source_book": row.get("source_book", "Unknown"),
                "license_tag": row.get("license_tag", "OGL"),
                "content_type": content_type,
                "data": _normalize_payload(content_type, row.get("payload", {})),
            }
        )

    parsed_dir = run_path / "parsed"
    write_jsonl(parsed_dir / "parsed_records.jsonl", parsed_rows)

    report = {
        "parsed_count": len(parsed_rows),
        "parsed_hash": sha256_text(stable_json_dumps(parsed_rows)),
    }
    write_json(parsed_dir / "parse_report.json", report)
    return parsed_dir
