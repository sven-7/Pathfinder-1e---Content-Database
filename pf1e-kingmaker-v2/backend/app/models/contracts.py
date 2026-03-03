"""Versioned contracts for character and derived stats."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScoreValue = int


class ClassLevelV2(BaseModel):
    class_name: str
    level: int = Field(ge=1, le=20)
    archetype_name: str | None = None


class FeatSelectionV2(BaseModel):
    name: str
    level_gained: int = Field(ge=1, le=20)
    method: Literal["general", "bonus", "racial", "campaign", "dm_award"]


class TraitEffectV2(BaseModel):
    key: str
    delta: int | float
    bonus_type: str = "untyped"
    source: str


class TraitSelectionV2(BaseModel):
    name: str
    category: str
    effects: list[TraitEffectV2] = Field(default_factory=list)


class EquipmentSelectionV2(BaseModel):
    name: str
    kind: Literal["weapon", "armor", "shield", "gear"]
    quantity: int = Field(default=1, ge=1)


class AbilityScoresV2(BaseModel):
    str: ScoreValue = Field(ge=1)
    dex: ScoreValue = Field(ge=1)
    con: ScoreValue = Field(ge=1)
    int: ScoreValue = Field(ge=1)
    wis: ScoreValue = Field(ge=1)
    cha: ScoreValue = Field(ge=1)


class RuleOverrideV2(BaseModel):
    key: str
    operation: Literal["add", "set"] = "add"
    value: int | float = 0
    source: str


class CharacterV2(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Kairon",
                "race": "Tiefling",
                "alignment": "Lawful Neutral",
                "ability_scores": {"str": 12, "dex": 18, "con": 12, "int": 17, "wis": 18, "cha": 14},
                "class_levels": [{"class_name": "Investigator", "level": 9}],
                "feats": [
                    {"name": "Weapon Finesse", "level_gained": 1, "method": "general"},
                    {"name": "Weapon Focus", "level_gained": 3, "method": "general"},
                    {"name": "Rapid Shot", "level_gained": 5, "method": "general"},
                ],
                "traits": [
                    {
                        "name": "Reactionary",
                        "category": "Combat",
                        "effects": [{"key": "initiative", "delta": 2, "bonus_type": "trait", "source": "Reactionary"}],
                    }
                ],
                "skills": {"Perception": 9},
                "equipment": [
                    {"name": "Rapier", "kind": "weapon", "quantity": 1},
                    {"name": "Studded Leather", "kind": "armor", "quantity": 1},
                ],
                "conditions": [],
                "overrides": [],
            }
        }
    )

    id: str | None = None
    owner_id: str | None = None
    campaign_id: str | None = None
    name: str
    race: str
    alignment: str | None = None
    ability_scores: AbilityScoresV2
    class_levels: list[ClassLevelV2]
    feats: list[FeatSelectionV2] = Field(default_factory=list)
    traits: list[TraitSelectionV2] = Field(default_factory=list)
    skills: dict[str, int] = Field(default_factory=dict)
    equipment: list[EquipmentSelectionV2] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    overrides: list[RuleOverrideV2] = Field(default_factory=list)


class BreakdownLineV2(BaseModel):
    key: str
    value: int | float
    source: str


class AttackLineV2(BaseModel):
    name: str
    attack_bonus: int
    damage: str
    notes: str = ""


class FeatPrereqResultV2(BaseModel):
    feat_name: str
    level_gained: int
    valid: bool
    missing: list[str] = Field(default_factory=list)


class DerivedStatsV2(BaseModel):
    total_level: int
    bab: int
    fort: int
    ref: int
    will: int
    hp_max: int
    ac_total: int
    ac_touch: int
    ac_flat_footed: int
    cmb: int
    cmd: int
    initiative: int
    spell_slots: dict[str, int] = Field(default_factory=dict)
    skill_totals: dict[str, int] = Field(default_factory=dict)
    attack_lines: list[AttackLineV2] = Field(default_factory=list)
    feat_prereq_results: list[FeatPrereqResultV2] = Field(default_factory=list)
    breakdown: list[BreakdownLineV2] = Field(default_factory=list)


class CharacterValidationResponseV2(BaseModel):
    ok: bool
    name: str
    total_levels: int
    feat_prereq_results: list[FeatPrereqResultV2] = Field(default_factory=list)
    invalid_feats: list[FeatPrereqResultV2] = Field(default_factory=list)


class ContentFeatV2(BaseModel):
    id: int | None = None
    name: str
    feat_type: str | None = None
    prerequisites: str | None = None
    benefit: str | None = None
    source_book: str | None = None
    ui_enabled: int | None = None
    ui_tier: str | None = None
    policy_reason: str | None = None


class ContentRaceV2(BaseModel):
    id: int | None = None
    name: str
    race_type: str | None = None
    size: str | None = None
    base_speed: int | None = None
    source_book: str | None = None
    ui_enabled: int | None = None
    ui_tier: str | None = None
    policy_reason: str | None = None


class PolicySummaryV2(BaseModel):
    accepted_total: int = 0
    active_total: int = 0
    deferred_total: int = 0
    reason_counts: dict[str, int] = Field(default_factory=dict)
    tier_counts: dict[str, int] = Field(default_factory=dict)


class DeriveResponseV2(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "character": {
                    "name": "Kairon",
                    "race": "Tiefling",
                    "alignment": "Lawful Neutral",
                    "ability_scores": {"str": 12, "dex": 18, "con": 12, "int": 17, "wis": 18, "cha": 14},
                    "class_levels": [{"class_name": "Investigator", "level": 9}],
                    "feats": [
                        {"name": "Weapon Finesse", "level_gained": 1, "method": "general"},
                        {"name": "Weapon Focus", "level_gained": 3, "method": "general"},
                        {"name": "Rapid Shot", "level_gained": 5, "method": "general"},
                    ],
                    "traits": [
                        {
                            "name": "Reactionary",
                            "category": "Combat",
                            "effects": [
                                {"key": "initiative", "delta": 2, "bonus_type": "trait", "source": "Reactionary"}
                            ],
                        }
                    ],
                    "skills": {"Perception": 9},
                    "equipment": [
                        {"name": "Rapier", "kind": "weapon", "quantity": 1},
                        {"name": "Studded Leather", "kind": "armor", "quantity": 1},
                    ],
                    "conditions": [],
                    "overrides": [],
                },
                "derived": {
                    "total_level": 9,
                    "bab": 6,
                    "fort": 4,
                    "ref": 10,
                    "will": 10,
                    "hp_max": 57,
                    "ac_total": 17,
                    "ac_touch": 14,
                    "ac_flat_footed": 13,
                    "cmb": 7,
                    "cmd": 21,
                    "initiative": 6,
                    "spell_slots": {"1": 5, "2": 4, "3": 3},
                    "skill_totals": {"Perception": 16},
                    "attack_lines": [
                        {
                            "name": "Rapier",
                            "attack_bonus": 11,
                            "damage": "1d6+1",
                            "notes": "18-20/x2; Weapon Finesse",
                        }
                    ],
                    "feat_prereq_results": [
                        {"feat_name": "Weapon Finesse", "level_gained": 1, "valid": True, "missing": []},
                        {"feat_name": "Weapon Focus", "level_gained": 3, "valid": True, "missing": []},
                        {
                            "feat_name": "Rapid Shot",
                            "level_gained": 5,
                            "valid": False,
                            "missing": ["Point-Blank Shot"],
                        },
                    ],
                    "breakdown": [
                        {"key": "BAB", "value": 6, "source": "Investigator 9 levels"},
                        {"key": "AC(total)", "value": 17, "source": "10 + armor + DEX + misc"},
                    ],
                },
            }
        }
    )

    character: CharacterV2
    derived: DerivedStatsV2
