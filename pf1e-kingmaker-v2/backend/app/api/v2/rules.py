"""Rules derivation API V2 routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.contracts import (
    BreakdownLineV2,
    CharacterV2,
    DeriveResponseV2,
    DerivedStatsV2,
)

router = APIRouter(prefix="/rules", tags=["rules-v2"])


_BAB_STYLE = {
    "Fighter": "full",
    "Barbarian": "full",
    "Paladin": "full",
    "Ranger": "full",
    "Investigator": "three_quarter",
    "Rogue": "three_quarter",
    "Cleric": "three_quarter",
    "Druid": "three_quarter",
    "Bard": "three_quarter",
    "Wizard": "half",
    "Sorcerer": "half",
}

_SAVE_STYLES = {
    "Fighter": ("good", "poor", "poor"),
    "Investigator": ("poor", "good", "good"),
    "Wizard": ("poor", "poor", "good"),
    "Rogue": ("poor", "good", "poor"),
}


def _mod(score: int) -> int:
    return (score - 10) // 2


def _bab_for_level(style: str, level: int) -> int:
    if style == "full":
        return level
    if style == "three_quarter":
        return (level * 3) // 4
    return level // 2


def _save_for_level(style: str, level: int) -> int:
    if style == "good":
        return (level // 2) + 2
    return level // 3


@router.post("/derive", response_model=DeriveResponseV2)
def derive(character: CharacterV2) -> DeriveResponseV2:
    scores = character.ability_scores
    mods = {
        "str": _mod(scores.str),
        "dex": _mod(scores.dex),
        "con": _mod(scores.con),
        "int": _mod(scores.int),
        "wis": _mod(scores.wis),
        "cha": _mod(scores.cha),
    }

    bab = 0
    fort_base = 0
    ref_base = 0
    will_base = 0
    total_level = 0

    for cl in character.class_levels:
        total_level += cl.level
        bab_style = _BAB_STYLE.get(cl.class_name, "half")
        bab += _bab_for_level(bab_style, cl.level)

        save_styles = _SAVE_STYLES.get(cl.class_name, ("poor", "poor", "poor"))
        fort_base += _save_for_level(save_styles[0], cl.level)
        ref_base += _save_for_level(save_styles[1], cl.level)
        will_base += _save_for_level(save_styles[2], cl.level)

    fort = fort_base + mods["con"]
    ref = ref_base + mods["dex"]
    will = will_base + mods["wis"]

    # Baseline HP: max d8 at first level + average d8 for remaining levels.
    hp_max = 0
    remaining = total_level
    if remaining > 0:
        hp_max += 8 + mods["con"]
        remaining -= 1
    hp_max += remaining * (5 + mods["con"])

    ac_total = 10 + mods["dex"]
    ac_touch = 10 + mods["dex"]
    ac_flat = 10
    cmb = bab + mods["str"]
    cmd = 10 + bab + mods["str"] + mods["dex"]
    initiative = mods["dex"]

    breakdown = [
        BreakdownLineV2(key="BAB", value=bab, source="class progression"),
        BreakdownLineV2(key="Fort", value=fort, source="base + CON"),
        BreakdownLineV2(key="Ref", value=ref, source="base + DEX"),
        BreakdownLineV2(key="Will", value=will, source="base + WIS"),
        BreakdownLineV2(key="HP", value=hp_max, source="d8 baseline + CON"),
    ]

    return DeriveResponseV2(
        character=character,
        derived=DerivedStatsV2(
            total_level=total_level,
            bab=bab,
            fort=fort,
            ref=ref,
            will=will,
            hp_max=max(hp_max, total_level),
            ac_total=ac_total,
            ac_touch=ac_touch,
            ac_flat_footed=ac_flat,
            cmb=cmb,
            cmd=cmd,
            initiative=initiative,
            breakdown=breakdown,
        ),
    )
