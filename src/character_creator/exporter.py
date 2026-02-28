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

    # AC — include armor/shield bonus from equipped items
    dex_mod = mods["dex"]
    armor_bonus = 0
    shield_bonus = 0
    max_dex_from_armor: int | None = None

    equipped_armor = char.get("equipped_armor")  # dict or None
    equipped_shield = char.get("equipped_shield")  # dict or None

    if equipped_armor:
        armor_bonus = equipped_armor.get("armor_bonus", 0) or 0
        md = equipped_armor.get("max_dex")
        if md is not None:
            max_dex_from_armor = md

    if equipped_shield:
        shield_bonus = equipped_shield.get("armor_bonus", 0) or 0

    # Apply max_dex cap from armor
    effective_dex_mod = dex_mod
    if max_dex_from_armor is not None:
        effective_dex_mod = min(dex_mod, max_dex_from_armor)

    ac_total = 10 + effective_dex_mod + armor_bonus + shield_bonus
    ac_touch = 10 + dex_mod  # touch ignores armor/shield
    ac_ff = 10 + armor_bonus + shield_bonus  # flat-footed ignores dex

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

    # Weapon attack/damage bonuses
    weapons_derived = []
    for w in char.get("weapons", []):
        w_name = w.get("name", "Unknown")
        w_handedness = (w.get("handedness") or "").lower()
        # Melee: STR to attack and damage; finesse weapons may use DEX
        is_finesse = "finesse" in (w.get("special") or "").lower()
        if w.get("weapon_type") == "ranged":
            atk_mod = mods["dex"]
            dmg_mod = 0  # composite bows use STR; simplified here
        elif is_finesse:
            atk_mod = max(mods["str"], mods["dex"])
            dmg_mod = mods["str"]
        else:
            atk_mod = mods["str"]
            dmg_mod = mods["str"]

        atk_bonus = bab + atk_mod
        # Build iterative attack string (iteratives based on BAB, not total)
        # BAB 1-5 → 1 attack; 6-10 → 2; 11-15 → 3; 16+ → 4
        num_attacks = 1 + max(0, (bab - 1) // 5)
        attacks = []
        for i in range(num_attacks):
            ab = atk_bonus - (i * 5)
            sign = "+" if ab >= 0 else ""
            attacks.append(f"{sign}{ab}")
        atk_str = "/".join(attacks) if attacks else "+0"

        dmg_str = w.get("damage_medium") or ""
        if dmg_mod != 0:
            sign = "+" if dmg_mod >= 0 else ""
            dmg_str += f"{sign}{dmg_mod}"

        weapons_derived.append({
            "name": w_name,
            "attack": atk_str,
            "damage": dmg_str,
            "critical": w.get("critical") or "×2",
            "range": w.get("range_increment") or "—",
            "type": w.get("damage_type") or "",
            "special": w.get("special") or "",
        })

    return {
        "bab": bab,
        "fort": fort,
        "ref": ref,
        "will": will,
        "ac": {
            "total": ac_total,
            "touch": ac_touch,
            "flat_footed": ac_ff,
            "armor_bonus": armor_bonus,
            "shield_bonus": shield_bonus,
            "dex_mod": effective_dex_mod,
        },
        "cmb": cmb,
        "cmd": cmd,
        "initiative": initiative,
        "total_level": total_level,
        "hp_max": hp_max,
        "hp_current": hp_current,
        "skill_totals": skill_totals,
        "ability_mods": mods,
        "class_features": class_features,
        "feat_details": char.get("feat_details", []),
        "weapons_derived": weapons_derived,
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
