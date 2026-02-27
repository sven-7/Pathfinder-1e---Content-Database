"""Character sheet exporter — generates standalone HTML from a character dict."""

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.db import RulesDB

ROOT = pathlib.Path(__file__).parent.parent.parent
SHEET_TEMPLATE = ROOT / "static" / "sheet.html"
CHARS_DIR = ROOT / "characters"

_PLACEHOLDER = "__CHAR_DATA__"


def _compute_derived(char: dict, db: "RulesDB") -> dict:
    """Compute derived stats from the character dict using the rules engine."""
    from src.rules_engine import Character, ClassLevel, get_bab, get_save, get_hp
    from src.rules_engine.skills import _ability_for_skill, get_class_skills
    from src.character_creator.builder import CLASS_HIT_DIE, CLASS_SKILL_RANKS, HIT_DIE_AVG

    cls_levels = [ClassLevel.from_dict(cl) for cl in char.get("class_levels", [])]
    char_obj = Character(
        name=char.get("name", ""),
        race=char.get("race", ""),
        alignment=char.get("alignment", ""),
        ability_scores=char.get("ability_scores", {}),
        class_levels=cls_levels,
        feats=char.get("feats", []),
        traits=char.get("traits", []),
        skills=char.get("skills", {}),
        equipment=char.get("equipment", []),
        conditions=char.get("conditions", []),
    )

    scores = char_obj.ability_scores
    mods = {ab: (scores.get(ab, 10) - 10) // 2 for ab in ("str", "dex", "con", "int", "wis", "cha")}

    # BAB and saves
    try:
        bab = get_bab(cls_levels, db)
        fort_base = get_save(cls_levels, "fort", db)
        ref_base = get_save(cls_levels, "ref", db)
        will_base = get_save(cls_levels, "will", db)
    except Exception:
        bab = 0
        fort_base = ref_base = will_base = 0

    fort = fort_base + mods["con"]
    ref = ref_base + mods["dex"]
    will = will_base + mods["wis"]

    # AC
    dex_mod = mods["dex"]
    ac_total = 10 + dex_mod
    ac_touch = 10 + dex_mod
    ac_ff = 10

    # CMB / CMD
    total_level = sum(cl.level for cl in cls_levels)
    cmb = bab + mods["str"]
    cmd = 10 + bab + mods["str"] + mods["dex"]
    initiative = mods["dex"]

    # HP
    class_name = cls_levels[0].class_name if cls_levels else "Fighter"
    hp_max = char.get("hp_max", 0)
    if not hp_max:
        hit_die = CLASS_HIT_DIE.get(class_name, "d8")
        hp_max = max(1, HIT_DIE_AVG.get(hit_die, 5) + mods["con"])
    hp_current = char.get("hp_current", hp_max)

    # Skills
    skill_totals = {}
    class_skill_names: set[str] = set()
    if cls_levels:
        row = db.get_class(cls_levels[0].class_name)
        if row:
            for sk in db.get_class_skills(row["id"]):
                class_skill_names.add(sk["name"].lower())

    all_skills = db.get_all_skills()
    for sk in all_skills:
        sk_name = sk["name"]
        ranks = char.get("skills", {}).get(sk_name, 0)
        ab = _ability_for_skill(sk_name)
        ab_mod = mods.get(ab, 0)
        trained_bonus = 3 if (ranks > 0 and sk_name.lower() in class_skill_names) else 0
        skill_totals[sk_name] = {
            "ranks": ranks,
            "ability": ab,
            "ability_mod": ab_mod,
            "trained_bonus": trained_bonus,
            "total": ranks + ab_mod + trained_bonus,
            "is_class_skill": sk_name.lower() in class_skill_names,
        }

    # Class features from progression table
    class_features: list[str] = []
    if cls_levels:
        cl = cls_levels[0]
        class_row = db.get_class(cl.class_name)
        if class_row:
            progression = db.get_class_progression(class_row["id"])
            for prog_row in progression:
                if prog_row["level"] <= cl.level:
                    special = prog_row.get("special") or ""
                    for feat_name in special.split(","):
                        feat_name = feat_name.strip()
                        if feat_name:
                            class_features.append(feat_name)
        # Archetype features (if selected)
        if cl.archetype_name:
            arch_row = db.get_archetype_for_class(cl.class_name, cl.archetype_name)
            if arch_row:
                arch_features = db.get_archetype_features(arch_row["id"])
                for af in arch_features:
                    if af.get("level") is None or af["level"] <= cl.level:
                        name = (af.get("name") or "").strip()
                        if name:
                            class_features.append(f"{name} [Archetype]")

    return {
        "bab": bab,
        "fort": fort,
        "ref": ref,
        "will": will,
        "ac": {"total": ac_total, "touch": ac_touch, "flat_footed": ac_ff},
        "cmb": cmb,
        "cmd": cmd,
        "initiative": initiative,
        "total_level": total_level,
        "hp_max": hp_max,
        "hp_current": hp_current,
        "skill_totals": skill_totals,
        "ability_mods": mods,
        "class_features": class_features,
    }


def generate_sheet_html(char: dict, db: "RulesDB") -> str:
    """Generate a self-contained character sheet HTML string."""
    if not SHEET_TEMPLATE.exists():
        raise FileNotFoundError(f"Sheet template not found: {SHEET_TEMPLATE}")

    derived = _compute_derived(char, db)
    payload = {**char, "derived": derived}
    json_str = json.dumps(payload, ensure_ascii=False)

    template_html = SHEET_TEMPLATE.read_text(encoding="utf-8")
    return template_html.replace(_PLACEHOLDER, json_str)


def export_to_file(char: dict, db: "RulesDB", output_path: pathlib.Path | None = None) -> pathlib.Path:
    """Write a standalone character sheet HTML to disk. Returns the path."""
    if output_path is None:
        char_id = char.get("id", "character")
        char_name = char.get("name", "character").replace(" ", "_")
        CHARS_DIR.mkdir(exist_ok=True)
        output_path = CHARS_DIR / f"{char_name}_{char_id[:8]}.html"

    html = generate_sheet_html(char, db)
    output_path.write_text(html, encoding="utf-8")
    return output_path
