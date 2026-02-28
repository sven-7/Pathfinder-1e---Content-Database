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


def _compute_class_resources(cls_levels: list, mods: dict) -> list:
    """Return list of class resource pool dicts for display on the sheet."""
    resources = []
    for cl in cls_levels:
        cn = cl.class_name
        lvl = cl.level
        if cn in ("Barbarian", "Unchained Barbarian"):
            uses = 4 + lvl + mods["con"]
            resources.append({"name": "Rage", "uses_per_day": max(1, uses),
                               "label": "Rage Rounds/Day", "resource_type": "rounds"})
        elif cn in ("Monk", "Unchained Monk"):
            uses = lvl // 2 + mods["wis"]
            resources.append({"name": "Ki Pool", "uses_per_day": max(1, uses),
                               "label": "Ki Points", "resource_type": "points"})
        elif cn == "Paladin":
            uses = max(1, mods["cha"])
            resources.append({"name": "Lay on Hands", "uses_per_day": max(1, lvl // 2 * uses),
                               "label": "Lay on Hands/Day", "resource_type": "uses"})
            if lvl >= 4:
                smite = max(1, (lvl + 2) // 3)
                resources.append({"name": "Smite Evil", "uses_per_day": smite,
                                   "label": "Smite Evil/Day", "resource_type": "uses"})
        elif cn == "Cleric":
            chan_pool = max(1, 3 + mods["cha"])
            resources.append({"name": "Channel Energy", "uses_per_day": chan_pool,
                               "label": "Channel Energy/Day", "resource_type": "uses"})
        elif cn == "Druid":
            if lvl >= 2:
                wild = 1 + (lvl - 2) // 2
                resources.append({"name": "Wild Shape", "uses_per_day": wild,
                                   "label": "Wild Shape/Day", "resource_type": "uses"})
        elif cn == "Gunslinger":
            grit = max(1, mods["wis"])
            resources.append({"name": "Grit", "uses_per_day": grit,
                               "label": "Grit Points", "resource_type": "points"})
        elif cn == "Swashbuckler":
            panache = max(1, mods["cha"])
            resources.append({"name": "Panache", "uses_per_day": panache,
                               "label": "Panache Points", "resource_type": "points"})
        elif cn in ("Investigator", "Alchemist"):
            label = "Inspiration" if cn == "Investigator" else "Extracts"
            uses = lvl + mods["int"]
            resources.append({"name": label, "uses_per_day": max(1, uses),
                               "label": f"{label} Prepared", "resource_type": "uses"})
        elif cn == "Magus":
            pool = max(1, lvl // 2 + mods["int"])
            resources.append({"name": "Arcane Pool", "uses_per_day": pool,
                               "label": "Arcane Pool Points", "resource_type": "points"})
        elif cn == "Ninja":
            ki = max(1, lvl // 2 + mods["cha"])
            resources.append({"name": "Ki Pool", "uses_per_day": ki,
                               "label": "Ki Points", "resource_type": "points"})
        elif cn == "Samurai":
            resolve = max(1, (lvl + 1) // 2)
            resources.append({"name": "Resolve", "uses_per_day": resolve,
                               "label": "Resolve Points", "resource_type": "points"})
    return resources


def _compute_derived(char: dict, db: "RulesDB") -> dict:
    """Compute derived stats from the character dict using the rules engine."""
    from src.rules_engine import Character, ClassLevel, get_bab, get_save, get_hp
    from src.rules_engine.skills import _ability_for_skill, get_class_skills

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

    # HP — always recompute from rules engine (character JSON hp_max may be stale)
    fav_class_choice = char.get("fav_class_choice", "")
    favored_class_hp = total_level if fav_class_choice == "hp" else 0
    hp_max = get_hp(cls_levels, mods["con"], favored_class_hp, db)
    hp_current = char.get("hp_current", hp_max)

    # Skills
    skill_totals = {}
    class_skill_names: set[str] = set()
    for cl in cls_levels:
        row = db.get_class(cl.class_name)
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
            has_special = False
            for prog_row in progression:
                if prog_row["level"] <= cl.level:
                    special = prog_row.get("special") or ""
                    for feat_name in special.split(","):
                        feat_name = feat_name.strip()
                        if feat_name:
                            class_features.append(feat_name)
                            has_special = True
            # OA classes have no special text; fall back to class_features table
            if not has_special:
                for cf in db.get_class_features(class_row["id"]):
                    cf_level = cf.get("level") or 0
                    if cf_level <= cl.level:
                        name = (cf.get("name") or "").strip()
                        if name:
                            class_features.append(name)
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

    # Spell slots
    from src.rules_engine.progression import get_spell_slots
    spell_slots_all: dict = {}
    for cl in cls_levels:
        slots = get_spell_slots(cl.class_name, cl.level, db)
        if slots:
            spell_slots_all[cl.class_name] = slots

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
        "spell_slots": spell_slots_all,
        "class_resources": _compute_class_resources(cls_levels, mods),
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
