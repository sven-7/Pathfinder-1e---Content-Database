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


def _trait_effect_lines(character: CharacterV2, keys: list[str]) -> list[tuple[str, int, str]]:
    targets = {_norm(k): k for k in keys}
    lines: list[tuple[str, int, str]] = []
    for trait in character.traits:
        for effect in trait.effects:
            effect_key = _norm(effect.key)
            if effect_key in targets:
                source_name = effect.source or trait.name
                lines.append((source_name, int(effect.delta), targets[effect_key]))
    lines.sort(key=lambda item: (_norm(item[0]), _norm(item[2]), item[1]))
    return lines


def _skill_effect_total(character: CharacterV2, skill_name: str) -> int:
    target = _norm(f"skill:{skill_name}")
    total = 0
    for trait in character.traits:
        for effect in trait.effects:
            if _norm(effect.key) == target:
                total += int(effect.delta)
    return total


def _skill_effect_lines(character: CharacterV2, skill_name: str) -> list[tuple[str, int]]:
    target = _norm(f"skill:{skill_name}")
    lines: list[tuple[str, int]] = []
    for trait in character.traits:
        for effect in trait.effects:
            if _norm(effect.key) == target:
                source_name = effect.source or trait.name
                lines.append((source_name, int(effect.delta)))
    lines.sort(key=lambda item: (_norm(item[0]), item[1]))
    return lines


def _add_breakdown_line(breakdown: list[BreakdownLineV2], key: str, value: int | float, source: str) -> None:
    breakdown.append(BreakdownLineV2(key=key, value=value, source=source))


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

    has_equipped_weapon = any(eq.kind == "weapon" for eq in character.equipment)
    results: list[FeatPrereqResultV2] = []
    granted_feats: set[str] = set()

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
            if character.ability_scores.dexterity < 13:
                missing.append("Dex 13")
            if "point-blank shot" not in granted_feats:
                missing.append("Point-Blank Shot")

        results.append(
            FeatPrereqResultV2(
                feat_name=feat.name,
                level_gained=feat.level_gained,
                valid=len(missing) == 0,
                missing=missing,
            )
        )
        if len(missing) == 0:
            granted_feats.add(name_norm)

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
        "str": _mod(scores.str_score),
        "dex": _mod(scores.dex),
        "con": _mod(scores.con),
        "int": _mod(scores.int_score),
        "wis": _mod(scores.wis),
        "cha": _mod(scores.cha),
    }
    breakdown: list[BreakdownLineV2] = []

    total_level = 0
    bab = 0
    fort_base = 0
    ref_base = 0
    will_base = 0

    hp_hit_die_total = 0
    hp_con_total = 0
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

        class_hit_die_hp = 0
        class_con_hp = cl.level * mods["con"]
        if cl.level > 0:
            if first_character_level:
                class_hit_die_hp += rule.hit_die
                class_hit_die_hp += max(0, cl.level - 1) * (rule.hit_die // 2 + 1)
                first_character_level = False
            else:
                class_hit_die_hp += cl.level * (rule.hit_die // 2 + 1)

        hp_hit_die_total += class_hit_die_hp
        hp_con_total += class_con_hp

        source_label = f"{cl.class_name} {cl.level} levels"
        _add_breakdown_line(breakdown, key=f"BAB:class:{cl.class_name}", value=bab_gain, source=source_label)
        _add_breakdown_line(breakdown, key=f"Fort:class:{cl.class_name}", value=fort_gain, source=source_label)
        _add_breakdown_line(breakdown, key=f"Ref:class:{cl.class_name}", value=ref_gain, source=source_label)
        _add_breakdown_line(breakdown, key=f"Will:class:{cl.class_name}", value=will_gain, source=source_label)
        _add_breakdown_line(
            breakdown,
            key=f"HP:hit_die:{cl.class_name}",
            value=class_hit_die_hp,
            source=f"{source_label} (max at character level 1, average thereafter)",
        )
        _add_breakdown_line(
            breakdown,
            key=f"HP:con:{cl.class_name}",
            value=class_con_hp,
            source=f"{source_label} (CON modifier per level)",
        )

    feat_prereq_results = evaluate_feat_prerequisites(character, total_bab=bab)
    valid_feats = {_norm(f.feat_name) for f in feat_prereq_results if f.valid}
    for result in feat_prereq_results:
        if not result.valid:
            _add_breakdown_line(
                breakdown,
                key=f"FeatPrereq:{result.feat_name}",
                value=0,
                source=f"blocked ({', '.join(result.missing)})",
            )

    fort_effect_lines = _trait_effect_lines(character, ["fort", "fortitude"])
    ref_effect_lines = _trait_effect_lines(character, ["ref", "reflex"])
    will_effect_lines = _trait_effect_lines(character, ["will"])
    initiative_effect_lines = _trait_effect_lines(character, ["initiative"])
    ac_effect_lines = _trait_effect_lines(character, ["ac"])
    hp_effect_lines = _trait_effect_lines(character, ["hp"])
    cmb_effect_lines = _trait_effect_lines(character, ["cmb"])
    cmd_effect_lines = _trait_effect_lines(character, ["cmd"])

    fort_misc = sum(line[1] for line in fort_effect_lines)
    ref_misc = sum(line[1] for line in ref_effect_lines)
    will_misc = sum(line[1] for line in will_effect_lines)
    initiative_misc = sum(line[1] for line in initiative_effect_lines)
    ac_misc = sum(line[1] for line in ac_effect_lines)
    hp_misc = sum(line[1] for line in hp_effect_lines)
    cmb_misc = sum(line[1] for line in cmb_effect_lines)
    cmd_misc = sum(line[1] for line in cmd_effect_lines)

    condition_attack_penalty = 0
    condition_save_penalty = 0
    condition_names = sorted({_norm(c) for c in character.conditions})
    for condition in condition_names:
        if condition == "shaken":
            condition_attack_penalty -= 2
            condition_save_penalty -= 2
        if condition == "sickened":
            condition_attack_penalty -= 2
            condition_save_penalty -= 2

    fort = fort_base + mods["con"] + fort_misc + condition_save_penalty
    ref = ref_base + mods["dex"] + ref_misc + condition_save_penalty
    will = will_base + mods["wis"] + will_misc + condition_save_penalty
    hp_pre_floor = hp_hit_die_total + hp_con_total + hp_misc
    hp_max = max(total_level, hp_pre_floor)

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

    _add_breakdown_line(breakdown, key="BAB:total", value=bab, source="class progression")

    _add_breakdown_line(breakdown, key="Fort:base", value=fort_base, source="class progression")
    _add_breakdown_line(breakdown, key="Fort:ability", value=mods["con"], source="CON modifier")
    for source_name, delta, source_key in fort_effect_lines:
        _add_breakdown_line(breakdown, key="Fort:misc", value=delta, source=f"{source_name} ({source_key})")
    _add_breakdown_line(breakdown, key="Fort:condition", value=condition_save_penalty, source="conditions")
    _add_breakdown_line(breakdown, key="Fort:total", value=fort, source="base + ability + misc + conditions")

    _add_breakdown_line(breakdown, key="Ref:base", value=ref_base, source="class progression")
    _add_breakdown_line(breakdown, key="Ref:ability", value=mods["dex"], source="DEX modifier")
    for source_name, delta, source_key in ref_effect_lines:
        _add_breakdown_line(breakdown, key="Ref:misc", value=delta, source=f"{source_name} ({source_key})")
    _add_breakdown_line(breakdown, key="Ref:condition", value=condition_save_penalty, source="conditions")
    _add_breakdown_line(breakdown, key="Ref:total", value=ref, source="base + ability + misc + conditions")

    _add_breakdown_line(breakdown, key="Will:base", value=will_base, source="class progression")
    _add_breakdown_line(breakdown, key="Will:ability", value=mods["wis"], source="WIS modifier")
    for source_name, delta, source_key in will_effect_lines:
        _add_breakdown_line(breakdown, key="Will:misc", value=delta, source=f"{source_name} ({source_key})")
    _add_breakdown_line(breakdown, key="Will:condition", value=condition_save_penalty, source="conditions")
    _add_breakdown_line(breakdown, key="Will:total", value=will, source="base + ability + misc + conditions")

    _add_breakdown_line(breakdown, key="HP:hit_die", value=hp_hit_die_total, source="class hit dice")
    _add_breakdown_line(breakdown, key="HP:con", value=hp_con_total, source="CON modifier per level")
    for source_name, delta, source_key in hp_effect_lines:
        _add_breakdown_line(breakdown, key="HP:misc", value=delta, source=f"{source_name} ({source_key})")
    if hp_max != hp_pre_floor:
        _add_breakdown_line(breakdown, key="HP:floor", value=total_level, source="minimum 1 HP per level")
    _add_breakdown_line(breakdown, key="HP:total", value=hp_max, source="hit die + CON + misc")

    _add_breakdown_line(breakdown, key="AC:base", value=10, source="core rule")
    _add_breakdown_line(breakdown, key="AC:armor", value=armor_bonus, source="equipped armor")
    _add_breakdown_line(breakdown, key="AC:dex", value=dex_to_ac, source="DEX modifier (capped by armor)")
    for source_name, delta, source_key in ac_effect_lines:
        _add_breakdown_line(breakdown, key="AC:misc", value=delta, source=f"{source_name} ({source_key})")
    _add_breakdown_line(breakdown, key="AC:total", value=ac_total, source="10 + armor + DEX + misc")
    # Keep the legacy key for contract/backward compatibility with existing consumers.
    _add_breakdown_line(breakdown, key="AC(total)", value=ac_total, source="10 + armor + DEX + misc")
    _add_breakdown_line(breakdown, key="AC:touch", value=ac_touch, source="10 + DEX + misc")
    _add_breakdown_line(breakdown, key="AC:flat_footed", value=ac_flat_footed, source="10 + armor + misc")

    _add_breakdown_line(breakdown, key="CMB:bab", value=bab, source="base attack bonus")
    _add_breakdown_line(breakdown, key="CMB:ability", value=mods["str"], source="STR modifier")
    for source_name, delta, source_key in cmb_effect_lines:
        _add_breakdown_line(breakdown, key="CMB:misc", value=delta, source=f"{source_name} ({source_key})")
    _add_breakdown_line(breakdown, key="CMB:total", value=cmb, source="BAB + STR + misc")

    _add_breakdown_line(breakdown, key="CMD:base", value=10, source="core rule")
    _add_breakdown_line(breakdown, key="CMD:bab", value=bab, source="base attack bonus")
    _add_breakdown_line(breakdown, key="CMD:str", value=mods["str"], source="STR modifier")
    _add_breakdown_line(breakdown, key="CMD:dex", value=mods["dex"], source="DEX modifier")
    for source_name, delta, source_key in cmd_effect_lines:
        _add_breakdown_line(breakdown, key="CMD:misc", value=delta, source=f"{source_name} ({source_key})")
    _add_breakdown_line(breakdown, key="CMD:total", value=cmd, source="10 + BAB + STR + DEX + misc")

    _add_breakdown_line(breakdown, key="Initiative:dex", value=mods["dex"], source="DEX modifier")
    for source_name, delta, source_key in initiative_effect_lines:
        _add_breakdown_line(breakdown, key="Initiative:misc", value=delta, source=f"{source_name} ({source_key})")
    _add_breakdown_line(breakdown, key="Initiative:total", value=initiative, source="DEX + misc")

    skill_totals: dict[str, int] = {}
    for skill_name in sorted(character.skills):
        ranks = character.skills[skill_name]
        ability_key = None
        if skill_name.startswith("Knowledge"):
            ability_key = "int"
        else:
            ability_key = _SKILL_ABILITIES.get(skill_name)
        if ability_key is None:
            continue

        class_bonus = 3 if ranks > 0 and (skill_name in class_skills or skill_name.startswith("Knowledge")) else 0
        skill_effect_lines = _skill_effect_lines(character, skill_name)
        misc = _skill_effect_total(character, skill_name)
        total = int(ranks) + mods[ability_key] + class_bonus + misc
        skill_totals[skill_name] = total

        _add_breakdown_line(breakdown, key=f"Skill:{skill_name}:ranks", value=int(ranks), source="allocated ranks")
        _add_breakdown_line(
            breakdown,
            key=f"Skill:{skill_name}:ability",
            value=mods[ability_key],
            source=f"{ability_key.upper()} modifier",
        )
        _add_breakdown_line(
            breakdown,
            key=f"Skill:{skill_name}:class",
            value=class_bonus,
            source="class skill bonus (+3 when trained)",
        )
        for source_name, delta in skill_effect_lines:
            _add_breakdown_line(
                breakdown,
                key=f"Skill:{skill_name}:misc",
                value=delta,
                source=source_name,
            )
        _add_breakdown_line(
            breakdown,
            key=f"Skill:{skill_name}:total",
            value=total,
            source="ranks + ability + class + misc",
        )

    spell_slots: dict[str, int] = {}
    if investigator_level > 0:
        spell_slots = _investigator_spell_slots(investigator_level, mods["int"])
        if spell_slots:
            _add_breakdown_line(
                breakdown,
                key="SpellSlots:total",
                value=sum(spell_slots.values()),
                source=f"Investigator {investigator_level} + INT bonus slots",
            )

    attack_lines: list[AttackLineV2] = []
    weapon_entries = [(index, gear) for index, gear in enumerate(character.equipment) if gear.kind == "weapon"]
    weapon_entries.sort(key=lambda item: (_norm(item[1].name), item[0]))
    for _, gear in weapon_entries:
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
        if bab >= 6:
            notes = f"{notes}; iterative +{attack_bonus}/+{attack_bonus - 5}"
        if use_dex and weapon.finesse_eligible:
            notes = f"{notes}; Weapon Finesse"

        _add_breakdown_line(breakdown, key=f"Attack:{gear.name}:bab", value=bab, source="base attack bonus")
        _add_breakdown_line(
            breakdown,
            key=f"Attack:{gear.name}:ability",
            value=attack_ability_mod,
            source="DEX modifier" if use_dex else "STR modifier",
        )
        _add_breakdown_line(
            breakdown,
            key=f"Attack:{gear.name}:feat",
            value=feat_attack_bonus,
            source="Weapon Focus",
        )
        _add_breakdown_line(
            breakdown,
            key=f"Attack:{gear.name}:condition",
            value=condition_attack_penalty,
            source="conditions",
        )
        _add_breakdown_line(
            breakdown,
            key=f"Attack:{gear.name}:total",
            value=attack_bonus,
            source="BAB + ability + feat + condition",
        )
        _add_breakdown_line(
            breakdown,
            key=f"Attack:{gear.name}:damage_bonus",
            value=damage_bonus,
            source="STR modifier (melee only)",
        )
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
        override = raw_override if isinstance(raw_override, RuleOverrideV2) else RuleOverrideV2.model_validate(raw_override)
        key = _norm(override.key)
        if key not in override_targets:
            continue
        if override.operation == "set":
            override_targets[key] = override.value
        else:
            override_targets[key] = override_targets[key] + override.value
        _add_breakdown_line(
            breakdown,
            key=f"Override:{override.key}",
            value=override.value,
            source=f"{override.operation} ({override.source})",
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

    _add_breakdown_line(breakdown, key="Result:bab", value=bab, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:fort", value=fort, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:ref", value=ref, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:will", value=will, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:hp_max", value=hp_max, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:ac_total", value=ac_total, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:ac_touch", value=ac_touch, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:ac_flat_footed", value=ac_flat_footed, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:cmb", value=cmb, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:cmd", value=cmd, source="after overrides")
    _add_breakdown_line(breakdown, key="Result:initiative", value=initiative, source="after overrides")

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
