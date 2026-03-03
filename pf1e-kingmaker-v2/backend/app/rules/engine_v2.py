"""Deterministic PF1e rules engine for the Kairon V2 vertical slice."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.contracts import (
    AttackLineV2,
    BreakdownLineV2,
    CharacterV2,
    DerivedStatsV2,
    FeatPrereqResultV2,
    RuleOverrideV2,
)


@dataclass(frozen=True)
class ClassRule:
    hit_die: int
    bab_progression: str
    fort_progression: str
    ref_progression: str
    will_progression: str
    class_skills: set[str]


@dataclass(frozen=True)
class ArmorRule:
    armor_bonus: int
    max_dex: int | None


@dataclass(frozen=True)
class WeaponRule:
    weapon_type: str
    handedness: str
    damage_medium: str
    critical: str
    finesse_eligible: bool


_CLASS_RULES = {
    "investigator": ClassRule(
        hit_die=8,
        bab_progression="three_quarter",
        fort_progression="poor",
        ref_progression="good",
        will_progression="good",
        class_skills={
            "Acrobatics",
            "Appraise",
            "Bluff",
            "Climb",
            "Craft",
            "Diplomacy",
            "Disable Device",
            "Disguise",
            "Escape Artist",
            "Heal",
            "Intimidate",
            "Knowledge (all)",
            "Linguistics",
            "Perception",
            "Perform",
            "Profession",
            "Sense Motive",
            "Sleight of Hand",
            "Spellcraft",
            "Stealth",
            "Use Magic Device",
        },
    ),
}


_ARMOR_RULES = {
    "studded leather": ArmorRule(armor_bonus=3, max_dex=5),
}


_WEAPON_RULES = {
    "rapier": WeaponRule(
        weapon_type="melee",
        handedness="one-handed",
        damage_medium="1d6",
        critical="18-20/x2",
        finesse_eligible=True,
    ),
}


_SKILL_ABILITIES = {
    "Acrobatics": "dex",
    "Appraise": "int",
    "Bluff": "cha",
    "Climb": "str",
    "Craft": "int",
    "Diplomacy": "cha",
    "Disable Device": "dex",
    "Disguise": "cha",
    "Escape Artist": "dex",
    "Heal": "wis",
    "Intimidate": "cha",
    "Knowledge": "int",
    "Linguistics": "int",
    "Perception": "wis",
    "Perform": "cha",
    "Profession": "wis",
    "Ride": "dex",
    "Sense Motive": "wis",
    "Sleight of Hand": "dex",
    "Spellcraft": "int",
    "Stealth": "dex",
    "Survival": "wis",
    "Swim": "str",
    "Use Magic Device": "cha",
}


# Investigator base spell slots for level 9 slice; bonus slots are applied from INT modifier.
_INVESTIGATOR_BASE_SPELL_SLOTS = {9: {"1": 4, "2": 3, "3": 2}}


def _norm(text: str) -> str:
    return text.strip().lower()


def _mod(score: int) -> int:
    return (score - 10) // 2


def _bab_for_level(style: str, level: int) -> int:
    if style == "full":
        return level
    if style == "three_quarter":
        return (3 * level) // 4
    return level // 2


def _save_for_level(style: str, level: int) -> int:
    if style == "good":
        return 2 + (level // 2)
    return level // 3


def _trait_effect_total(character: CharacterV2, key: str) -> int:
    target = _norm(key)
    total = 0
    for trait in character.traits:
        for effect in trait.effects:
            if _norm(effect.key) == target:
                total += int(effect.delta)
    return total


def _skill_effect_total(character: CharacterV2, skill_name: str) -> int:
    target = _norm(f"skill:{skill_name}")
    total = 0
    for trait in character.traits:
        for effect in trait.effects:
            if _norm(effect.key) == target:
                total += int(effect.delta)
    return total


def _investigator_spell_slots(level: int, int_mod: int) -> dict[str, int]:
    base = dict(_INVESTIGATOR_BASE_SPELL_SLOTS.get(level, {}))
    out = {k: int(v) for k, v in base.items()}
    for lvl_text in list(out.keys()):
        spell_level = int(lvl_text)
        bonus = 0
        if int_mod >= spell_level:
            bonus = 1 + (int_mod - spell_level) // 4
        out[lvl_text] += max(0, bonus)
    return out


def evaluate_feat_prerequisites(character: CharacterV2, total_bab: int | None = None) -> list[FeatPrereqResultV2]:
    if total_bab is None:
        total_bab = 0
        for cl in character.class_levels:
            class_rule = _CLASS_RULES.get(_norm(cl.class_name))
            progression = class_rule.bab_progression if class_rule else "half"
            total_bab += _bab_for_level(progression, cl.level)

    feat_names = {_norm(f.name) for f in character.feats}
    has_equipped_weapon = any(eq.kind == "weapon" for eq in character.equipment)
    results: list[FeatPrereqResultV2] = []

    for feat in sorted(character.feats, key=lambda f: (f.level_gained, _norm(f.name))):
        name_norm = _norm(feat.name)
        missing: list[str] = []

        if name_norm == "weapon finesse":
            if total_bab < 1:
                missing.append("Base attack bonus +1")
        elif name_norm == "weapon focus":
            if total_bab < 1:
                missing.append("Base attack bonus +1")
            if not has_equipped_weapon:
                missing.append("Proficiency with selected weapon")
        elif name_norm == "rapid shot":
            if character.ability_scores.dex < 13:
                missing.append("Dex 13")
            if "point-blank shot" not in feat_names:
                missing.append("Point-Blank Shot")

        results.append(
            FeatPrereqResultV2(
                feat_name=feat.name,
                level_gained=feat.level_gained,
                valid=len(missing) == 0,
                missing=missing,
            )
        )

    return results


def _class_rule_or_default(class_name: str) -> ClassRule:
    return _CLASS_RULES.get(
        _norm(class_name),
        ClassRule(
            hit_die=6,
            bab_progression="half",
            fort_progression="poor",
            ref_progression="poor",
            will_progression="poor",
            class_skills=set(),
        ),
    )


def derive_stats(character: CharacterV2) -> DerivedStatsV2:
    scores = character.ability_scores
    mods = {
        "str": _mod(scores.str),
        "dex": _mod(scores.dex),
        "con": _mod(scores.con),
        "int": _mod(scores.int),
        "wis": _mod(scores.wis),
        "cha": _mod(scores.cha),
    }
    breakdown: list[BreakdownLineV2] = []

    total_level = 0
    bab = 0
    fort_base = 0
    ref_base = 0
    will_base = 0

    hp_total = 0
    first_character_level = True
    investigator_level = 0
    class_skills: set[str] = set()

    for cl in character.class_levels:
        rule = _class_rule_or_default(cl.class_name)
        total_level += cl.level
        bab_gain = _bab_for_level(rule.bab_progression, cl.level)
        fort_gain = _save_for_level(rule.fort_progression, cl.level)
        ref_gain = _save_for_level(rule.ref_progression, cl.level)
        will_gain = _save_for_level(rule.will_progression, cl.level)
        bab += bab_gain
        fort_base += fort_gain
        ref_base += ref_gain
        will_base += will_gain
        class_skills |= rule.class_skills
        if _norm(cl.class_name) == "investigator":
            investigator_level += cl.level

        if cl.level > 0:
            if first_character_level:
                hp_total += rule.hit_die + mods["con"]
                hp_total += max(0, cl.level - 1) * ((rule.hit_die // 2 + 1) + mods["con"])
                first_character_level = False
            else:
                hp_total += cl.level * ((rule.hit_die // 2 + 1) + mods["con"])

        breakdown.append(BreakdownLineV2(key="BAB", value=bab_gain, source=f"{cl.class_name} {cl.level} levels"))
        breakdown.append(
            BreakdownLineV2(key="Fort(base)", value=fort_gain, source=f"{cl.class_name} {cl.level} levels")
        )
        breakdown.append(BreakdownLineV2(key="Ref(base)", value=ref_gain, source=f"{cl.class_name} {cl.level} levels"))
        breakdown.append(BreakdownLineV2(key="Will(base)", value=will_gain, source=f"{cl.class_name} {cl.level} levels"))

    feat_prereq_results = evaluate_feat_prerequisites(character, total_bab=bab)
    valid_feats = {_norm(f.feat_name) for f in feat_prereq_results if f.valid}
    for result in feat_prereq_results:
        if not result.valid:
            breakdown.append(
                BreakdownLineV2(
                    key="FeatPrereq",
                    value=0,
                    source=f"{result.feat_name} blocked ({', '.join(result.missing)})",
                )
            )

    fort_misc = _trait_effect_total(character, "fort") + _trait_effect_total(character, "fortitude")
    ref_misc = _trait_effect_total(character, "ref") + _trait_effect_total(character, "reflex")
    will_misc = _trait_effect_total(character, "will")
    initiative_misc = _trait_effect_total(character, "initiative")
    ac_misc = _trait_effect_total(character, "ac")
    hp_misc = _trait_effect_total(character, "hp")
    cmb_misc = _trait_effect_total(character, "cmb")
    cmd_misc = _trait_effect_total(character, "cmd")

    condition_attack_penalty = 0
    condition_save_penalty = 0
    for condition in {_norm(c) for c in character.conditions}:
        if condition == "shaken":
            condition_attack_penalty -= 2
            condition_save_penalty -= 2
        if condition == "sickened":
            condition_attack_penalty -= 2
            condition_save_penalty -= 2

    fort = fort_base + mods["con"] + fort_misc + condition_save_penalty
    ref = ref_base + mods["dex"] + ref_misc + condition_save_penalty
    will = will_base + mods["wis"] + will_misc + condition_save_penalty
    hp_max = max(total_level, hp_total + hp_misc)

    armor_bonus = 0
    armor_max_dex: int | None = None
    for gear in character.equipment:
        if gear.kind != "armor":
            continue
        armor = _ARMOR_RULES.get(_norm(gear.name))
        if not armor:
            continue
        armor_bonus += armor.armor_bonus
        if armor.max_dex is not None:
            armor_max_dex = armor.max_dex if armor_max_dex is None else min(armor_max_dex, armor.max_dex)

    dex_to_ac = mods["dex"] if armor_max_dex is None else min(mods["dex"], armor_max_dex)
    ac_total = 10 + armor_bonus + dex_to_ac + ac_misc
    ac_touch = 10 + dex_to_ac + ac_misc
    ac_flat_footed = 10 + armor_bonus + ac_misc

    cmb = bab + mods["str"] + cmb_misc
    cmd = 10 + bab + mods["str"] + mods["dex"] + cmd_misc
    initiative = mods["dex"] + initiative_misc

    breakdown.append(BreakdownLineV2(key="Fort(total)", value=fort, source="base + CON + misc"))
    breakdown.append(BreakdownLineV2(key="Ref(total)", value=ref, source="base + DEX + misc"))
    breakdown.append(BreakdownLineV2(key="Will(total)", value=will, source="base + WIS + misc"))
    breakdown.append(BreakdownLineV2(key="HP(total)", value=hp_max, source="class hit dice + CON + misc"))
    breakdown.append(BreakdownLineV2(key="AC(total)", value=ac_total, source="10 + armor + DEX + misc"))
    breakdown.append(BreakdownLineV2(key="Initiative", value=initiative, source="DEX + misc"))

    skill_totals: dict[str, int] = {}
    for skill_name, ranks in character.skills.items():
        ability_key = None
        if skill_name.startswith("Knowledge"):
            ability_key = "int"
        else:
            ability_key = _SKILL_ABILITIES.get(skill_name)
        if ability_key is None:
            continue

        class_bonus = 3 if ranks > 0 and (skill_name in class_skills or skill_name.startswith("Knowledge")) else 0
        misc = _skill_effect_total(character, skill_name)
        total = int(ranks) + mods[ability_key] + class_bonus + misc
        skill_totals[skill_name] = total
        breakdown.append(BreakdownLineV2(key=f"Skill:{skill_name}", value=total, source="ranks + ability + class + misc"))

    spell_slots: dict[str, int] = {}
    if investigator_level > 0:
        spell_slots = _investigator_spell_slots(investigator_level, mods["int"])
        if spell_slots:
            breakdown.append(
                BreakdownLineV2(
                    key="SpellSlots",
                    value=sum(spell_slots.values()),
                    source=f"Investigator {investigator_level} + INT bonus slots",
                )
            )

    attack_lines: list[AttackLineV2] = []
    for gear in character.equipment:
        if gear.kind != "weapon":
            continue
        weapon = _WEAPON_RULES.get(_norm(gear.name))
        if not weapon:
            continue

        use_dex = weapon.weapon_type == "ranged"
        if not use_dex and weapon.finesse_eligible and "weapon finesse" in valid_feats:
            use_dex = True
        attack_ability_mod = mods["dex"] if use_dex else mods["str"]

        feat_attack_bonus = 1 if "weapon focus" in valid_feats else 0
        attack_bonus = bab + attack_ability_mod + feat_attack_bonus + condition_attack_penalty

        damage_bonus = mods["str"] if weapon.weapon_type == "melee" else 0
        if damage_bonus >= 0:
            damage = f"{weapon.damage_medium}+{damage_bonus}"
        else:
            damage = f"{weapon.damage_medium}{damage_bonus}"

        notes = f"{weapon.critical}"
        if use_dex and weapon.finesse_eligible:
            notes = f"{notes}; Weapon Finesse"
        attack_lines.append(
            AttackLineV2(
                name=gear.name,
                attack_bonus=attack_bonus,
                damage=damage,
                notes=notes,
            )
        )

    # Deterministic override layer for table/house rules.
    override_targets: dict[str, int | float] = {
        "bab": bab,
        "fort": fort,
        "ref": ref,
        "will": will,
        "hp_max": hp_max,
        "ac_total": ac_total,
        "ac_touch": ac_touch,
        "ac_flat_footed": ac_flat_footed,
        "cmb": cmb,
        "cmd": cmd,
        "initiative": initiative,
    }
    for raw_override in character.overrides:
        override = (
            raw_override
            if isinstance(raw_override, RuleOverrideV2)
            else RuleOverrideV2.model_validate(raw_override)
        )
        key = _norm(override.key)
        if key not in override_targets:
            continue
        if override.operation == "set":
            override_targets[key] = override.value
        else:
            override_targets[key] = override_targets[key] + override.value
        breakdown.append(
            BreakdownLineV2(
                key=f"Override:{override.key}",
                value=float(override.value),
                source=f"{override.operation} ({override.source})",
            )
        )

    bab = int(override_targets["bab"])
    fort = int(override_targets["fort"])
    ref = int(override_targets["ref"])
    will = int(override_targets["will"])
    hp_max = int(override_targets["hp_max"])
    ac_total = int(override_targets["ac_total"])
    ac_touch = int(override_targets["ac_touch"])
    ac_flat_footed = int(override_targets["ac_flat_footed"])
    cmb = int(override_targets["cmb"])
    cmd = int(override_targets["cmd"])
    initiative = int(override_targets["initiative"])

    return DerivedStatsV2(
        total_level=total_level,
        bab=bab,
        fort=fort,
        ref=ref,
        will=will,
        hp_max=hp_max,
        ac_total=ac_total,
        ac_touch=ac_touch,
        ac_flat_footed=ac_flat_footed,
        cmb=cmb,
        cmd=cmd,
        initiative=initiative,
        spell_slots=spell_slots,
        skill_totals=skill_totals,
        attack_lines=attack_lines,
        feat_prereq_results=feat_prereq_results,
        breakdown=breakdown,
    )
