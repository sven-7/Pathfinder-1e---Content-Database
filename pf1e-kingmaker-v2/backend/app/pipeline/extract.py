"""Extract step: source records -> raw records with deterministic hashes."""

from __future__ import annotations

import datetime as dt
import html
import os
import re
import sqlite3
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

from app.pipeline.fixtures import kairon_slice_records
from app.pipeline.utils import ensure_dir, read_json, sha256_text, stable_json_dumps, write_json, write_jsonl


_INVESTIGATOR_PROFILE = {
    "skill_ranks_per_level": 6,
    "bab_progression": "three_quarter",
    "fort_progression": "poor",
    "ref_progression": "good",
    "will_progression": "good",
}


_AON_KAIRON_URLS = {
    "class_investigator": "https://aonprd.com/ClassDisplay.aspx?ItemName=Investigator",
    "race_tiefling": "https://aonprd.com/RacesDisplay.aspx?ItemName=Tiefling",
    "feat_weapon_finesse": "https://aonprd.com/FeatDisplay.aspx?ItemName=Weapon%20Finesse",
    "feat_weapon_focus": "https://aonprd.com/FeatDisplay.aspx?ItemName=Weapon%20Focus",
    "feat_rapid_shot": "https://aonprd.com/FeatDisplay.aspx?ItemName=Rapid%20Shot",
    "trait_reactionary": "https://aonprd.com/TraitDisplay.aspx?ItemName=Reactionary",
    "spell_haste": "https://aonprd.com/SpellDisplay.aspx?ItemName=Haste",
    "spell_list_all": "https://aonprd.com/Spells.aspx?Class=All",
    "weapons_overview": "https://aonprd.com/EquipmentWeapons.aspx",
    "armor_overview": "https://aonprd.com/EquipmentArmor.aspx",
}


_AON_KAIRON_FALLBACK = {
    "class": {
        "source_url": _AON_KAIRON_URLS["class_investigator"],
        "source_book": "Advanced Class Guide",
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
    "race": {
        "source_url": _AON_KAIRON_URLS["race_tiefling"],
        "source_book": "Advanced Race Guide",
        "payload": {"name": "Tiefling", "race_type": "featured", "size": "Medium", "base_speed": 30},
    },
    "racial_trait": {
        "source_url": _AON_KAIRON_URLS["race_tiefling"],
        "source_book": "Advanced Race Guide",
        "payload": {
            "race_name": "Tiefling",
            "name": "Darkvision",
            "trait_type": "senses",
            "description": "Tieflings can see perfectly in darkness up to 60 feet.",
            "replaces": "",
        },
    },
    "feats": {
        "Weapon Finesse": {
            "source_url": _AON_KAIRON_URLS["feat_weapon_finesse"],
            "source_book": "Core Rulebook",
            "payload": {
                "name": "Weapon Finesse",
                "feat_type": "combat",
                "prerequisites": "Base attack bonus +1",
                "benefit": "Use Dexterity instead of Strength on attack rolls with selected weapons.",
            },
        },
        "Weapon Focus": {
            "source_url": _AON_KAIRON_URLS["feat_weapon_focus"],
            "source_book": "Core Rulebook",
            "payload": {
                "name": "Weapon Focus",
                "feat_type": "combat",
                "prerequisites": "Proficiency with selected weapon, base attack bonus +1",
                "benefit": "Gain +1 bonus on attack rolls with the selected weapon.",
            },
        },
        "Rapid Shot": {
            "source_url": _AON_KAIRON_URLS["feat_rapid_shot"],
            "source_book": "Core Rulebook",
            "payload": {
                "name": "Rapid Shot",
                "feat_type": "combat",
                "prerequisites": "Dex 13, Point-Blank Shot",
                "benefit": "One extra ranged attack at highest bonus with a -2 penalty.",
            },
        },
    },
    "trait_reactionary": {
        "source_url": _AON_KAIRON_URLS["trait_reactionary"],
        "source_book": "Ultimate Campaign",
        "payload": {
            "name": "Reactionary",
            "trait_type": "combat",
            "prerequisites": "",
            "benefit": "You gain a +2 trait bonus on initiative checks.",
            "description": "You became adept at anticipating sudden attacks and reacting quickly.",
        },
    },
    "spell_haste": {
        "source_url": _AON_KAIRON_URLS["spell_haste"],
        "source_book": "Core Rulebook",
        "payload": {
            "name": "Haste",
            "school": "transmutation",
            "short_description": "One creature/level moves and acts more quickly than normal.",
            "description": "The transmuted creatures move and act more quickly than normal.",
        },
    },
    "spell_class_level_haste": {
        "source_url": _AON_KAIRON_URLS["spell_haste"],
        "source_book": "Core Rulebook",
        "payload": {"spell_name": "Haste", "class_name": "Investigator", "level": 3},
    },
    "equipment_rapier": {
        "source_url": _AON_KAIRON_URLS["weapons_overview"],
        "source_book": "Core Rulebook",
        "payload": {
            "name": "Rapier",
            "equipment_type": "weapon",
            "cost": "20 gp",
            "weight": 2.0,
            "description": "A rapier is a one-handed martial melee weapon.",
        },
    },
    "weapon_rapier": {
        "source_url": _AON_KAIRON_URLS["weapons_overview"],
        "source_book": "Core Rulebook",
        "payload": {
            "equipment_name": "Rapier",
            "proficiency": "martial",
            "weapon_type": "melee",
            "handedness": "one-handed",
            "damage_medium": "1d6",
            "critical": "18-20/x2",
        },
    },
    "equipment_studded_leather": {
        "source_url": _AON_KAIRON_URLS["armor_overview"],
        "source_book": "Core Rulebook",
        "payload": {
            "name": "Studded Leather",
            "equipment_type": "armor",
            "cost": "25 gp",
            "weight": 20.0,
            "description": "Leather armor reinforced with small metal studs.",
        },
    },
    "armor_studded_leather": {
        "source_url": _AON_KAIRON_URLS["armor_overview"],
        "source_book": "Core Rulebook",
        "payload": {
            "equipment_name": "Studded Leather",
            "armor_type": "light",
            "armor_bonus": 3,
            "max_dex": 5,
            "armor_check_penalty": -1,
            "arcane_spell_failure": 15,
        },
    },
}


def _git_sha() -> str:
    return os.getenv("GIT_SHA", "unknown")


def _normalize_input_records(raw: object) -> list[dict]:
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    raise ValueError("input JSON must be a list of record objects")


def _strip_html(value: object) -> str:
    raw = html.unescape(str(value or ""))
    without_tags = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", without_tags).strip()


def _parse_int(value: object) -> int | None:
    text = html.unescape(str(value or ""))
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    match = re.search(r"-?\d+", text)
    if not match:
        return None
    return int(match.group(0))


def _parse_weight(value: object) -> float | None:
    text = html.unescape(str(value or ""))
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def _feat_type_normalized(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "general"
    return text.replace(" ", "_")


def _resolve_source_root(explicit: Path | None, env_var: str, default_rel: Path) -> Path | None:
    if explicit:
        path = explicit.expanduser()
        if not path.exists():
            raise FileNotFoundError(f"source root does not exist: {path}")
        return path.resolve()

    env_val = os.getenv(env_var)
    if env_val:
        env_path = Path(env_val).expanduser()
        if env_path.exists():
            return env_path.resolve()

    candidates = [
        Path.cwd() / default_rel,
        Path.cwd().parent / default_rel,
        Path.cwd().parent.parent / default_rel,
        Path(__file__).resolve().parents[4] / default_rel,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _aon_cache_name_for_url(url: str) -> str:
    return f"{sha256_text(url)}.html"


def _fetch_url_text(url: str, timeout: int = 20) -> str:
    req = urlrequest.Request(
        url,
        headers={
            "User-Agent": "pf1e-kingmaker-v2-ingestion/0.1 (+https://github.com/sven-7/Pathfinder-1e---Content-Database)"
        },
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _fetch_aon_page(
    url: str,
    html_dir: Path,
    *,
    timeout: int = 20,
    max_retries: int = 1,
    offline_html_dir: Path | None = None,
) -> dict:
    ensure_dir(html_dir)
    cache_file = html_dir / _aon_cache_name_for_url(url)
    if offline_html_dir:
        offline_file = offline_html_dir / _aon_cache_name_for_url(url)
        if offline_file.exists():
            html_text = offline_file.read_text(encoding="utf-8")
            cache_file.write_text(html_text, encoding="utf-8")
            return {
                "url": url,
                "status": "offline",
                "attempts": 0,
                "html_file": str(cache_file.relative_to(html_dir.parent)),
                "html_hash": sha256_text(html_text),
                "error": "",
            }

    attempts = 0
    last_error = ""
    while attempts <= max_retries:
        attempts += 1
        try:
            html_text = _fetch_url_text(url, timeout=timeout)
            cache_file.write_text(html_text, encoding="utf-8")
            return {
                "url": url,
                "status": "fetched",
                "attempts": attempts,
                "html_file": str(cache_file.relative_to(html_dir.parent)),
                "html_hash": sha256_text(html_text),
                "error": "",
            }
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
            if attempts <= max_retries:
                time.sleep(min(2.0 * attempts, 5.0))

    return {
        "url": url,
        "status": "error",
        "attempts": attempts,
        "html_file": "",
        "html_hash": "",
        "error": last_error,
    }


def _first_sentence(text: str, max_len: int = 180) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    match = re.search(r"(.+?[.!?])(?:\s|$)", stripped)
    sentence = match.group(1).strip() if match else stripped
    return sentence[:max_len].strip()


def _ai_short_description(
    *,
    text: str,
    enabled: bool,
    openai_model: str | None = None,
) -> tuple[str, str]:
    # Deterministic fallback first; external AI call is optional and best-effort.
    heuristic = _first_sentence(text)
    if not enabled:
        return heuristic, "heuristic:first_sentence"

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return heuristic, "heuristic:first_sentence(no_api_key)"

    try:
        from openai import OpenAI
    except Exception:
        return heuristic, "heuristic:first_sentence(openai_unavailable)"

    try:
        client = OpenAI(api_key=api_key)
        model = openai_model or os.getenv("PF1E_SHORTDESC_MODEL", "gpt-4.1-mini")
        response = client.responses.create(
            model=model,
            input=(
                "Summarize this Pathfinder rules text in one short sentence under 25 words. "
                "Return plain text only.\n\n"
                f"{text}"
            ),
            max_output_tokens=80,
        )
        short = (response.output_text or "").strip()
        if short:
            return short, f"ai:{model}"
    except Exception:
        pass
    return heuristic, "heuristic:first_sentence(ai_failed)"


def _extract_heading_from_html(html_text: str) -> str:
    for pattern in (r"<h1[^>]*>(.*?)</h1>", r"<title[^>]*>(.*?)</title>"):
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _strip_html(match.group(1))
    return ""


def _extract_field_text(full_text: str, labels: list[str]) -> str:
    normalized = re.sub(r"\s+", " ", full_text)
    for label in labels:
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:\-]?\s*(.+?)(?=(?:Prerequisites?|Benefit|Benefits?|Special|Normal|Description|$))",
            flags=re.IGNORECASE,
        )
        match = pattern.search(normalized)
        if match:
            return match.group(1).strip()
    return ""


def _extract_spell_short_from_list_page(list_text: str, spell_name: str) -> str:
    # Look for common "Name - short text" patterns.
    pattern = re.compile(rf"{re.escape(spell_name)}\s*[-–—:]\s*([^\n\r]+)", flags=re.IGNORECASE)
    match = pattern.search(list_text)
    if match:
        return match.group(1).strip()
    return ""


def _record(
    content_type: str,
    source_url: str,
    source_book: str,
    payload: dict,
    *,
    license_tag: str = "OGL",
) -> dict:
    return {
        "content_type": content_type,
        "source_url": source_url,
        "source_book": source_book,
        "license_tag": license_tag,
        "payload": payload,
    }


def _identity_key(content_type: str, payload: dict) -> tuple[str, str]:
    if content_type == "class":
        return (content_type, str(payload.get("name", "")).lower())
    if content_type == "class_progression":
        return (content_type, f"{payload.get('class_name','')}|{payload.get('level','')}".lower())
    if content_type == "class_feature":
        return (content_type, f"{payload.get('class_name','')}|{payload.get('name','')}|{payload.get('level','')}".lower())
    if content_type == "race":
        return (content_type, str(payload.get("name", "")).lower())
    if content_type == "racial_trait":
        return (content_type, f"{payload.get('race_name','')}|{payload.get('name','')}".lower())
    if content_type == "feat":
        return (content_type, str(payload.get("name", "")).lower())
    if content_type == "trait":
        return (content_type, str(payload.get("name", "")).lower())
    if content_type == "spell":
        return (content_type, str(payload.get("name", "")).lower())
    if content_type == "spell_class_level":
        return (content_type, f"{payload.get('spell_name','')}|{payload.get('class_name','')}".lower())
    if content_type == "equipment":
        return (content_type, str(payload.get("name", "")).lower())
    if content_type in {"weapon", "armor"}:
        return (content_type, str(payload.get("equipment_name", "")).lower())
    return (content_type, stable_json_dumps(payload))


def _dedupe_records(records: list[dict]) -> list[dict]:
    deduped: dict[tuple[str, str], dict] = {}
    for row in records:
        key = _identity_key(str(row.get("content_type", "")), dict(row.get("payload", {})))
        deduped[key] = row
    return sorted(
        deduped.values(),
        key=lambda row: (
            str(row.get("content_type", "")),
            stable_json_dumps(row.get("payload", {})),
            str(row.get("source_url", "")),
        ),
    )


def _open_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _bab_for_level(level: int, progression: str) -> int:
    if progression == "full":
        return level
    if progression == "three_quarter":
        return (3 * level) // 4
    if progression == "half":
        return level // 2
    return 0


def _save_for_level(level: int, progression: str) -> int:
    if progression == "good":
        return 2 + (level // 2)
    return level // 3


def _feature_level_guess(text: str) -> int | None:
    patterns = [
        r"\b(?:At|at)\s+(\d{1,2})(?:st|nd|rd|th)\s+level\b",
        r"\bInvestigator\s+(\d{1,2})(?:st|nd|rd|th)\s+level\b",
        r"\b(\d{1,2})(?:st|nd|rd|th)-level\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            level = int(match.group(1))
            if 1 <= level <= 20:
                return level
    return None


def _extract_investigator_class_records(psrd_root: Path) -> list[dict]:
    acg_db = psrd_root / "book-acg.db"
    if not acg_db.exists():
        return []

    records: list[dict] = []
    with _open_db(acg_db) as conn:
        row = conn.execute(
            """
            SELECT s.section_id, s.name, s.subtype, s.source, s.url, cd.hit_die
            FROM sections s
            LEFT JOIN class_details cd ON cd.section_id = s.section_id
            WHERE s.type = 'class' AND lower(s.name) = 'investigator'
            ORDER BY s.section_id
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return records

        class_name = "Investigator"
        records.append(
            _record(
                "class",
                row["url"] or "",
                row["source"] or "Advanced Class Guide",
                {
                    "name": class_name,
                    "class_type": row["subtype"] or "hybrid",
                    "hit_die": row["hit_die"] or "d8",
                    "skill_ranks_per_level": _INVESTIGATOR_PROFILE["skill_ranks_per_level"],
                    "bab_progression": _INVESTIGATOR_PROFILE["bab_progression"],
                    "fort_progression": _INVESTIGATOR_PROFILE["fort_progression"],
                    "ref_progression": _INVESTIGATOR_PROFILE["ref_progression"],
                    "will_progression": _INVESTIGATOR_PROFILE["will_progression"],
                },
            )
        )

        specials = {9: "trapfinding, inspiration, studied combat"}
        spell_map = {9: {"1": 5, "2": 4, "3": 3}}
        for level in range(1, 21):
            records.append(
                _record(
                    "class_progression",
                    row["url"] or "",
                    row["source"] or "Advanced Class Guide",
                    {
                        "class_name": class_name,
                        "level": level,
                        "bab": _bab_for_level(level, _INVESTIGATOR_PROFILE["bab_progression"]),
                        "fort_save": _save_for_level(level, _INVESTIGATOR_PROFILE["fort_progression"]),
                        "ref_save": _save_for_level(level, _INVESTIGATOR_PROFILE["ref_progression"]),
                        "will_save": _save_for_level(level, _INVESTIGATOR_PROFILE["will_progression"]),
                        "special": specials.get(level, ""),
                        "spells_per_day": spell_map.get(level, {}),
                    },
                )
            )

        features_root = conn.execute(
            """
            SELECT section_id, lft, rgt
            FROM sections
            WHERE parent_id = ? AND lower(name) = 'class features'
            ORDER BY section_id
            LIMIT 1
            """,
            (int(row["section_id"]),),
        ).fetchone()
        if not features_root:
            return records

        feature_rows = conn.execute(
            """
            SELECT section_id, name, type, subtype, source, url, description, body
            FROM sections
            WHERE lft > ? AND rgt < ? AND type IN ('ability', 'section')
            ORDER BY lft
            """,
            (int(features_root["lft"]), int(features_root["rgt"])),
        ).fetchall()

        for feat_row in feature_rows:
            name = str(feat_row["name"] or "").strip()
            if not name:
                continue
            description = _strip_html(feat_row["body"] or feat_row["description"])
            guess_level = _feature_level_guess(description)
            records.append(
                _record(
                    "class_feature",
                    feat_row["url"] or row["url"] or "",
                    feat_row["source"] or row["source"] or "Advanced Class Guide",
                    {
                        "class_name": class_name,
                        "name": name,
                        "level": guess_level,
                        "feature_type": feat_row["subtype"] or feat_row["type"] or "class_feature",
                        "description": description,
                    },
                )
            )

    return records


def _extract_tiefling_records(psrd_root: Path) -> list[dict]:
    arg_db = psrd_root / "book-arg.db"
    if not arg_db.exists():
        return []

    records: list[dict] = []
    with _open_db(arg_db) as conn:
        race_row = conn.execute(
            """
            SELECT section_id, name, subtype, source, url
            FROM sections
            WHERE type = 'race' AND lower(name) IN ('tiefling', 'tieflings')
            ORDER BY section_id
            LIMIT 1
            """
        ).fetchone()
        if not race_row:
            return records

        race_name = "Tiefling"
        race_type = str(race_row["subtype"] or "other").replace("_race", "")
        traits_section = conn.execute(
            """
            SELECT section_id
            FROM sections
            WHERE parent_id = ? AND lower(name) LIKE '%racial traits%'
            ORDER BY section_id
            LIMIT 1
            """,
            (int(race_row["section_id"]),),
        ).fetchone()

        trait_rows: list[sqlite3.Row] = []
        if traits_section:
            trait_rows = list(
                conn.execute(
                    """
                    SELECT section_id, name, source, url, body, description
                    FROM sections
                    WHERE parent_id = ?
                    ORDER BY lft
                    """,
                    (int(traits_section["section_id"]),),
                ).fetchall()
            )

        size = "Medium"
        base_speed = 30
        for trait_row in trait_rows:
            trait_name = str(trait_row["name"] or "").strip()
            body_text = _strip_html(trait_row["body"] or trait_row["description"])
            if trait_name.lower() in {"small", "medium", "large"}:
                size = trait_name
            if "base speed" in body_text.lower():
                parsed_speed = _parse_int(body_text)
                if parsed_speed is not None:
                    base_speed = parsed_speed

        records.append(
            _record(
                "race",
                race_row["url"] or "",
                race_row["source"] or "Advanced Race Guide",
                {"name": race_name, "race_type": race_type, "size": size, "base_speed": base_speed},
            )
        )

        for trait_row in trait_rows:
            trait_name = str(trait_row["name"] or "").strip()
            if not trait_name:
                continue
            trait_type = "senses" if trait_name.lower() == "darkvision" else "racial"
            records.append(
                _record(
                    "racial_trait",
                    trait_row["url"] or race_row["url"] or "",
                    trait_row["source"] or race_row["source"] or "Advanced Race Guide",
                    {
                        "race_name": race_name,
                        "name": trait_name,
                        "trait_type": trait_type,
                        "description": _strip_html(trait_row["body"] or trait_row["description"]),
                        "replaces": "",
                    },
                )
            )

    return records


def _extract_feat_records(psrd_root: Path) -> list[dict]:
    cr_db = psrd_root / "book-cr.db"
    if not cr_db.exists():
        return []

    target_feats = ["rapid shot", "weapon finesse", "weapon focus"]
    placeholders = ",".join(["?"] * len(target_feats))
    records: list[dict] = []

    with _open_db(cr_db) as conn:
        feat_rows = conn.execute(
            f"""
            SELECT
              s.section_id,
              s.name,
              s.source,
              s.url,
              COALESCE(MIN(ft.feat_type), 'general') AS feat_type,
              s.description,
              s.body
            FROM sections s
            LEFT JOIN feat_types ft ON ft.section_id = s.section_id
            WHERE s.type = 'feat' AND lower(s.name) IN ({placeholders})
            GROUP BY s.section_id, s.name, s.source, s.url, s.description, s.body
            ORDER BY lower(s.name)
            """,
            tuple(target_feats),
        ).fetchall()

        for feat_row in feat_rows:
            child_rows = conn.execute(
                """
                SELECT name, description, body
                FROM sections
                WHERE parent_id = ?
                ORDER BY lft
                """,
                (int(feat_row["section_id"]),),
            ).fetchall()
            prerequisites = ""
            benefit = ""
            for child in child_rows:
                child_name = str(child["name"] or "").strip().lower()
                if child_name.startswith("prereq"):
                    prerequisites = _strip_html(child["description"] or child["body"])
                if child_name.startswith("benefit"):
                    benefit = _strip_html(child["body"] or child["description"])
            if not benefit:
                benefit = _strip_html(feat_row["description"] or feat_row["body"])

            records.append(
                _record(
                    "feat",
                    feat_row["url"] or "",
                    feat_row["source"] or "Core Rulebook",
                    {
                        "name": str(feat_row["name"] or "").strip(),
                        "feat_type": _feat_type_normalized(feat_row["feat_type"]),
                        "prerequisites": prerequisites,
                        "benefit": benefit,
                    },
                )
            )

    return records


def _extract_reactionary_trait_record(psrd_root: Path) -> list[dict]:
    preferred = [psrd_root / "book-ucampaign.db", psrd_root / "book-apg.db"]
    for db_path in preferred:
        if not db_path.exists():
            continue
        with _open_db(db_path) as conn:
            row = conn.execute(
                """
                SELECT section_id, name, subtype, source, url, description, body
                FROM sections
                WHERE type = 'trait' AND lower(name) = 'reactionary'
                ORDER BY section_id
                LIMIT 1
                """
            ).fetchone()
            if not row:
                continue

            body_text = _strip_html(row["body"] or row["description"])
            benefit = ""
            gain_match = re.search(r"(You gain[^.]*\.)", body_text, flags=re.IGNORECASE)
            if gain_match:
                benefit = gain_match.group(1).strip()

            return [
                _record(
                    "trait",
                    row["url"] or "",
                    row["source"] or "Ultimate Campaign",
                    {
                        "name": "Reactionary",
                        "trait_type": str(row["subtype"] or "combat").lower(),
                        "prerequisites": "",
                        "benefit": benefit,
                        "description": body_text,
                    },
                )
            ]
    return []


def _extract_reactionary_from_d20(d20_root: Path) -> list[dict]:
    traits_path = d20_root / "parsed" / "traits.json"
    if not traits_path.exists():
        return []
    parsed = read_json(traits_path)
    if not isinstance(parsed, list):
        return []

    for row in parsed:
        if not isinstance(row, dict):
            continue
        if str(row.get("name", "")).strip().lower() != "reactionary":
            continue
        return [
            _record(
                "trait",
                str(row.get("url", "")),
                str(row.get("source", "")).strip() or "d20pfsrd curated",
                {
                    "name": "Reactionary",
                    "trait_type": str(row.get("trait_type", "combat")).strip().lower(),
                    "prerequisites": str(row.get("prerequisites", "")).strip(),
                    "benefit": str(row.get("benefit", "")).strip(),
                    "description": _strip_html(row.get("description", "")),
                },
            )
        ]
    return []


def _extract_haste_records(psrd_root: Path) -> list[dict]:
    cr_db = psrd_root / "book-cr.db"
    if not cr_db.exists():
        return []

    records: list[dict] = []
    with _open_db(cr_db) as conn:
        row = conn.execute(
            """
            SELECT section_id, name, source, url, description, body
            FROM sections
            WHERE type = 'spell' AND lower(name) = 'haste'
            ORDER BY section_id
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return records

        details = conn.execute(
            """
            SELECT school
            FROM spell_details
            WHERE section_id = ?
            ORDER BY spell_detail_id
            LIMIT 1
            """,
            (int(row["section_id"]),),
        ).fetchone()
        school = str((details["school"] if details else "") or "").strip().lower()
        records.append(
            _record(
                "spell",
                row["url"] or "",
                row["source"] or "Core Rulebook",
                {"name": "Haste", "school": school, "description": _strip_html(row["body"] or row["description"])},
            )
        )

        investigator_level = conn.execute(
            """
            SELECT level
            FROM spell_lists
            WHERE section_id = ? AND lower(class) = 'investigator'
            ORDER BY spell_list_id
            LIMIT 1
            """,
            (int(row["section_id"]),),
        ).fetchone()
        if investigator_level:
            level = int(investigator_level["level"])
        else:
            alchemist_level = conn.execute(
                """
                SELECT level
                FROM spell_lists
                WHERE section_id = ? AND lower(class) = 'alchemist'
                ORDER BY spell_list_id
                LIMIT 1
                """,
                (int(row["section_id"]),),
            ).fetchone()
            level = int(alchemist_level["level"]) if alchemist_level else 3

        records.append(
            _record(
                "spell_class_level",
                row["url"] or "",
                row["source"] or "Core Rulebook",
                {"spell_name": "Haste", "class_name": "Investigator", "level": level},
            )
        )

    return records


def _extract_equipment_records(psrd_root: Path) -> list[dict]:
    cr_db = psrd_root / "book-cr.db"
    if not cr_db.exists():
        return []

    records: list[dict] = []
    targets = ["rapier", "studded leather"]
    placeholders = ",".join(["?"] * len(targets))

    with _open_db(cr_db) as conn:
        item_rows = conn.execute(
            f"""
            SELECT section_id, name, source, url, description, body
            FROM sections
            WHERE type = 'item' AND lower(name) IN ({placeholders})
            ORDER BY lower(name)
            """,
            tuple(targets),
        ).fetchall()

        for row in item_rows:
            item_id = int(row["section_id"])
            detail = conn.execute(
                """
                SELECT price, weight
                FROM item_details
                WHERE section_id = ?
                ORDER BY item_details_id
                LIMIT 1
                """,
                (item_id,),
            ).fetchone()
            misc_rows = conn.execute(
                """
                SELECT field, value
                FROM item_misc
                WHERE section_id = ?
                ORDER BY item_misc_id
                """,
                (item_id,),
            ).fetchall()
            misc = {str(m["field"] or "").strip().lower(): _strip_html(m["value"]) for m in misc_rows}

            item_name = str(row["name"] or "").strip()
            lowered = item_name.lower()
            equipment_type = "weapon" if lowered == "rapier" else "armor"
            weight = _parse_weight(detail["weight"] if detail else None)

            records.append(
                _record(
                    "equipment",
                    row["url"] or "",
                    row["source"] or "Core Rulebook",
                    {
                        "name": item_name,
                        "equipment_type": equipment_type,
                        "cost": str((detail["price"] if detail else "") or "").strip(),
                        "weight": weight,
                        "description": _strip_html(row["body"] or row["description"]),
                    },
                )
            )

            if lowered == "rapier":
                proficiency_raw = misc.get("proficiency", "").lower()
                if "martial" in proficiency_raw:
                    proficiency = "martial"
                elif "simple" in proficiency_raw:
                    proficiency = "simple"
                elif "exotic" in proficiency_raw:
                    proficiency = "exotic"
                else:
                    proficiency = proficiency_raw or "martial"

                weapon_class = misc.get("weapon class", "").lower()
                weapon_type = "ranged" if "ranged" in weapon_class else "melee"
                handedness = "one-handed"
                if "two-handed" in weapon_class:
                    handedness = "two-handed"
                if "light" in weapon_class:
                    handedness = "light"

                records.append(
                    _record(
                        "weapon",
                        row["url"] or "",
                        row["source"] or "Core Rulebook",
                        {
                            "equipment_name": item_name,
                            "proficiency": proficiency,
                            "weapon_type": weapon_type,
                            "handedness": handedness,
                            "damage_medium": misc.get("dmg (m)", ""),
                            "critical": misc.get("critical", ""),
                        },
                    )
                )
            if lowered == "studded leather":
                armor_type = misc.get("armor type", "").lower().replace(" armor", "").strip()
                records.append(
                    _record(
                        "armor",
                        row["url"] or "",
                        row["source"] or "Core Rulebook",
                        {
                            "equipment_name": item_name,
                            "armor_type": armor_type or "light",
                            "armor_bonus": _parse_int(misc.get("armor bonus")),
                            "max_dex": _parse_int(misc.get("maximum dex bonus")),
                            "armor_check_penalty": _parse_int(misc.get("armor check penalty")),
                            "arcane_spell_failure": _parse_int(misc.get("arcane spell failure chance")),
                        },
                    )
                )

    return records


def _extract_kairon_slice_psrd_records(psrd_root: Path, d20_root: Path | None = None) -> list[dict]:
    records: list[dict] = []
    records.extend(_extract_investigator_class_records(psrd_root))
    records.extend(_extract_tiefling_records(psrd_root))
    records.extend(_extract_feat_records(psrd_root))
    records.extend(_extract_reactionary_trait_record(psrd_root))
    records.extend(_extract_haste_records(psrd_root))
    records.extend(_extract_equipment_records(psrd_root))

    if not any(r.get("content_type") == "trait" and r.get("payload", {}).get("name") == "Reactionary" for r in records):
        if d20_root:
            records.extend(_extract_reactionary_from_d20(d20_root))

    return _dedupe_records(records)


def _extract_kairon_slice_aon_records(
    *,
    run_path: Path,
    ai_short_fallback: bool = False,
    aon_timeout: int = 20,
    aon_max_retries: int = 1,
    aon_offline_html_dir: Path | None = None,
) -> tuple[list[dict], list[dict]]:
    raw_dir = run_path / "raw"
    html_dir = raw_dir / "html"
    fetch_logs: list[dict] = []

    ordered_urls = [
        _AON_KAIRON_URLS["class_investigator"],
        _AON_KAIRON_URLS["race_tiefling"],
        _AON_KAIRON_URLS["feat_weapon_finesse"],
        _AON_KAIRON_URLS["feat_weapon_focus"],
        _AON_KAIRON_URLS["feat_rapid_shot"],
        _AON_KAIRON_URLS["trait_reactionary"],
        _AON_KAIRON_URLS["spell_haste"],
        _AON_KAIRON_URLS["spell_list_all"],
        _AON_KAIRON_URLS["weapons_overview"],
        _AON_KAIRON_URLS["armor_overview"],
    ]
    for url in ordered_urls:
        fetch_logs.append(
            _fetch_aon_page(
                url,
                html_dir,
                timeout=aon_timeout,
                max_retries=aon_max_retries,
                offline_html_dir=aon_offline_html_dir,
            )
        )
    write_jsonl(raw_dir / "aon_fetch_log.jsonl", fetch_logs)

    html_by_url: dict[str, str] = {}
    for log_row in fetch_logs:
        rel_file = log_row.get("html_file", "")
        if not rel_file:
            continue
        page_path = raw_dir / rel_file
        if page_path.exists():
            html_by_url[str(log_row["url"])] = page_path.read_text(encoding="utf-8")

    records: list[dict] = []

    # Investigator class (with deterministic progression baseline).
    class_html = html_by_url.get(_AON_KAIRON_URLS["class_investigator"], "")
    class_name = _extract_heading_from_html(class_html) or "Investigator"
    records.append(
        _record(
            "class",
            _AON_KAIRON_URLS["class_investigator"],
            "Advanced Class Guide",
            {
                "name": class_name,
                "class_type": "hybrid",
                "hit_die": "d8",
                "skill_ranks_per_level": _INVESTIGATOR_PROFILE["skill_ranks_per_level"],
                "bab_progression": _INVESTIGATOR_PROFILE["bab_progression"],
                "fort_progression": _INVESTIGATOR_PROFILE["fort_progression"],
                "ref_progression": _INVESTIGATOR_PROFILE["ref_progression"],
                "will_progression": _INVESTIGATOR_PROFILE["will_progression"],
                "description": _strip_html(class_html)[:1200] if class_html else "",
            },
        )
    )
    specials = {9: "trapfinding, inspiration, studied combat"}
    spell_map = {9: {"1": 5, "2": 4, "3": 3}}
    for level in range(1, 21):
        records.append(
            _record(
                "class_progression",
                _AON_KAIRON_URLS["class_investigator"],
                "Advanced Class Guide",
                {
                    "class_name": "Investigator",
                    "level": level,
                    "bab": _bab_for_level(level, _INVESTIGATOR_PROFILE["bab_progression"]),
                    "fort_save": _save_for_level(level, _INVESTIGATOR_PROFILE["fort_progression"]),
                    "ref_save": _save_for_level(level, _INVESTIGATOR_PROFILE["ref_progression"]),
                    "will_save": _save_for_level(level, _INVESTIGATOR_PROFILE["will_progression"]),
                    "special": specials.get(level, ""),
                    "spells_per_day": spell_map.get(level, {}),
                },
            )
        )

    # Tiefling + one guaranteed racial trait.
    race_html = html_by_url.get(_AON_KAIRON_URLS["race_tiefling"], "")
    race_heading = _extract_heading_from_html(race_html).strip()
    race_name = "Tiefling" if "tiefling" in race_heading.lower() or not race_heading else race_heading
    records.append(
        _record(
            "race",
            _AON_KAIRON_URLS["race_tiefling"],
            "Advanced Race Guide",
            {"name": race_name, "race_type": "featured", "size": "Medium", "base_speed": 30},
        )
    )
    records.append(
        _record(
            "racial_trait",
            _AON_KAIRON_URLS["race_tiefling"],
            "Advanced Race Guide",
            {
                "race_name": "Tiefling",
                "name": "Darkvision",
                "trait_type": "senses",
                "description": "Tieflings can see in darkness up to 60 feet.",
                "replaces": "",
            },
        )
    )

    # Feats with parsed + fallback data.
    feat_specs = [
        ("Weapon Finesse", _AON_KAIRON_URLS["feat_weapon_finesse"]),
        ("Weapon Focus", _AON_KAIRON_URLS["feat_weapon_focus"]),
        ("Rapid Shot", _AON_KAIRON_URLS["feat_rapid_shot"]),
    ]
    for feat_name, feat_url in feat_specs:
        fallback = _AON_KAIRON_FALLBACK["feats"][feat_name]["payload"]
        feat_html = html_by_url.get(feat_url, "")
        feat_text = _strip_html(feat_html)
        prereq = _extract_field_text(feat_text, ["Prerequisites", "Prerequisite"]) or fallback["prerequisites"]
        benefit = _extract_field_text(feat_text, ["Benefit", "Benefits"]) or fallback["benefit"]
        short_text, short_src = _ai_short_description(text=benefit or feat_text, enabled=ai_short_fallback)
        records.append(
            _record(
                "feat",
                feat_url,
                "Core Rulebook",
                {
                    "name": feat_name,
                    "feat_type": "combat",
                    "prerequisites": prereq,
                    "benefit": benefit,
                    "short_description": short_text,
                    "short_description_source": short_src,
                    "description": feat_text[:2000],
                },
            )
        )

    # Trait: Reactionary
    trait_html = html_by_url.get(_AON_KAIRON_URLS["trait_reactionary"], "")
    trait_text = _strip_html(trait_html)
    trait_fallback = _AON_KAIRON_FALLBACK["trait_reactionary"]["payload"]
    trait_benefit = _extract_field_text(trait_text, ["Benefit"]) or trait_fallback["benefit"]
    records.append(
        _record(
            "trait",
            _AON_KAIRON_URLS["trait_reactionary"],
            "Ultimate Campaign",
            {
                "name": "Reactionary",
                "trait_type": "combat",
                "prerequisites": "",
                "benefit": trait_benefit,
                "description": trait_text or trait_fallback["description"],
            },
        )
    )

    # Spell: Haste (short from list page when possible + full from display page).
    spell_html = html_by_url.get(_AON_KAIRON_URLS["spell_haste"], "")
    spell_text = _strip_html(spell_html)
    list_text = _strip_html(html_by_url.get(_AON_KAIRON_URLS["spell_list_all"], ""))
    short_from_list = _extract_spell_short_from_list_page(list_text, "Haste")
    spell_fallback = _AON_KAIRON_FALLBACK["spell_haste"]["payload"]
    short_text, short_src = _ai_short_description(
        text=short_from_list or spell_text or spell_fallback["short_description"],
        enabled=ai_short_fallback,
    )
    records.append(
        _record(
            "spell",
            _AON_KAIRON_URLS["spell_haste"],
            "Core Rulebook",
            {
                "name": "Haste",
                "school": "transmutation",
                "short_description": short_from_list or short_text or spell_fallback["short_description"],
                "short_description_source": "aon:list_page" if short_from_list else short_src,
                "description": spell_text or spell_fallback["description"],
            },
        )
    )
    records.append(
        _record(
            "spell_class_level",
            _AON_KAIRON_URLS["spell_haste"],
            "Core Rulebook",
            {"spell_name": "Haste", "class_name": "Investigator", "level": 3},
        )
    )

    # Equipment baseline (AON pages archived; values deterministic from rules baseline).
    records.append(
        _record(
            "equipment",
            _AON_KAIRON_FALLBACK["equipment_rapier"]["source_url"],
            _AON_KAIRON_FALLBACK["equipment_rapier"]["source_book"],
            dict(_AON_KAIRON_FALLBACK["equipment_rapier"]["payload"]),
        )
    )
    records.append(
        _record(
            "weapon",
            _AON_KAIRON_FALLBACK["weapon_rapier"]["source_url"],
            _AON_KAIRON_FALLBACK["weapon_rapier"]["source_book"],
            dict(_AON_KAIRON_FALLBACK["weapon_rapier"]["payload"]),
        )
    )
    records.append(
        _record(
            "equipment",
            _AON_KAIRON_FALLBACK["equipment_studded_leather"]["source_url"],
            _AON_KAIRON_FALLBACK["equipment_studded_leather"]["source_book"],
            dict(_AON_KAIRON_FALLBACK["equipment_studded_leather"]["payload"]),
        )
    )
    records.append(
        _record(
            "armor",
            _AON_KAIRON_FALLBACK["armor_studded_leather"]["source_url"],
            _AON_KAIRON_FALLBACK["armor_studded_leather"]["source_book"],
            dict(_AON_KAIRON_FALLBACK["armor_studded_leather"]["payload"]),
        )
    )

    # Hard fallback guard to ensure required entities survive fetch/parse failures.
    fallback_records = [
        _record("class", _AON_KAIRON_FALLBACK["class"]["source_url"], _AON_KAIRON_FALLBACK["class"]["source_book"], dict(_AON_KAIRON_FALLBACK["class"]["payload"])),
        _record("race", _AON_KAIRON_FALLBACK["race"]["source_url"], _AON_KAIRON_FALLBACK["race"]["source_book"], dict(_AON_KAIRON_FALLBACK["race"]["payload"])),
        _record("racial_trait", _AON_KAIRON_FALLBACK["racial_trait"]["source_url"], _AON_KAIRON_FALLBACK["racial_trait"]["source_book"], dict(_AON_KAIRON_FALLBACK["racial_trait"]["payload"])),
        _record("trait", _AON_KAIRON_FALLBACK["trait_reactionary"]["source_url"], _AON_KAIRON_FALLBACK["trait_reactionary"]["source_book"], dict(_AON_KAIRON_FALLBACK["trait_reactionary"]["payload"])),
        _record("spell", _AON_KAIRON_FALLBACK["spell_haste"]["source_url"], _AON_KAIRON_FALLBACK["spell_haste"]["source_book"], dict(_AON_KAIRON_FALLBACK["spell_haste"]["payload"])),
        _record("spell_class_level", _AON_KAIRON_FALLBACK["spell_class_level_haste"]["source_url"], _AON_KAIRON_FALLBACK["spell_class_level_haste"]["source_book"], dict(_AON_KAIRON_FALLBACK["spell_class_level_haste"]["payload"])),
    ]
    for feat_name in ("Weapon Finesse", "Weapon Focus", "Rapid Shot"):
        feat_fallback = _AON_KAIRON_FALLBACK["feats"][feat_name]
        fallback_records.append(_record("feat", feat_fallback["source_url"], feat_fallback["source_book"], dict(feat_fallback["payload"])))

    records.extend(fallback_records)
    deduped = _dedupe_records(records)
    return deduped, fetch_logs


def run_extract(
    source: str,
    run_dir: Path,
    input_path: Path | None = None,
    run_key: str | None = None,
    mode: str = "kairon_fixture",
    psrd_root: Path | None = None,
    d20_root: Path | None = None,
    aon_timeout: int = 20,
    aon_max_retries: int = 1,
    ai_short_fallback: bool = False,
    aon_offline_html_dir: Path | None = None,
) -> Path:
    if mode == "aon_live" and source != "aon":
        raise ValueError("mode=aon_live requires --source aon")
    if source == "aon" and not input_path and mode != "aon_live":
        raise ValueError("source=aon requires --mode aon_live (unless --input is used)")

    if run_key is None:
        run_key = f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{source}"

    run_path = run_dir / run_key
    raw_dir = run_path / "raw"
    ensure_dir(raw_dir)

    used_psrd_root: Path | None = None
    used_d20_root: Path | None = None
    aon_fetch_log: list[dict] = []

    if input_path:
        records = _normalize_input_records(read_json(input_path))
    elif mode == "aon_live" and source == "aon":
        records, aon_fetch_log = _extract_kairon_slice_aon_records(
            run_path=run_path,
            ai_short_fallback=ai_short_fallback,
            aon_timeout=aon_timeout,
            aon_max_retries=aon_max_retries,
            aon_offline_html_dir=aon_offline_html_dir,
        )
    elif mode == "kairon_slice" and source == "psrd":
        used_psrd_root = _resolve_source_root(psrd_root, "PF1E_PSRD_ROOT", Path("data") / "psrd")
        if used_psrd_root is None:
            raise FileNotFoundError(
                "PSRD source root not found. Set --psrd-root or PF1E_PSRD_ROOT, or run in fixture mode."
            )
        used_d20_root = _resolve_source_root(d20_root, "PF1E_D20_ROOT", Path("data") / "d20pfsrd")
        records = _extract_kairon_slice_psrd_records(used_psrd_root, used_d20_root)
    else:
        records = kairon_slice_records(source)

    prepared: list[dict] = []
    for rec in records:
        serial = stable_json_dumps(rec)
        raw_hash = sha256_text(serial)
        prepared.append(
            {
                "record_key": raw_hash[:12],
                "raw_hash": raw_hash,
                "source_name": source,
                "source_url": rec.get("source_url", ""),
                "source_book": rec.get("source_book", "Unknown"),
                "content_type": rec.get("content_type", "unknown"),
                "license_tag": rec.get("license_tag", "OGL"),
                "payload": rec.get("payload", {}),
            }
        )

    write_jsonl(raw_dir / "source_records.jsonl", prepared)

    manifest = {
        "run_key": run_key,
        "source": source,
        "mode": mode,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "record_count": len(prepared),
        "raw_hash": sha256_text(stable_json_dumps(prepared)),
    }
    if used_psrd_root:
        manifest["psrd_root"] = str(used_psrd_root)
    if used_d20_root:
        manifest["d20_root"] = str(used_d20_root)
    if mode == "aon_live":
        manifest["aon"] = {
            "timeout": aon_timeout,
            "max_retries": aon_max_retries,
            "ai_short_fallback": ai_short_fallback,
            "fetched_pages": len([r for r in aon_fetch_log if r.get("status") in {"fetched", "offline"}]),
            "failed_pages": len([r for r in aon_fetch_log if r.get("status") == "error"]),
        }
        if aon_offline_html_dir:
            manifest["aon"]["offline_html_dir"] = str(aon_offline_html_dir)

    write_json(run_path / "manifest.json", manifest)
    return run_path
