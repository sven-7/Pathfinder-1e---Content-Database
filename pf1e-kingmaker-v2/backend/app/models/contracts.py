"""Versioned contracts for character and derived stats."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
    str: int = Field(ge=1)
    dex: int = Field(ge=1)
    con: int = Field(ge=1)
    int: int = Field(ge=1)
    wis: int = Field(ge=1)
    cha: int = Field(ge=1)


class CharacterV2(BaseModel):
    id: str | None = None
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


class BreakdownLineV2(BaseModel):
    key: str
    value: int | float
    source: str


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
    breakdown: list[BreakdownLineV2] = Field(default_factory=list)


class DeriveResponseV2(BaseModel):
    character: CharacterV2
    derived: DerivedStatsV2
