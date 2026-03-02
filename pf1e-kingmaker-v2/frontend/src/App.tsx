import { useEffect, useMemo, useState } from "react";

type Health = {
  ok: boolean;
  env: string;
  version: string;
};

type FeatRow = {
  id: number | null;
  name: string;
  feat_type: string | null;
  prerequisites: string | null;
  benefit: string | null;
  source_book: string | null;
  ui_enabled?: number | boolean | null;
  ui_tier?: string | null;
  policy_reason?: string | null;
};

type RaceRow = {
  id: number | null;
  name: string;
  race_type: string | null;
  size: string | null;
  base_speed: number | null;
  source_book: string | null;
  ui_enabled?: number | boolean | null;
  ui_tier?: string | null;
  policy_reason?: string | null;
};

type PolicySummary = {
  accepted_total: number;
  active_total: number;
  deferred_total: number;
  reason_counts: Record<string, number>;
  tier_counts: Record<string, number>;
};

type AbilityScores = {
  str: number;
  dex: number;
  con: number;
  int: number;
  wis: number;
  cha: number;
};

type ClassLevelV2 = {
  class_name: string;
  level: number;
  archetype_name?: string | null;
};

type FeatSelectionV2 = {
  name: string;
  level_gained: number;
  method: "general" | "bonus" | "racial" | "campaign" | "dm_award";
};

type EquipmentSelectionV2 = {
  name: string;
  kind: "weapon" | "armor" | "shield" | "gear";
  quantity: number;
};

type TraitSelectionV2 = {
  name: string;
  category: string;
  effects: Array<{ key: string; delta: number; bonus_type: string; source: string }>;
};

type CharacterV2 = {
  id?: string | null;
  owner_id?: string | null;
  campaign_id?: string | null;
  name: string;
  race: string;
  alignment?: string | null;
  ability_scores: AbilityScores;
  class_levels: ClassLevelV2[];
  feats: FeatSelectionV2[];
  traits: TraitSelectionV2[];
  skills: Record<string, number>;
  equipment: EquipmentSelectionV2[];
  conditions: string[];
  overrides: Array<{ key: string; operation: "add" | "set"; value: number; source: string }>;
};

type CharacterSummaryV2 = {
  id: string;
  name: string;
  race?: string;
  class_str?: string;
  total_level?: number;
  modified_at?: string;
};

type FeatPrereqResultV2 = {
  feat_name: string;
  level_gained: number;
  valid: boolean;
  missing: string[];
};

type CharacterValidationResponseV2 = {
  ok: boolean;
  name: string;
  total_levels: number;
  feat_prereq_results: FeatPrereqResultV2[];
  invalid_feats: FeatPrereqResultV2[];
};

type AttackLineV2 = {
  name: string;
  attack_bonus: number;
  damage: string;
  notes: string;
};

type DerivedStatsV2 = {
  total_level: number;
  bab: number;
  fort: number;
  ref: number;
  will: number;
  hp_max: number;
  ac_total: number;
  ac_touch: number;
  ac_flat_footed: number;
  cmb: number;
  cmd: number;
  initiative: number;
  spell_slots: Record<string, number>;
  skill_totals: Record<string, number>;
  attack_lines: AttackLineV2[];
  feat_prereq_results: FeatPrereqResultV2[];
  breakdown: Array<{ key: string; value: number; source: string }>;
};

type DeriveResponseV2 = {
  character: CharacterV2;
  derived: DerivedStatsV2;
};

type CampaignRowV1 = {
  id: string;
  name: string;
  owner_id: string;
  description?: string | null;
  status: "draft" | "active" | "paused" | "archived";
  gm_id?: string | null;
  player_id?: string | null;
  created_at: string;
  updated_at: string;
};

type PartyMemberRowV1 = {
  id: string;
  party_id: string;
  display_name: string;
  role: "pc" | "npc" | "companion" | "guest";
  character_id?: string | null;
  owner_id?: string | null;
  gm_id?: string | null;
  player_id?: string | null;
  created_at: string;
};

type PartyRowV1 = {
  id: string;
  campaign_id: string;
  name: string;
  owner_id: string;
  notes?: string | null;
  gm_id?: string | null;
  player_id?: string | null;
  members: PartyMemberRowV1[];
  created_at: string;
  updated_at: string;
};

type ViewMode = "creator" | "library" | "sheet" | "dm";
type StorageMode = "unknown" | "server" | "local";
type CharacterSource = "server" | "local";
type FormErrors = Partial<Record<"name" | "race" | "class_name" | "class_level" | "abilities", string>>;

type CharacterRecord = {
  id: string;
  name: string;
  race: string;
  class_summary: string;
  total_level: number;
  modified_at: string;
  source: CharacterSource;
  payload: CharacterV2 | null;
};

type LocalCharacterEntry = {
  id: string;
  modified_at: string;
  payload: CharacterV2;
};

type EditorDraft = {
  id: string | null;
  name: string;
  alignment: string;
  race: string;
  class_name: string;
  class_level: number;
  ability_scores: AbilityScores;
  feat_text: string;
  skills_text: string;
  equipment_text: string;
  conditions_text: string;
};

type ConditionDelta = {
  ac_total?: number;
  ac_touch?: number;
  ac_flat_footed?: number;
  fort?: number;
  ref?: number;
  will?: number;
  initiative?: number;
  cmb?: number;
  cmd?: number;
  attack?: number;
  skill_all?: number;
  skill_specific?: Record<string, number>;
};

type ConditionRule = {
  key: string;
  label: string;
  detail: string;
  extract_linked?: boolean;
  requires_derive?: boolean;
  delta: ConditionDelta;
};

type SpellTracker = {
  known: number;
  prepared: number;
  used: number;
};

type CharacterSheetResources = {
  hp_max: number;
  hp_current: number;
  hp_temp: number;
  hp_nonlethal: number;
  inspiration_max: number;
  inspiration_current: number;
  consumables: Record<string, number>;
};

type QuickCombatState = {
  initiative_roll: string;
  selected_attack_index: number;
  damage_notes: string;
};

type CharacterSheetState = {
  version: number;
  conditions: Record<string, boolean>;
  resources: CharacterSheetResources;
  spells: Record<string, SpellTracker>;
  quick_combat: QuickCombatState;
};

type AggregateConditionDelta = {
  ac_total: number;
  ac_touch: number;
  ac_flat_footed: number;
  fort: number;
  ref: number;
  will: number;
  initiative: number;
  cmb: number;
  cmd: number;
  attack: number;
  skill_all: number;
  skill_specific: Record<string, number>;
  requires_derive: boolean;
  active_labels: string[];
};

const LOCAL_STORAGE_KEY = "pf1e.v2.frontend.characters";
const SHEET_STATE_STORAGE_KEY = "pf1e.v2.frontend.sheet-state";
const ABILITY_KEYS = ["str", "dex", "con", "int", "wis", "cha"] as const;
const KEY_SKILL_SHORTCUTS = ["Perception", "Stealth", "Disable Device", "Knowledge (arcana)"] as const;

const CONSUMABLE_DEFINITIONS = [
  { key: "healing_potion", label: "Healing Potions", default_count: 3 },
  { key: "alchemist_fire", label: "Alchemist's Fire", default_count: 2 },
  { key: "antitoxin", label: "Antitoxin", default_count: 1 },
] as const;

const SHEET_CONDITIONS: ConditionRule[] = [
  {
    key: "studied-combat",
    label: "Studied Combat",
    detail: "Situational attack profile managed by derive rules.",
    requires_derive: true,
    delta: {},
  },
  {
    key: "shield",
    label: "Shield",
    detail: "+4 shield AC.",
    extract_linked: true,
    delta: { ac_total: 4, ac_flat_footed: 4 },
  },
  {
    key: "cats-grace",
    label: "Cat's Grace",
    detail: "+2 AC/Ref/Init/ATK (enhancement).",
    extract_linked: true,
    delta: { ac_total: 2, ac_touch: 2, ref: 2, initiative: 2, attack: 2 },
  },
  {
    key: "heroism",
    label: "Heroism",
    detail: "+2 attack, saves, and skills.",
    extract_linked: true,
    delta: { fort: 2, ref: 2, will: 2, attack: 2, skill_all: 2 },
  },
  {
    key: "haste",
    label: "Haste",
    detail: "+1 attack, AC, Ref, CMB, CMD.",
    extract_linked: true,
    delta: { ac_total: 1, ac_touch: 1, ref: 1, cmb: 1, cmd: 1, attack: 1 },
  },
  {
    key: "displacement",
    label: "Displacement",
    detail: "Miss chance reminder.",
    extract_linked: true,
    requires_derive: true,
    delta: {},
  },
  {
    key: "invisible",
    label: "Invisible",
    detail: "+2 attack, +20 Stealth.",
    extract_linked: true,
    delta: { attack: 2, skill_specific: { Stealth: 20 } },
  },
  {
    key: "channel-vigor",
    label: "Channel Vigor",
    detail: "Mode-specific benefits managed by derive rules.",
    extract_linked: true,
    requires_derive: true,
    delta: {},
  },
  {
    key: "enlarged",
    label: "Enlarged",
    detail: "-2 AC/ATK, +2 CMB, -1 CMD.",
    extract_linked: true,
    delta: { ac_total: -2, ac_touch: -2, ac_flat_footed: -1, ref: -1, initiative: -1, cmb: 2, cmd: -1, attack: -2 },
  },
  {
    key: "fly",
    label: "Fly",
    detail: "Movement condition, +4 Fly.",
    extract_linked: true,
    delta: { skill_specific: { Fly: 4 } },
  },
  {
    key: "exp-retreat",
    label: "Expeditious Retreat",
    detail: "Movement condition.",
    extract_linked: true,
    requires_derive: true,
    delta: {},
  },
  {
    key: "thorn-body",
    label: "Thorn Body",
    detail: "Reactive damage condition.",
    extract_linked: true,
    requires_derive: true,
    delta: {},
  },
  {
    key: "fire-breath",
    label: "Fire Breath",
    detail: "Track cone uses in resources.",
    extract_linked: true,
    requires_derive: true,
    delta: {},
  },
  {
    key: "darkness",
    label: "Darkness",
    detail: "Visibility condition.",
    requires_derive: true,
    delta: {},
  },
];

const CONDITION_RULE_BY_KEY = SHEET_CONDITIONS.reduce<Record<string, ConditionRule>>((acc, rule) => {
  acc[rule.key] = rule;
  return acc;
}, {});

const DEFAULT_DRAFT: EditorDraft = {
  id: null,
  name: "Kairon",
  alignment: "Lawful Neutral",
  race: "Tiefling",
  class_name: "Investigator",
  class_level: 9,
  ability_scores: {
    str: 12,
    dex: 18,
    con: 12,
    int: 17,
    wis: 18,
    cha: 14,
  },
  feat_text: "Weapon Finesse, Weapon Focus, Rapid Shot",
  skills_text: "Perception:9, Stealth:8",
  equipment_text: "Rapier:weapon:1, Studded Leather:armor:1",
  conditions_text: "",
};

function isDeferredRow(row: { ui_enabled?: number | boolean | null; ui_tier?: string | null }): boolean {
  return row.ui_tier === "deferred" || row.ui_enabled === 0 || row.ui_enabled === false;
}

function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

function parseCsv(text: string): string[] {
  return text
    .split(",")
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
}

function parseFeatSelections(text: string, classLevel: number): FeatSelectionV2[] {
  const names = parseCsv(text);
  return names.map((name, index) => ({
    name,
    level_gained: Math.max(1, Math.min(classLevel, 1 + index * 2)),
    method: "general",
  }));
}

function serializeFeatSelections(feats: FeatSelectionV2[]): string {
  return feats.map((feat) => feat.name).join(", ");
}

function parseSkills(text: string): Record<string, number> {
  const pairs = parseCsv(text);
  const skills: Record<string, number> = {};

  for (const pair of pairs) {
    const [rawName, rawValue] = pair.split(":");
    const name = (rawName ?? "").trim();
    if (!name) {
      continue;
    }
    const parsed = Number.parseInt((rawValue ?? "0").trim(), 10);
    skills[name] = Number.isFinite(parsed) ? parsed : 0;
  }

  return skills;
}

function serializeSkills(skills: Record<string, number>): string {
  return Object.entries(skills)
    .map(([name, value]) => `${name}:${value}`)
    .join(", ");
}

function parseEquipment(text: string): EquipmentSelectionV2[] {
  const entries = parseCsv(text);

  return entries
    .map((entry) => {
      const parts = entry.split(":").map((part) => part.trim());
      if (parts.length === 0 || !parts[0]) {
        return null;
      }

      const rawKind = (parts[1] ?? "gear").toLowerCase();
      const kind: EquipmentSelectionV2["kind"] =
        rawKind === "weapon" || rawKind === "armor" || rawKind === "shield" ? rawKind : "gear";
      const qtyParsed = Number.parseInt(parts[2] ?? "1", 10);
      const quantity = Number.isFinite(qtyParsed) && qtyParsed > 0 ? qtyParsed : 1;

      return {
        name: parts[0],
        kind,
        quantity,
      };
    })
    .filter((entry): entry is EquipmentSelectionV2 => Boolean(entry));
}

function serializeEquipment(equipment: EquipmentSelectionV2[]): string {
  return equipment.map((item) => `${item.name}:${item.kind}:${item.quantity}`).join(", ");
}

function parseConditions(text: string): string[] {
  return parseCsv(text);
}

function serializeConditions(conditions: string[]): string {
  return conditions.join(", ");
}

function classSummary(classLevels: ClassLevelV2[]): string {
  return classLevels.map((entry) => `${entry.class_name} ${entry.level}`).join(", ");
}

function totalLevel(classLevels: ClassLevelV2[]): number {
  return classLevels.reduce((sum, entry) => sum + Math.max(0, entry.level), 0);
}

function createCharacterPayload(draft: EditorDraft): CharacterV2 {
  const classLevel = Math.max(1, Math.min(20, draft.class_level));

  return {
    id: draft.id,
    name: draft.name.trim() || "Unnamed",
    race: draft.race.trim(),
    alignment: draft.alignment.trim() || null,
    ability_scores: {
      str: Math.max(1, draft.ability_scores.str),
      dex: Math.max(1, draft.ability_scores.dex),
      con: Math.max(1, draft.ability_scores.con),
      int: Math.max(1, draft.ability_scores.int),
      wis: Math.max(1, draft.ability_scores.wis),
      cha: Math.max(1, draft.ability_scores.cha),
    },
    class_levels: [
      {
        class_name: draft.class_name.trim() || "Adventurer",
        level: classLevel,
      },
    ],
    feats: parseFeatSelections(draft.feat_text, classLevel),
    traits: [],
    skills: parseSkills(draft.skills_text),
    equipment: parseEquipment(draft.equipment_text),
    conditions: parseConditions(draft.conditions_text),
    overrides: [],
  };
}

function draftFromCharacter(character: CharacterV2): EditorDraft {
  const mainClass = character.class_levels[0] ?? { class_name: "Adventurer", level: 1 };

  return {
    id: character.id ?? null,
    name: character.name,
    alignment: character.alignment ?? "",
    race: character.race,
    class_name: mainClass.class_name,
    class_level: mainClass.level,
    ability_scores: {
      str: character.ability_scores.str,
      dex: character.ability_scores.dex,
      con: character.ability_scores.con,
      int: character.ability_scores.int,
      wis: character.ability_scores.wis,
      cha: character.ability_scores.cha,
    },
    feat_text: serializeFeatSelections(character.feats),
    skills_text: serializeSkills(character.skills),
    equipment_text: serializeEquipment(character.equipment),
    conditions_text: serializeConditions(character.conditions),
  };
}

function buildRecord(payload: CharacterV2, source: CharacterSource, modifiedAt: string): CharacterRecord {
  const id = payload.id ?? generateId();
  const fixedPayload = { ...payload, id };

  return {
    id,
    name: fixedPayload.name,
    race: fixedPayload.race,
    class_summary: classSummary(fixedPayload.class_levels),
    total_level: totalLevel(fixedPayload.class_levels),
    modified_at: modifiedAt,
    source,
    payload: fixedPayload,
  };
}

function parseLocalStorageCharacters(raw: string | null): CharacterRecord[] {
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    const mapped = parsed
      .map((entry) => {
        if (typeof entry !== "object" || entry === null) {
          return null;
        }

        const value = entry as Partial<LocalCharacterEntry>;
        if (!value.payload || typeof value.payload !== "object") {
          return null;
        }

        const payload = value.payload as CharacterV2;
        const id = typeof value.id === "string" ? value.id : payload.id ?? generateId();
        const modifiedAt = typeof value.modified_at === "string" ? value.modified_at : nowIso();

        return buildRecord({ ...payload, id }, "local", modifiedAt);
      })
      .filter((entry): entry is CharacterRecord => Boolean(entry));

    return mapped.sort((a, b) => b.modified_at.localeCompare(a.modified_at));
  } catch {
    return [];
  }
}

function loadLocalStorageCharacters(): CharacterRecord[] {
  if (typeof window === "undefined") {
    return [];
  }
  return parseLocalStorageCharacters(window.localStorage.getItem(LOCAL_STORAGE_KEY));
}

function persistLocalStorageCharacters(records: CharacterRecord[]): void {
  if (typeof window === "undefined") {
    return;
  }

  const entries: LocalCharacterEntry[] = records
    .filter((record) => record.source === "local" && record.payload !== null)
    .map((record) => ({
      id: record.id,
      modified_at: record.modified_at,
      payload: record.payload as CharacterV2,
    }));

  window.localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(entries));
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "unknown";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function abilityModifierValue(score: number): number {
  return Math.floor((score - 10) / 2);
}

function abilityMod(score: number): string {
  const mod = abilityModifierValue(score);
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

function formatSigned(value: number): string {
  return value >= 0 ? `+${value}` : `${value}`;
}

function clampInteger(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.max(min, Math.min(max, Math.trunc(value)));
}

function calculateInspirationMax(payload: CharacterV2): number {
  return Math.max(0, Math.floor(totalLevel(payload.class_levels) / 2) + abilityModifierValue(payload.ability_scores.int));
}

function createDefaultConditionState(payload: CharacterV2): Record<string, boolean> {
  const conditions: Record<string, boolean> = {};
  for (const rule of SHEET_CONDITIONS) {
    conditions[rule.key] = false;
  }
  for (const condition of payload.conditions) {
    conditions[condition] = true;
  }
  return conditions;
}

function createDefaultSpellTrackers(derived: DerivedStatsV2 | null): Record<string, SpellTracker> {
  const trackers: Record<string, SpellTracker> = {};
  if (!derived) {
    return trackers;
  }

  for (const [level, slots] of Object.entries(derived.spell_slots)) {
    const known = Math.max(0, Math.trunc(slots));
    trackers[level] = {
      known,
      prepared: known,
      used: 0,
    };
  }

  return trackers;
}

function createDefaultCharacterSheetState(payload: CharacterV2, derived: DerivedStatsV2 | null): CharacterSheetState {
  const hpMax = Math.max(1, derived?.hp_max ?? totalLevel(payload.class_levels) * 8);
  const inspirationMax = calculateInspirationMax(payload);
  const consumables: Record<string, number> = {};
  for (const definition of CONSUMABLE_DEFINITIONS) {
    consumables[definition.key] = definition.default_count;
  }

  return {
    version: 1,
    conditions: createDefaultConditionState(payload),
    resources: {
      hp_max: hpMax,
      hp_current: hpMax,
      hp_temp: 0,
      hp_nonlethal: 0,
      inspiration_max: inspirationMax,
      inspiration_current: inspirationMax,
      consumables,
    },
    spells: createDefaultSpellTrackers(derived),
    quick_combat: {
      initiative_roll: "",
      selected_attack_index: 0,
      damage_notes: "",
    },
  };
}

function normalizeCharacterSheetState(
  state: CharacterSheetState | undefined,
  payload: CharacterV2,
  derived: DerivedStatsV2 | null
): CharacterSheetState {
  const defaults = createDefaultCharacterSheetState(payload, derived);
  const hpMax = defaults.resources.hp_max;
  const inspirationMax = defaults.resources.inspiration_max;

  const conditions: Record<string, boolean> = {
    ...defaults.conditions,
  };
  if (state?.conditions) {
    for (const [key, value] of Object.entries(state.conditions)) {
      conditions[key] = Boolean(value);
    }
  }

  const consumables: Record<string, number> = {};
  for (const definition of CONSUMABLE_DEFINITIONS) {
    const raw = state?.resources?.consumables?.[definition.key];
    consumables[definition.key] =
      typeof raw === "number" && Number.isFinite(raw) ? Math.max(0, Math.trunc(raw)) : definition.default_count;
  }

  const resources: CharacterSheetResources = {
    hp_max: hpMax,
    hp_current:
      typeof state?.resources?.hp_current === "number" ? clampInteger(state.resources.hp_current, 0, hpMax) : defaults.resources.hp_current,
    hp_temp: typeof state?.resources?.hp_temp === "number" ? Math.max(0, Math.trunc(state.resources.hp_temp)) : 0,
    hp_nonlethal:
      typeof state?.resources?.hp_nonlethal === "number" ? Math.max(0, Math.trunc(state.resources.hp_nonlethal)) : 0,
    inspiration_max: inspirationMax,
    inspiration_current:
      typeof state?.resources?.inspiration_current === "number"
        ? clampInteger(state.resources.inspiration_current, 0, inspirationMax)
        : inspirationMax,
    consumables,
  };

  const defaultSpells = defaults.spells;
  const spellLevels = new Set<string>([...Object.keys(defaultSpells), ...Object.keys(state?.spells ?? {})]);
  const spells: Record<string, SpellTracker> = {};

  for (const level of spellLevels) {
    const fallback = defaultSpells[level] ?? { known: 0, prepared: 0, used: 0 };
    const source = state?.spells?.[level];
    const knownFromState = typeof source?.known === "number" ? Math.max(0, Math.trunc(source.known)) : fallback.known;
    const known = Math.max(fallback.known, knownFromState);
    const preparedFromState = typeof source?.prepared === "number" ? Math.max(0, Math.trunc(source.prepared)) : fallback.prepared;
    const prepared = Math.min(known, preparedFromState);
    const usedFromState = typeof source?.used === "number" ? Math.max(0, Math.trunc(source.used)) : fallback.used;
    const used = Math.min(prepared, usedFromState);

    spells[level] = {
      known,
      prepared,
      used,
    };
  }

  const quick_combat: QuickCombatState = {
    initiative_roll: typeof state?.quick_combat?.initiative_roll === "string" ? state.quick_combat.initiative_roll : "",
    selected_attack_index:
      typeof state?.quick_combat?.selected_attack_index === "number"
        ? Math.max(0, Math.trunc(state.quick_combat.selected_attack_index))
        : 0,
    damage_notes: typeof state?.quick_combat?.damage_notes === "string" ? state.quick_combat.damage_notes : "",
  };

  return {
    version: 1,
    conditions,
    resources,
    spells,
    quick_combat,
  };
}

function aggregateConditionDelta(conditions: Record<string, boolean>): AggregateConditionDelta {
  const aggregate: AggregateConditionDelta = {
    ac_total: 0,
    ac_touch: 0,
    ac_flat_footed: 0,
    fort: 0,
    ref: 0,
    will: 0,
    initiative: 0,
    cmb: 0,
    cmd: 0,
    attack: 0,
    skill_all: 0,
    skill_specific: {},
    requires_derive: false,
    active_labels: [],
  };

  for (const rule of SHEET_CONDITIONS) {
    if (!conditions[rule.key]) {
      continue;
    }

    aggregate.ac_total += rule.delta.ac_total ?? 0;
    aggregate.ac_touch += rule.delta.ac_touch ?? 0;
    aggregate.ac_flat_footed += rule.delta.ac_flat_footed ?? 0;
    aggregate.fort += rule.delta.fort ?? 0;
    aggregate.ref += rule.delta.ref ?? 0;
    aggregate.will += rule.delta.will ?? 0;
    aggregate.initiative += rule.delta.initiative ?? 0;
    aggregate.cmb += rule.delta.cmb ?? 0;
    aggregate.cmd += rule.delta.cmd ?? 0;
    aggregate.attack += rule.delta.attack ?? 0;
    aggregate.skill_all += rule.delta.skill_all ?? 0;
    aggregate.requires_derive = aggregate.requires_derive || Boolean(rule.requires_derive);
    aggregate.active_labels.push(rule.label);

    if (rule.delta.skill_specific) {
      for (const [skillName, bonus] of Object.entries(rule.delta.skill_specific)) {
        aggregate.skill_specific[skillName] = (aggregate.skill_specific[skillName] ?? 0) + bonus;
      }
    }
  }

  return aggregate;
}

function applySkillAdjustments(baseSkills: Record<string, number>, delta: AggregateConditionDelta): Record<string, number> {
  const adjusted: Record<string, number> = {};
  for (const [skillName, value] of Object.entries(baseSkills)) {
    adjusted[skillName] = value + delta.skill_all + (delta.skill_specific[skillName] ?? 0);
  }
  for (const [skillName, bonus] of Object.entries(delta.skill_specific)) {
    if (!(skillName in adjusted)) {
      adjusted[skillName] = delta.skill_all + bonus;
    }
  }
  return adjusted;
}

function buildDerivePayloadWithSheetConditions(payload: CharacterV2, sheetState: CharacterSheetState | null): CharacterV2 {
  if (!sheetState) {
    return payload;
  }

  const deriveConditionKeys = Object.entries(sheetState.conditions)
    .filter(([key, enabled]) => enabled && Boolean(CONDITION_RULE_BY_KEY[key]?.requires_derive))
    .map(([key]) => key);
  const payloadConditions = payload.conditions.filter((condition) => {
    const rule = CONDITION_RULE_BY_KEY[condition];
    return !rule || Boolean(rule.requires_derive);
  });

  return {
    ...payload,
    conditions: Array.from(new Set([...payloadConditions, ...deriveConditionKeys])),
  };
}

function parseSheetStateStorage(raw: string | null): Record<string, CharacterSheetState> {
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return {};
    }

    const out: Record<string, CharacterSheetState> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof key !== "string" || key.length === 0 || typeof value !== "object" || value === null) {
        continue;
      }
      out[key] = value as CharacterSheetState;
    }
    return out;
  } catch {
    return {};
  }
}

function loadSheetStateStorage(): Record<string, CharacterSheetState> {
  if (typeof window === "undefined") {
    return {};
  }
  return parseSheetStateStorage(window.localStorage.getItem(SHEET_STATE_STORAGE_KEY));
}

function persistSheetStateStorage(entries: Record<string, CharacterSheetState>): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(SHEET_STATE_STORAGE_KEY, JSON.stringify(entries));
}

function fetchLabel(status: StorageMode): string {
  if (status === "server") {
    return "Server";
  }
  if (status === "local") {
    return "Local";
  }
  return "Detecting";
}

function validateDraft(draft: EditorDraft): FormErrors {
  const errors: FormErrors = {};

  if (draft.name.trim().length === 0) {
    errors.name = "Name is required.";
  }
  if (draft.race.trim().length === 0) {
    errors.race = "Race is required.";
  }
  if (draft.class_name.trim().length === 0) {
    errors.class_name = "Class is required.";
  }
  if (!Number.isFinite(draft.class_level) || draft.class_level < 1 || draft.class_level > 20) {
    errors.class_level = "Level must be between 1 and 20.";
  }

  const invalidAbility = ABILITY_KEYS.some((key) => !Number.isFinite(draft.ability_scores[key]) || draft.ability_scores[key] < 1);
  if (invalidAbility) {
    errors.abilities = "All ability scores must be 1 or higher.";
  }

  return errors;
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const data = (await response.json()) as T;
  return data;
}

export function App() {
  const base = import.meta.env.VITE_API_BASE ?? "http://localhost:8100";

  const [view, setView] = useState<ViewMode>("creator");
  const [health, setHealth] = useState<Health | null>(null);
  const [includeDeferred, setIncludeDeferred] = useState<boolean>(false);

  const [contentLoading, setContentLoading] = useState<boolean>(true);
  const [contentError, setContentError] = useState<string>("");
  const [feats, setFeats] = useState<FeatRow[]>([]);
  const [races, setRaces] = useState<RaceRow[]>([]);
  const [policy, setPolicy] = useState<PolicySummary | null>(null);

  const [storageMode, setStorageMode] = useState<StorageMode>("unknown");
  const [libraryLoading, setLibraryLoading] = useState<boolean>(true);
  const [libraryError, setLibraryError] = useState<string>("");
  const [characters, setCharacters] = useState<CharacterRecord[]>([]);
  const [activeCharacterId, setActiveCharacterId] = useState<string | null>(null);

  const [draft, setDraft] = useState<EditorDraft>(DEFAULT_DRAFT);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [notice, setNotice] = useState<string>("");
  const [saveLoading, setSaveLoading] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string>("");

  const [deriveLoading, setDeriveLoading] = useState<boolean>(false);
  const [deriveError, setDeriveError] = useState<string>("");
  const [deriveResult, setDeriveResult] = useState<DeriveResponseV2 | null>(null);
  const [validationResult, setValidationResult] = useState<CharacterValidationResponseV2 | null>(null);
  const [derivedByCharacterId, setDerivedByCharacterId] = useState<Record<string, DerivedStatsV2>>({});
  const [sheetStateByCharacterId, setSheetStateByCharacterId] = useState<Record<string, CharacterSheetState>>(() =>
    loadSheetStateStorage()
  );

  const [searchText, setSearchText] = useState<string>("");
  const [raceFilter, setRaceFilter] = useState<string>("all");
  const [classFilter, setClassFilter] = useState<string>("all");
  const [dmCampaigns, setDmCampaigns] = useState<CampaignRowV1[]>([]);
  const [dmCampaignName, setDmCampaignName] = useState<string>("Stolen Lands");
  const [dmCampaignOwnerId, setDmCampaignOwnerId] = useState<string>("owner-stephen");
  const [dmLoading, setDmLoading] = useState<boolean>(true);
  const [dmError, setDmError] = useState<string>("");
  const [dmNotice, setDmNotice] = useState<string>("");
  const [dmSelectedCampaignId, setDmSelectedCampaignId] = useState<string | null>(null);
  const [dmParties, setDmParties] = useState<PartyRowV1[]>([]);
  const [dmPartiesLoading, setDmPartiesLoading] = useState<boolean>(false);

  useEffect(() => {
    fetch(`${base}/health`)
      .then((response) => parseJsonResponse<Health>(response))
      .then((json) => setHealth(json))
      .catch(() => setHealth(null));
  }, [base]);

  useEffect(() => {
    let active = true;
    const query = includeDeferred ? "?include_deferred=true" : "";

    async function loadContent(): Promise<void> {
      setContentLoading(true);
      setContentError("");

      try {
        const [featRows, raceRows, policySummary] = await Promise.all([
          fetch(`${base}/api/v2/content/feats${query}`).then((response) => {
            if (!response.ok) {
              throw new Error(`feats_${response.status}`);
            }
            return parseJsonResponse<FeatRow[]>(response);
          }),
          fetch(`${base}/api/v2/content/races${query}`).then((response) => {
            if (!response.ok) {
              throw new Error(`races_${response.status}`);
            }
            return parseJsonResponse<RaceRow[]>(response);
          }),
          fetch(`${base}/api/v2/content/policy-summary`).then((response) => {
            if (!response.ok) {
              throw new Error(`policy_${response.status}`);
            }
            return parseJsonResponse<PolicySummary>(response);
          }),
        ]);

        if (!active) {
          return;
        }

        setFeats(Array.isArray(featRows) ? featRows : []);
        setRaces(Array.isArray(raceRows) ? raceRows : []);
        setPolicy(policySummary);
      } catch {
        if (!active) {
          return;
        }
        setContentError("Unable to load API V2 content endpoints.");
        setFeats([]);
        setRaces([]);
        setPolicy(null);
      } finally {
        if (active) {
          setContentLoading(false);
        }
      }
    }

    void loadContent();

    return () => {
      active = false;
    };
  }, [base, includeDeferred]);

  useEffect(() => {
    let active = true;

    async function loadLibrary(): Promise<void> {
      setLibraryLoading(true);
      setLibraryError("");

      try {
        const response = await fetch(`${base}/api/v2/characters`);
        if (!response.ok) {
          throw new Error(`list_${response.status}`);
        }

        const summaries = await parseJsonResponse<CharacterSummaryV2[]>(response);
        if (!active) {
          return;
        }

        const mapped: CharacterRecord[] = (Array.isArray(summaries) ? summaries : [])
          .filter((row) => typeof row.id === "string" && row.id.length > 0)
          .map((row) => ({
            id: row.id,
            name: row.name || "Unnamed",
            race: row.race || "Unknown",
            class_summary: row.class_str || "Unknown Class",
            total_level: typeof row.total_level === "number" ? row.total_level : 0,
            modified_at: row.modified_at || nowIso(),
            source: "server",
            payload: null,
          }))
          .sort((a, b) => b.modified_at.localeCompare(a.modified_at));

        setStorageMode("server");
        setCharacters(mapped);

        if (mapped.length > 0) {
          setActiveCharacterId(mapped[0].id);
        }
      } catch {
        if (!active) {
          return;
        }
        setStorageMode("local");
        const local = loadLocalStorageCharacters();
        setCharacters(local);
        if (local.length > 0) {
          setActiveCharacterId(local[0].id);
          if (local[0].payload) {
            setDraft(draftFromCharacter(local[0].payload));
          }
        }
      } finally {
        if (active) {
          setLibraryLoading(false);
        }
      }
    }

    void loadLibrary();

    return () => {
      active = false;
    };
  }, [base]);

  useEffect(() => {
    if (storageMode === "local") {
      persistLocalStorageCharacters(characters);
    }
  }, [characters, storageMode]);

  useEffect(() => {
    persistSheetStateStorage(sheetStateByCharacterId);
  }, [sheetStateByCharacterId]);

  useEffect(() => {
    if (races.length === 0) {
      return;
    }

    if (draft.race.trim().length === 0) {
      setDraft((prev) => ({ ...prev, race: races[0].name }));
    }
  }, [draft.race, races]);

  const topDeferredReason = policy
    ? Object.entries(policy.reason_counts)
        .filter(([reason]) => reason !== "allowlisted")
        .sort((a, b) => b[1] - a[1])[0]?.[0] || "none"
    : "none";

  const visibleFeats = useMemo(() => {
    return includeDeferred ? feats : feats.filter((feat) => !isDeferredRow(feat));
  }, [feats, includeDeferred]);

  const visibleRaces = useMemo(() => {
    return includeDeferred ? races : races.filter((race) => !isDeferredRow(race));
  }, [includeDeferred, races]);

  const activeRecord = useMemo(() => {
    if (!activeCharacterId) {
      return null;
    }
    return characters.find((record) => record.id === activeCharacterId) ?? null;
  }, [activeCharacterId, characters]);

  const activeDerived = useMemo(() => {
    if (activeCharacterId && derivedByCharacterId[activeCharacterId]) {
      return derivedByCharacterId[activeCharacterId];
    }
    return deriveResult?.derived ?? null;
  }, [activeCharacterId, deriveResult, derivedByCharacterId]);

  const libraryRaces = useMemo(() => {
    const options = Array.from(new Set(characters.map((character) => character.race))).sort();
    return options;
  }, [characters]);

  const libraryClasses = useMemo(() => {
    const options = Array.from(new Set(characters.map((character) => character.class_summary))).sort();
    return options;
  }, [characters]);

  const filteredCharacters = useMemo(() => {
    const query = searchText.trim().toLowerCase();

    return characters.filter((character) => {
      const matchesText =
        query.length === 0 ||
        character.name.toLowerCase().includes(query) ||
        character.race.toLowerCase().includes(query) ||
        character.class_summary.toLowerCase().includes(query);
      const matchesRace = raceFilter === "all" || character.race === raceFilter;
      const matchesClass = classFilter === "all" || character.class_summary === classFilter;
      return matchesText && matchesRace && matchesClass;
    });
  }, [characters, classFilter, raceFilter, searchText]);

  const selectedDmCampaign = useMemo(() => {
    if (!dmSelectedCampaignId) {
      return null;
    }
    return dmCampaigns.find((campaign) => campaign.id === dmSelectedCampaignId) ?? null;
  }, [dmCampaigns, dmSelectedCampaignId]);

  useEffect(() => {
    let active = true;

    async function loadDmCampaigns(): Promise<void> {
      setDmLoading(true);
      setDmError("");

      try {
        const response = await fetch(`${base}/api/v2/campaigns`);
        if (!response.ok) {
          throw new Error(`campaigns_${response.status}`);
        }

        const rows = await parseJsonResponse<CampaignRowV1[]>(response);
        if (!active) {
          return;
        }

        const campaigns = Array.isArray(rows) ? rows : [];
        setDmCampaigns(campaigns);

        if (campaigns.length > 0) {
          setDmSelectedCampaignId((prev) => prev ?? campaigns[0].id);
        } else {
          setDmSelectedCampaignId(null);
          setDmParties([]);
        }
      } catch {
        if (!active) {
          return;
        }
        setDmCampaigns([]);
        setDmParties([]);
        setDmSelectedCampaignId(null);
        setDmError("Unable to load campaign endpoints.");
      } finally {
        if (active) {
          setDmLoading(false);
        }
      }
    }

    void loadDmCampaigns();

    return () => {
      active = false;
    };
  }, [base]);

  useEffect(() => {
    if (!dmSelectedCampaignId) {
      return;
    }
    void loadDmParties(dmSelectedCampaignId);
  }, [dmSelectedCampaignId]);

  async function loadDmParties(campaignId: string): Promise<void> {
    setDmPartiesLoading(true);
    setDmError("");

    try {
      const response = await fetch(`${base}/api/v2/parties?campaign_id=${encodeURIComponent(campaignId)}`);
      if (!response.ok) {
        throw new Error(`parties_${response.status}`);
      }
      const rows = await parseJsonResponse<PartyRowV1[]>(response);
      setDmParties(Array.isArray(rows) ? rows : []);
    } catch {
      setDmParties([]);
      setDmError("Unable to load party roster for selected campaign.");
    } finally {
      setDmPartiesLoading(false);
    }
  }

  async function openDmCampaign(campaignId: string): Promise<void> {
    setDmSelectedCampaignId(campaignId);
    await loadDmParties(campaignId);
  }

  async function createDmCampaign(): Promise<void> {
    setDmError("");
    setDmNotice("");

    const name = dmCampaignName.trim();
    const ownerId = dmCampaignOwnerId.trim();
    if (name.length === 0 || ownerId.length === 0) {
      setDmError("Campaign name and owner id are required.");
      return;
    }

    try {
      const response = await fetch(`${base}/api/v2/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          owner_id: ownerId,
          status: "active",
        }),
      });

      if (!response.ok) {
        throw new Error(`campaign_create_${response.status}`);
      }

      const created = await parseJsonResponse<CampaignRowV1>(response);
      setDmCampaigns((prev) =>
        [...prev, created].sort((a, b) => a.created_at.localeCompare(b.created_at))
      );
      setDmNotice(`Campaign "${created.name}" created.`);
      await openDmCampaign(created.id);
    } catch {
      setDmError("Unable to create campaign.");
    }
  }

  function upsertCharacterSheetState(characterId: string, payload: CharacterV2, derived: DerivedStatsV2 | null): void {
    setSheetStateByCharacterId((prev) => ({
      ...prev,
      [characterId]: normalizeCharacterSheetState(prev[characterId], payload, derived),
    }));
  }

  function setDraftField<K extends keyof EditorDraft>(key: K, value: EditorDraft[K]): void {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setNotice("");
    setSaveError("");
  }

  function setAbility(key: keyof AbilityScores, raw: string): void {
    const parsed = Number.parseInt(raw, 10);
    const nextValue = Number.isFinite(parsed) ? parsed : draft.ability_scores[key];
    setDraft((prev) => ({
      ...prev,
      ability_scores: {
        ...prev.ability_scores,
        [key]: Math.max(1, nextValue),
      },
    }));
    setNotice("");
    setSaveError("");
  }

  function resetForNewCharacter(): void {
    const fallbackRace = visibleRaces[0]?.name ?? races[0]?.name ?? DEFAULT_DRAFT.race;
    setDraft({ ...DEFAULT_DRAFT, id: null, race: fallbackRace });
    setFormErrors({});
    setActiveCharacterId(null);
    setDeriveResult(null);
    setValidationResult(null);
    setDeriveError("");
    setSaveError("");
    setNotice("Started a new character draft.");
    setView("creator");
  }

  async function ensurePayload(record: CharacterRecord): Promise<CharacterV2 | null> {
    if (record.payload) {
      return record.payload;
    }

    if (record.source !== "server") {
      return null;
    }

    try {
      const response = await fetch(`${base}/api/v2/characters/${record.id}`);
      if (!response.ok) {
        throw new Error(`get_${response.status}`);
      }
      const payload = await parseJsonResponse<CharacterV2>(response);
      const withId = { ...payload, id: payload.id ?? record.id };

      setCharacters((prev) =>
        prev.map((entry) =>
          entry.id === record.id
            ? {
                ...entry,
                payload: withId,
                race: withId.race,
                class_summary: classSummary(withId.class_levels),
                total_level: totalLevel(withId.class_levels),
              }
            : entry
        )
      );

      return withId;
    } catch {
      setLibraryError(`Unable to load full payload for ${record.name}.`);
      return null;
    }
  }

  async function editCharacter(record: CharacterRecord): Promise<void> {
    const payload = await ensurePayload(record);
    if (!payload) {
      return;
    }

    setActiveCharacterId(record.id);
    setDraft(draftFromCharacter(payload));
    setFormErrors({});
    setDeriveResult(null);
    setValidationResult(null);
    setDeriveError("");
    setSaveError("");
    setNotice(`Editing ${record.name}.`);
    setView("creator");
  }

  async function openSheet(record: CharacterRecord): Promise<void> {
    const payload = await ensurePayload(record);
    if (!payload) {
      return;
    }

    upsertCharacterSheetState(record.id, payload, derivedByCharacterId[record.id] ?? null);
    setActiveCharacterId(record.id);
    setDraft(draftFromCharacter(payload));
    setView("sheet");

    if (!derivedByCharacterId[record.id]) {
      await deriveCharacter(payload, record.id, false);
    }
  }

  async function saveCharacter(): Promise<void> {
    const errors = validateDraft(draft);
    setFormErrors(errors);
    setSaveError("");

    if (Object.keys(errors).length > 0) {
      setSaveError("Fix validation errors before saving.");
      return;
    }

    const payload = createCharacterPayload(draft);
    setSaveLoading(true);

    try {
      if (storageMode === "server") {
        const targetId = draft.id ?? activeCharacterId;
        const endpoint = targetId ? `${base}/api/v2/characters/${targetId}` : `${base}/api/v2/characters`;
        const method = targetId ? "PUT" : "POST";

        const response = await fetch(endpoint, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          if (response.status === 404 || response.status === 405) {
            setStorageMode("local");
            const localId = targetId ?? payload.id ?? generateId();
            const localPayload = { ...payload, id: localId };
            const localRecord = buildRecord(localPayload, "local", nowIso());

            setCharacters((prev) =>
              [localRecord, ...prev.filter((entry) => entry.id !== localRecord.id)].sort((a, b) =>
                b.modified_at.localeCompare(a.modified_at)
              )
            );
            setDraft(draftFromCharacter(localPayload));
            setActiveCharacterId(localId);
            upsertCharacterSheetState(localId, localPayload, derivedByCharacterId[localId] ?? null);
            setNotice("Server character CRUD unavailable in this backend state. Saved locally.");
            return;
          }

          throw new Error(`save_${response.status}`);
        }

        const body = (await parseJsonResponse<{ id?: string; name?: string }>(response)) || {};
        const savedId = body.id ?? targetId ?? payload.id ?? generateId();
        const mergedPayload = { ...payload, id: savedId };
        const record = buildRecord(mergedPayload, "server", nowIso());

        setCharacters((prev) =>
          [record, ...prev.filter((entry) => entry.id !== savedId)].sort((a, b) => b.modified_at.localeCompare(a.modified_at))
        );
        setDraft(draftFromCharacter(mergedPayload));
        setActiveCharacterId(savedId);
        upsertCharacterSheetState(savedId, mergedPayload, derivedByCharacterId[savedId] ?? deriveResult?.derived ?? null);
        setNotice("Character saved to API V2.");
        return;
      }

      const localId = draft.id ?? activeCharacterId ?? generateId();
      const localPayload = { ...payload, id: localId };
      const localRecord = buildRecord(localPayload, "local", nowIso());

      setCharacters((prev) =>
        [localRecord, ...prev.filter((entry) => entry.id !== localRecord.id)].sort((a, b) => b.modified_at.localeCompare(a.modified_at))
      );
      setDraft(draftFromCharacter(localPayload));
      setActiveCharacterId(localId);
      upsertCharacterSheetState(localId, localPayload, derivedByCharacterId[localId] ?? deriveResult?.derived ?? null);
      setNotice("Character saved locally.");
    } catch {
      setSaveError("Could not save character.");
    } finally {
      setSaveLoading(false);
    }
  }

  async function deriveCharacter(payloadOverride?: CharacterV2, characterIdForCache?: string, showNotice = true): Promise<void> {
    const payload = payloadOverride ?? createCharacterPayload(draft);

    if (!payloadOverride) {
      const errors = validateDraft(draft);
      setFormErrors(errors);
      if (Object.keys(errors).length > 0) {
        setDeriveError("Fix validation errors before deriving stats.");
        return;
      }
    }

    setDeriveLoading(true);
    setDeriveError("");

    try {
      const [validationResponse, deriveResponse] = await Promise.all([
        fetch(`${base}/api/v2/characters/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }),
        fetch(`${base}/api/v2/rules/derive`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }),
      ]);

      if (!validationResponse.ok || !deriveResponse.ok) {
        throw new Error(`derive_or_validate_${validationResponse.status}_${deriveResponse.status}`);
      }

      const validationBody = await parseJsonResponse<CharacterValidationResponseV2>(validationResponse);
      const deriveBody = await parseJsonResponse<DeriveResponseV2>(deriveResponse);

      setValidationResult(validationBody);
      setDeriveResult(deriveBody);

      const cacheId = characterIdForCache ?? payload.id ?? activeCharacterId;
      if (cacheId) {
        setDerivedByCharacterId((prev) => ({
          ...prev,
          [cacheId]: deriveBody.derived,
        }));
        upsertCharacterSheetState(cacheId, deriveBody.character, deriveBody.derived);
      }

      if (showNotice) {
        setNotice("Derived preview refreshed from API V2.");
      }
    } catch {
      setDeriveError("Could not derive and validate character via API V2.");
    } finally {
      setDeriveLoading(false);
    }
  }

  const selectedRaceRow = races.find((race) => race.name === draft.race) ?? null;
  const raceIsHiddenDeferred = Boolean(selectedRaceRow && isDeferredRow(selectedRaceRow) && !includeDeferred);
  const raceOptions = selectedRaceRow && !visibleRaces.some((row) => row.name === selectedRaceRow.name)
    ? [selectedRaceRow, ...visibleRaces]
    : visibleRaces;

  const activePayloadForSheet = activeRecord?.payload ?? deriveResult?.character ?? null;
  const activeSheetCharacterId = activeRecord?.id ?? activePayloadForSheet?.id ?? null;
  const activeSheetStorageId = activeSheetCharacterId ?? "__draft__";

  const activeSheetState = useMemo(() => {
    if (!activePayloadForSheet) {
      return null;
    }
    const stored = sheetStateByCharacterId[activeSheetStorageId];
    return normalizeCharacterSheetState(stored, activePayloadForSheet, activeDerived);
  }, [activeDerived, activePayloadForSheet, activeSheetStorageId, sheetStateByCharacterId]);

  const conditionDelta = useMemo(() => {
    return aggregateConditionDelta(activeSheetState?.conditions ?? {});
  }, [activeSheetState]);

  const adjustedDerived = useMemo(() => {
    if (!activeDerived) {
      return null;
    }

    return {
      ...activeDerived,
      ac_total: activeDerived.ac_total + conditionDelta.ac_total,
      ac_touch: activeDerived.ac_touch + conditionDelta.ac_touch,
      ac_flat_footed: activeDerived.ac_flat_footed + conditionDelta.ac_flat_footed,
      fort: activeDerived.fort + conditionDelta.fort,
      ref: activeDerived.ref + conditionDelta.ref,
      will: activeDerived.will + conditionDelta.will,
      initiative: activeDerived.initiative + conditionDelta.initiative,
      cmb: activeDerived.cmb + conditionDelta.cmb,
      cmd: activeDerived.cmd + conditionDelta.cmd,
      attack_lines: activeDerived.attack_lines.map((line) => ({
        ...line,
        attack_bonus: line.attack_bonus + conditionDelta.attack,
      })),
      skill_totals: applySkillAdjustments(activeDerived.skill_totals, conditionDelta),
    };
  }, [activeDerived, conditionDelta]);

  const displaySkillTotals = useMemo(() => {
    if (!activePayloadForSheet) {
      return {};
    }
    const baseSkills =
      activeDerived?.skill_totals && Object.keys(activeDerived.skill_totals).length > 0
        ? activeDerived.skill_totals
        : activePayloadForSheet.skills;
    return applySkillAdjustments(baseSkills, conditionDelta);
  }, [activeDerived, activePayloadForSheet, conditionDelta]);

  const keySkillShortcuts = useMemo(() => {
    const shortcuts: Array<{ name: string; value: number | null }> = [];
    for (const skillName of KEY_SKILL_SHORTCUTS) {
      if (typeof displaySkillTotals[skillName] === "number") {
        shortcuts.push({ name: skillName, value: displaySkillTotals[skillName] });
      } else {
        shortcuts.push({ name: skillName, value: null });
      }
    }
    return shortcuts;
  }, [displaySkillTotals]);

  const spellLevels = useMemo(() => {
    if (!activeSheetState) {
      return [] as Array<[string, SpellTracker]>;
    }
    return Object.entries(activeSheetState.spells).sort(
      ([a], [b]) => Number.parseInt(a, 10) - Number.parseInt(b, 10)
    );
  }, [activeSheetState]);

  const combatAttackLines = adjustedDerived?.attack_lines ?? [];
  const selectedAttackLine =
    activeSheetState && combatAttackLines.length > 0
      ? combatAttackLines[Math.min(activeSheetState.quick_combat.selected_attack_index, combatAttackLines.length - 1)]
      : null;
  const quickInitiativeTotal = useMemo(() => {
    if (!activeSheetState || typeof adjustedDerived?.initiative !== "number") {
      return null;
    }
    const parsed = Number.parseInt(activeSheetState.quick_combat.initiative_roll, 10);
    if (!Number.isFinite(parsed)) {
      return null;
    }
    return parsed + adjustedDerived.initiative;
  }, [activeSheetState, adjustedDerived]);

  function updateActiveSheetState(mutator: (state: CharacterSheetState) => CharacterSheetState): CharacterSheetState | null {
    if (!activePayloadForSheet) {
      return null;
    }

    let nextSnapshot: CharacterSheetState | null = null;
    setSheetStateByCharacterId((prev) => {
      const current = normalizeCharacterSheetState(prev[activeSheetStorageId], activePayloadForSheet, activeDerived);
      const next = mutator(current);
      nextSnapshot = next;
      return {
        ...prev,
        [activeSheetStorageId]: next,
      };
    });
    return nextSnapshot;
  }

  function toggleSheetCondition(conditionKey: string, enabled: boolean): void {
    const nextState = updateActiveSheetState((current) => ({
      ...current,
      conditions: {
        ...current.conditions,
        [conditionKey]: enabled,
      },
    }));
    const rule = CONDITION_RULE_BY_KEY[conditionKey];
    if (!nextState || !activePayloadForSheet || !rule?.requires_derive) {
      return;
    }

    void deriveCharacter(
      buildDerivePayloadWithSheetConditions(activePayloadForSheet, nextState),
      activeSheetCharacterId ?? undefined,
      false
    );
  }

  function setSheetResourceValue(
    key: "hp_current" | "hp_temp" | "hp_nonlethal" | "inspiration_current",
    rawValue: string
  ): void {
    const parsed = Number.parseInt(rawValue, 10);
    const nextRaw = Number.isFinite(parsed) ? parsed : 0;

    updateActiveSheetState((current) => {
      if (key === "hp_current") {
        return {
          ...current,
          resources: {
            ...current.resources,
            hp_current: clampInteger(nextRaw, 0, current.resources.hp_max),
          },
        };
      }

      if (key === "inspiration_current") {
        return {
          ...current,
          resources: {
            ...current.resources,
            inspiration_current: clampInteger(nextRaw, 0, current.resources.inspiration_max),
          },
        };
      }

      return {
        ...current,
        resources: {
          ...current.resources,
          [key]: Math.max(0, Math.trunc(nextRaw)),
        },
      };
    });
  }

  function adjustResource(
    key: "hp_current" | "inspiration_current",
    delta: number
  ): void {
    updateActiveSheetState((current) => {
      if (key === "hp_current") {
        return {
          ...current,
          resources: {
            ...current.resources,
            hp_current: clampInteger(current.resources.hp_current + delta, 0, current.resources.hp_max),
          },
        };
      }
      return {
        ...current,
        resources: {
          ...current.resources,
          inspiration_current: clampInteger(
            current.resources.inspiration_current + delta,
            0,
            current.resources.inspiration_max
          ),
        },
      };
    });
  }

  function adjustConsumable(consumableKey: string, delta: number): void {
    updateActiveSheetState((current) => ({
      ...current,
      resources: {
        ...current.resources,
        consumables: {
          ...current.resources.consumables,
          [consumableKey]: Math.max(0, (current.resources.consumables[consumableKey] ?? 0) + delta),
        },
      },
    }));
  }

  function adjustSpellTracker(level: string, field: "known" | "prepared" | "used", delta: number): void {
    updateActiveSheetState((current) => {
      const existing = current.spells[level] ?? { known: 0, prepared: 0, used: 0 };
      let known = existing.known;
      let prepared = existing.prepared;
      let used = existing.used;

      if (field === "known") {
        known = Math.max(0, known + delta);
      }
      if (field === "prepared") {
        prepared = Math.max(0, prepared + delta);
      }
      if (field === "used") {
        used = Math.max(0, used + delta);
      }

      prepared = Math.min(prepared, known);
      used = Math.min(used, prepared);

      return {
        ...current,
        spells: {
          ...current.spells,
          [level]: {
            known,
            prepared,
            used,
          },
        },
      };
    });
  }

  function applyRest(restType: "short" | "full"): void {
    updateActiveSheetState((current) => {
      const spells: Record<string, SpellTracker> = {};
      for (const [level, tracker] of Object.entries(current.spells)) {
        if (restType === "short") {
          const used = Math.max(0, tracker.used - 1);
          spells[level] = {
            known: tracker.known,
            prepared: tracker.prepared,
            used,
          };
        } else {
          spells[level] = {
            known: tracker.known,
            prepared: tracker.known,
            used: 0,
          };
        }
      }

      return {
        ...current,
        resources: {
          ...current.resources,
          hp_current: restType === "full" ? current.resources.hp_max : current.resources.hp_current,
          hp_temp: 0,
          hp_nonlethal: restType === "full" ? 0 : current.resources.hp_nonlethal,
          inspiration_current:
            restType === "full" ? current.resources.inspiration_max : current.resources.inspiration_current,
        },
        spells,
        quick_combat: {
          ...current.quick_combat,
          initiative_roll: "",
        },
      };
    });
    setNotice(restType === "full" ? "Full rest reset applied." : "Short rest reset applied.");
  }

  function setQuickCombatField<K extends keyof QuickCombatState>(key: K, value: QuickCombatState[K]): void {
    updateActiveSheetState((current) => ({
      ...current,
      quick_combat: {
        ...current.quick_combat,
        [key]: value,
      },
    }));
  }

  return (
    <main className="app-shell">
      <header className="hero card">
        <div>
          <h1>Phase 6 Kairon UI Parity</h1>
          <p>
            Create, validate, derive, save, load, and run tablet-ready in-sheet tracking against API V2 contracts.
          </p>
        </div>
        <div className="hero-meta">
          <span className={`pill ${storageMode === "server" ? "active" : "deferred"}`}>
            Store: {fetchLabel(storageMode)}
          </span>
          <span className={`pill ${includeDeferred ? "deferred" : "active"}`}>
            Mode: {includeDeferred ? "DM/Dev" : "Player"}
          </span>
        </div>
      </header>

      <section className="tabs card" aria-label="Primary views">
        <button
          type="button"
          data-testid="tab-creator"
          className={view === "creator" ? "tab active" : "tab"}
          onClick={() => setView("creator")}
        >
          Creator
        </button>
        <button
          type="button"
          data-testid="tab-library"
          className={view === "library" ? "tab active" : "tab"}
          onClick={() => setView("library")}
        >
          Library
        </button>
        <button
          type="button"
          data-testid="tab-sheet"
          className={view === "sheet" ? "tab active" : "tab"}
          onClick={() => setView("sheet")}
        >
          Sheet
        </button>
        <button
          type="button"
          data-testid="tab-dm"
          className={view === "dm" ? "tab active" : "tab"}
          onClick={() => setView("dm")}
        >
          DM
        </button>
      </section>

      <div className="workspace">
        <aside className="sidebar">
          <section className="card">
            <h2>Content Visibility</h2>
            <label className="toggle">
              <input
                type="checkbox"
                checked={includeDeferred}
                onChange={(event) => setIncludeDeferred(event.target.checked)}
              />
              <span>Include deferred rows</span>
            </label>
            <p className="muted">Player mode hides deferred rows from race/feat pickers.</p>
          </section>

          <section className="card">
            <h2>API Health</h2>
            {health ? (
              <p>
                Connected: env={health.env}, version={health.version}
              </p>
            ) : (
              <p>Not connected yet.</p>
            )}
            {contentError ? <p className="error">{contentError}</p> : null}
            {!contentError && policy ? (
              <div className="stack">
                <p>Accepted: {policy.accepted_total}</p>
                <p>Active: {policy.active_total}</p>
                <p>Deferred: {policy.deferred_total}</p>
                <p className="muted">Top deferred reason: {topDeferredReason}</p>
              </div>
            ) : null}
          </section>

          <section className="card">
            <h2>Quick Library</h2>
            <p className="muted">{characters.length} saved character(s)</p>
            <ul className="compact-list">
              {characters.slice(0, 6).map((record) => (
                <li key={record.id}>
                  <span className="row-title">{record.name}</span>
                  <span className="row-meta">{record.race} • {record.class_summary}</span>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        <section className="main-view">
          {view === "creator" ? (
            <section className="card" data-testid="creator-view">
              <div className="section-head">
                <h2>Character Creator</h2>
                <div className="actions">
                  <button type="button" className="ghost-btn" onClick={resetForNewCharacter}>
                    New
                  </button>
                  <button type="button" data-testid="save-button" className="primary-btn" onClick={() => void saveCharacter()} disabled={saveLoading}>
                    {saveLoading ? "Saving..." : "Save"}
                  </button>
                </div>
              </div>

              {notice ? <p className="notice">{notice}</p> : null}
              {saveError ? <p className="error">{saveError}</p> : null}

              <div className="form-grid">
                <label>
                  Name
                  <input
                    data-testid="input-name"
                    value={draft.name}
                    onChange={(event) => setDraftField("name", event.target.value)}
                  />
                  {formErrors.name ? <span className="field-error">{formErrors.name}</span> : null}
                </label>

                <label>
                  Alignment
                  <input
                    value={draft.alignment}
                    onChange={(event) => setDraftField("alignment", event.target.value)}
                    placeholder="Lawful Neutral"
                  />
                </label>

                <label>
                  Race
                  <select
                    data-testid="input-race"
                    value={draft.race}
                    onChange={(event) => setDraftField("race", event.target.value)}
                  >
                    {raceOptions.map((race) => (
                      <option key={race.name} value={race.name}>
                        {race.name}
                        {isDeferredRow(race) ? " (deferred)" : ""}
                      </option>
                    ))}
                  </select>
                  {formErrors.race ? <span className="field-error">{formErrors.race}</span> : null}
                </label>

                <label>
                  Class
                  <input
                    data-testid="input-class"
                    value={draft.class_name}
                    onChange={(event) => setDraftField("class_name", event.target.value)}
                  />
                  {formErrors.class_name ? <span className="field-error">{formErrors.class_name}</span> : null}
                </label>

                <label>
                  Level
                  <input
                    data-testid="input-level"
                    type="number"
                    min={1}
                    max={20}
                    value={draft.class_level}
                    onChange={(event) => {
                      const parsed = Number.parseInt(event.target.value || "1", 10);
                      const bounded = Number.isFinite(parsed) ? Math.max(1, Math.min(20, parsed)) : draft.class_level;
                      setDraftField("class_level", bounded);
                    }}
                  />
                  {formErrors.class_level ? <span className="field-error">{formErrors.class_level}</span> : null}
                </label>
              </div>

              {raceIsHiddenDeferred ? (
                <p className="warning">Current race is deferred; enable DM/Dev mode to view all deferred race options.</p>
              ) : null}

              <div className="abilities-grid">
                {ABILITY_KEYS.map((key) => (
                  <label key={key}>
                    {key.toUpperCase()} <span className="muted">({abilityMod(draft.ability_scores[key])})</span>
                    <input
                      type="number"
                      min={1}
                      value={draft.ability_scores[key]}
                      onChange={(event) => setAbility(key, event.target.value)}
                    />
                  </label>
                ))}
              </div>
              {formErrors.abilities ? <p className="field-error ability-error">{formErrors.abilities}</p> : null}

              <div className="text-grid">
                <label>
                  Feats (comma-separated)
                  <textarea
                    data-testid="input-feats"
                    value={draft.feat_text}
                    onChange={(event) => setDraftField("feat_text", event.target.value)}
                  />
                  <span className="muted">{visibleFeats.length} feat options loaded from `/api/v2/content/feats`.</span>
                </label>

                <label>
                  Skills (`Name:value`)
                  <textarea
                    value={draft.skills_text}
                    onChange={(event) => setDraftField("skills_text", event.target.value)}
                    placeholder="Perception:9, Stealth:8"
                  />
                </label>

                <label>
                  Equipment (`Name:kind:qty`)
                  <textarea
                    value={draft.equipment_text}
                    onChange={(event) => setDraftField("equipment_text", event.target.value)}
                    placeholder="Rapier:weapon:1, Studded Leather:armor:1"
                  />
                </label>

                <label>
                  Conditions (comma-separated)
                  <textarea
                    value={draft.conditions_text}
                    onChange={(event) => setDraftField("conditions_text", event.target.value)}
                    placeholder="fatigued, shaken"
                  />
                </label>
              </div>

              <div className="actions derive-row">
                <button
                  type="button"
                  data-testid="derive-button"
                  className="primary-btn"
                  onClick={() => void deriveCharacter()}
                  disabled={deriveLoading}
                >
                  {deriveLoading ? "Deriving..." : "Derive Preview"}
                </button>
                <button type="button" className="ghost-btn" onClick={() => setView("sheet")}>
                  Open Sheet
                </button>
              </div>

              {deriveError ? <p className="error">{deriveError}</p> : null}

              <div className="preview-panels">
                <article className="panel">
                  <h3>Derived Preview</h3>
                  {deriveResult ? (
                    <div className="derived-grid">
                      <div><strong>HP</strong>: {deriveResult.derived.hp_max}</div>
                      <div><strong>AC</strong>: {deriveResult.derived.ac_total}</div>
                      <div><strong>Touch</strong>: {deriveResult.derived.ac_touch}</div>
                      <div><strong>Flat</strong>: {deriveResult.derived.ac_flat_footed}</div>
                      <div><strong>BAB</strong>: {deriveResult.derived.bab}</div>
                      <div><strong>CMB</strong>: {deriveResult.derived.cmb}</div>
                      <div><strong>CMD</strong>: {deriveResult.derived.cmd}</div>
                      <div><strong>Init</strong>: {deriveResult.derived.initiative}</div>
                      <div><strong>Fort</strong>: {deriveResult.derived.fort}</div>
                      <div><strong>Ref</strong>: {deriveResult.derived.ref}</div>
                      <div><strong>Will</strong>: {deriveResult.derived.will}</div>
                      <div><strong>Level</strong>: {deriveResult.derived.total_level}</div>
                    </div>
                  ) : (
                    <p className="muted">Run derive to preview sheet stats.</p>
                  )}
                </article>

                <article className="panel">
                  <h3>Validation</h3>
                  {validationResult ? (
                    <>
                      <p>
                        Status: <strong>{validationResult.ok ? "valid" : "has issues"}</strong>
                      </p>
                      {validationResult.invalid_feats.length > 0 ? (
                        <ul className="compact-list">
                          {validationResult.invalid_feats.map((invalid) => (
                            <li key={`${invalid.feat_name}-${invalid.level_gained}`}>
                              <span className="row-title">{invalid.feat_name}</span>
                              <span className="reason">Missing: {invalid.missing.join(", ") || "Unknown requirement"}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted">All feat prerequisites pass.</p>
                      )}
                    </>
                  ) : (
                    <p className="muted">Validation results appear here after derive.</p>
                  )}
                </article>
              </div>
            </section>
          ) : null}

          {view === "library" ? (
            <section className="card" data-testid="library-view">
              <div className="section-head">
                <h2>Character Library</h2>
                <button type="button" className="ghost-btn" onClick={resetForNewCharacter}>
                  Create New
                </button>
              </div>

              {libraryError ? <p className="error">{libraryError}</p> : null}
              {libraryLoading ? <p>Loading character library...</p> : null}

              <div className="library-filters">
                <label>
                  Search
                  <input
                    data-testid="library-search"
                    value={searchText}
                    onChange={(event) => setSearchText(event.target.value)}
                    placeholder="name, race, class"
                  />
                </label>
                <label>
                  Race
                  <select value={raceFilter} onChange={(event) => setRaceFilter(event.target.value)}>
                    <option value="all">All races</option>
                    {libraryRaces.map((race) => (
                      <option key={race} value={race}>
                        {race}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Class
                  <select value={classFilter} onChange={(event) => setClassFilter(event.target.value)}>
                    <option value="all">All classes</option>
                    {libraryClasses.map((entry) => (
                      <option key={entry} value={entry}>
                        {entry}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {filteredCharacters.length === 0 ? (
                <p className="muted">No characters match the current filter.</p>
              ) : (
                <div className="card-grid">
                  {filteredCharacters.map((record) => (
                    <article key={record.id} className="library-card" data-testid="library-card">
                      <div className="section-head">
                        <h3>{record.name}</h3>
                        <span className={`pill ${record.source === "server" ? "active" : "deferred"}`}>{record.source}</span>
                      </div>
                      <p className="row-meta">{record.race}</p>
                      <p className="row-meta">{record.class_summary}</p>
                      <p className="row-meta">Level {record.total_level}</p>
                      <p className="row-meta">Updated {formatTimestamp(record.modified_at)}</p>
                      <div className="actions">
                        <button type="button" className="ghost-btn" onClick={() => void editCharacter(record)}>
                          Edit
                        </button>
                        <button type="button" className="primary-btn" onClick={() => void openSheet(record)}>
                          Open Sheet
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          ) : null}

          {view === "dm" ? (
            <section className="card" data-testid="dm-view">
              <div className="section-head">
                <h2>DM Campaign Foundations</h2>
              </div>

              {dmNotice ? <p className="notice">{dmNotice}</p> : null}
              {dmError ? <p className="error">{dmError}</p> : null}

              <div className="dm-layout">
                <article className="panel">
                  <h3>Create Campaign</h3>
                  <div className="form-grid">
                    <label>
                      Campaign Name
                      <input
                        data-testid="dm-campaign-name"
                        value={dmCampaignName}
                        onChange={(event) => setDmCampaignName(event.target.value)}
                      />
                    </label>
                    <label>
                      Owner ID
                      <input
                        data-testid="dm-campaign-owner"
                        value={dmCampaignOwnerId}
                        onChange={(event) => setDmCampaignOwnerId(event.target.value)}
                      />
                    </label>
                  </div>
                  <div className="actions">
                    <button
                      type="button"
                      data-testid="dm-create-campaign"
                      className="primary-btn"
                      onClick={() => void createDmCampaign()}
                    >
                      Create Campaign
                    </button>
                  </div>
                </article>

                <article className="panel">
                  <h3>Campaign List</h3>
                  {dmLoading ? <p className="muted">Loading campaigns...</p> : null}
                  {!dmLoading && dmCampaigns.length === 0 ? <p className="muted">No campaigns yet.</p> : null}
                  <ul className="compact-list">
                    {dmCampaigns.map((campaign) => (
                      <li key={campaign.id}>
                        <span className="row-title">{campaign.name}</span>
                        <span className="row-meta">{campaign.status} • owner {campaign.owner_id}</span>
                        <div className="actions">
                          <button
                            type="button"
                            className="ghost-btn"
                            data-testid={`dm-open-campaign-${campaign.id}`}
                            onClick={() => void openDmCampaign(campaign.id)}
                          >
                            Open
                          </button>
                          {dmSelectedCampaignId === campaign.id ? <span className="pill active">open</span> : null}
                        </div>
                      </li>
                    ))}
                  </ul>
                </article>
              </div>

              <article className="panel" data-testid="dm-party-roster">
                <h3>Party Roster (Read)</h3>
                {selectedDmCampaign ? (
                  <p className="row-meta">
                    Campaign: <strong>{selectedDmCampaign.name}</strong>
                  </p>
                ) : (
                  <p className="muted">Open a campaign to load parties.</p>
                )}
                {dmPartiesLoading ? <p className="muted">Loading party roster...</p> : null}
                {!dmPartiesLoading && selectedDmCampaign && dmParties.length === 0 ? (
                  <p className="muted">No parties found for this campaign.</p>
                ) : null}
                <div className="card-grid">
                  {dmParties.map((party) => (
                    <article key={party.id} className="library-card">
                      <h4>{party.name}</h4>
                      <p className="row-meta">Owner: {party.owner_id}</p>
                      {party.members.length === 0 ? (
                        <p className="muted">No members in roster.</p>
                      ) : (
                        <ul className="compact-list">
                          {party.members.map((member) => (
                            <li key={member.id}>
                              <span className="row-title">{member.display_name}</span>
                              <span className="row-meta">{member.role}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </article>
                  ))}
                </div>
              </article>
            </section>
          ) : null}

          {view === "sheet" ? (
            <section className="card" data-testid="sheet-view">
              <div className="section-head">
                <h2>Character Sheet</h2>
                <div className="actions">
                  <button
                    type="button"
                    className="ghost-btn"
                    onClick={() => setView("creator")}
                  >
                    Back to Creator
                  </button>
                  <button
                    type="button"
                    className="primary-btn"
                    onClick={() =>
                      void deriveCharacter(
                        activePayloadForSheet
                          ? buildDerivePayloadWithSheetConditions(activePayloadForSheet, activeSheetState)
                          : undefined,
                        activeSheetCharacterId ?? undefined,
                        false
                      )
                    }
                    disabled={deriveLoading || !activePayloadForSheet}
                  >
                    {deriveLoading ? "Refreshing..." : "Refresh Derived"}
                  </button>
                </div>
              </div>

              {!activePayloadForSheet ? (
                <p className="muted">No character loaded. Open a character from library or derive from creator.</p>
              ) : (
                <>
                  <div className="sheet-identity" data-testid="sheet-name">
                    <h3>{activePayloadForSheet.name}</h3>
                    <p>
                      {activePayloadForSheet.race} • {classSummary(activePayloadForSheet.class_levels)}
                      {activePayloadForSheet.alignment ? ` • ${activePayloadForSheet.alignment}` : ""}
                    </p>
                  </div>

                  <div className="sheet-grid">
                    <article className="panel">
                      <h4>Core Stats</h4>
                      <div className="derived-grid">
                        <div><strong>Level</strong>: {adjustedDerived?.total_level ?? totalLevel(activePayloadForSheet.class_levels)}</div>
                        <div><strong>HP Max</strong>: {adjustedDerived?.hp_max ?? "-"}</div>
                        <div data-testid="stat-ac"><strong>AC</strong>: {adjustedDerived?.ac_total ?? "-"}</div>
                        <div><strong>Touch</strong>: {adjustedDerived?.ac_touch ?? "-"}</div>
                        <div><strong>Flat</strong>: {adjustedDerived?.ac_flat_footed ?? "-"}</div>
                        <div><strong>BAB</strong>: {adjustedDerived?.bab ?? "-"}</div>
                        <div><strong>CMB</strong>: {adjustedDerived?.cmb ?? "-"}</div>
                        <div><strong>CMD</strong>: {adjustedDerived?.cmd ?? "-"}</div>
                        <div><strong>Init</strong>: {typeof adjustedDerived?.initiative === "number" ? formatSigned(adjustedDerived.initiative) : "-"}</div>
                      </div>
                      <div className="abilities-inline">
                        {ABILITY_KEYS.map((key) => (
                          <span key={key}>
                            {key.toUpperCase()} {activePayloadForSheet.ability_scores[key]} ({abilityMod(activePayloadForSheet.ability_scores[key])})
                          </span>
                        ))}
                      </div>
                    </article>

                    <article className="panel">
                      <h4>Resource Trackers</h4>
                      {activeSheetState ? (
                        <div className="tracker-stack">
                          <div className="resource-row">
                            <label>
                              HP Current
                              <input
                                data-testid="resource-hp-current"
                                type="number"
                                min={0}
                                max={activeSheetState.resources.hp_max}
                                value={activeSheetState.resources.hp_current}
                                onChange={(event) => setSheetResourceValue("hp_current", event.target.value)}
                              />
                            </label>
                            <div className="actions">
                              <button type="button" className="ghost-btn" data-testid="resource-hp-dec" onClick={() => adjustResource("hp_current", -1)}>
                                -1
                              </button>
                              <button type="button" className="ghost-btn" data-testid="resource-hp-inc" onClick={() => adjustResource("hp_current", 1)}>
                                +1
                              </button>
                            </div>
                          </div>
                          <div className="resource-inline">
                            <label>
                              Temp HP
                              <input
                                type="number"
                                min={0}
                                value={activeSheetState.resources.hp_temp}
                                onChange={(event) => setSheetResourceValue("hp_temp", event.target.value)}
                              />
                            </label>
                            <label>
                              Nonlethal
                              <input
                                type="number"
                                min={0}
                                value={activeSheetState.resources.hp_nonlethal}
                                onChange={(event) => setSheetResourceValue("hp_nonlethal", event.target.value)}
                              />
                            </label>
                          </div>
                          <div className="resource-row">
                            <label>
                              Inspiration
                              <input
                                data-testid="resource-inspiration-current"
                                type="number"
                                min={0}
                                max={activeSheetState.resources.inspiration_max}
                                value={activeSheetState.resources.inspiration_current}
                                onChange={(event) => setSheetResourceValue("inspiration_current", event.target.value)}
                              />
                            </label>
                            <p className="row-meta">/ {activeSheetState.resources.inspiration_max}</p>
                            <div className="actions">
                              <button type="button" className="ghost-btn" data-testid="resource-inspiration-dec" onClick={() => adjustResource("inspiration_current", -1)}>
                                -1
                              </button>
                              <button type="button" className="ghost-btn" data-testid="resource-inspiration-inc" onClick={() => adjustResource("inspiration_current", 1)}>
                                +1
                              </button>
                            </div>
                          </div>
                          <div className="consumables-grid">
                            {CONSUMABLE_DEFINITIONS.map((consumable) => (
                              <div key={consumable.key} className="consumable-item">
                                <span className="row-title">{consumable.label}</span>
                                <div className="actions">
                                  <button
                                    type="button"
                                    className="ghost-btn"
                                    data-testid={`resource-consumable-dec-${consumable.key}`}
                                    onClick={() => adjustConsumable(consumable.key, -1)}
                                  >
                                    -
                                  </button>
                                  <span data-testid={`resource-consumable-${consumable.key}`}>
                                    {activeSheetState.resources.consumables[consumable.key] ?? 0}
                                  </span>
                                  <button
                                    type="button"
                                    className="ghost-btn"
                                    data-testid={`resource-consumable-inc-${consumable.key}`}
                                    onClick={() => adjustConsumable(consumable.key, 1)}
                                  >
                                    +
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <p className="muted">Resource tracking is available after loading a character.</p>
                      )}
                    </article>

                    <article className="panel">
                      <h4>Condition Toggles</h4>
                      {activeSheetState ? (
                        <>
                          <div className="condition-grid">
                            {SHEET_CONDITIONS.map((condition) => {
                              const enabled = Boolean(activeSheetState.conditions[condition.key]);
                              return (
                                <label key={condition.key} className={`condition-item ${enabled ? "active" : ""}`}>
                                  <input
                                    type="checkbox"
                                    data-testid={`condition-toggle-${condition.key}`}
                                    checked={enabled}
                                    onChange={(event) => toggleSheetCondition(condition.key, event.target.checked)}
                                  />
                                  <span className="row-title">{condition.label}</span>
                                  <span className="reason">{condition.detail}</span>
                                  <div className="condition-flags">
                                    {condition.extract_linked ? <span className="pill active">extract</span> : null}
                                    {condition.requires_derive ? <span className="pill deferred">derive</span> : null}
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                          {conditionDelta.requires_derive ? (
                            <p className="muted">One or more active conditions are derive-linked; the sheet refreshes derive when those toggles change.</p>
                          ) : null}
                        </>
                      ) : (
                        <p className="muted">Condition toggles are available after loading a character.</p>
                      )}
                    </article>

                    <article className="panel">
                      <h4>Quick Combat</h4>
                      {activeSheetState ? (
                        <div className="tracker-stack" data-testid="quick-combat-panel">
                          <div className="resource-inline">
                            <label>
                              Initiative Roll
                              <input
                                data-testid="combat-initiative-roll"
                                type="number"
                                value={activeSheetState.quick_combat.initiative_roll}
                                onChange={(event) => setQuickCombatField("initiative_roll", event.target.value)}
                                placeholder="d20"
                              />
                            </label>
                            <p className="row-meta">
                              Total: {typeof quickInitiativeTotal === "number" ? quickInitiativeTotal : "--"}
                            </p>
                          </div>
                          <label>
                            Attack Preset
                            <select
                              value={activeSheetState.quick_combat.selected_attack_index}
                              onChange={(event) =>
                                setQuickCombatField("selected_attack_index", Number.parseInt(event.target.value || "0", 10))
                              }
                            >
                              {combatAttackLines.length === 0 ? <option value={0}>No derived attacks</option> : null}
                              {combatAttackLines.map((attack, index) => (
                                <option key={`${attack.name}-${index}`} value={index}>
                                  {attack.name}
                                </option>
                              ))}
                            </select>
                          </label>
                          {selectedAttackLine ? (
                            <p className="row-meta" data-testid="combat-selected-attack">
                              {selectedAttackLine.name}: {formatSigned(selectedAttackLine.attack_bonus)} to hit, {selectedAttackLine.damage}
                            </p>
                          ) : null}
                          <label>
                            Damage Notes
                            <textarea
                              data-testid="combat-damage-notes"
                              value={activeSheetState.quick_combat.damage_notes}
                              onChange={(event) => setQuickCombatField("damage_notes", event.target.value)}
                              placeholder="Track rider effects, DR, resistance, and triggers."
                            />
                          </label>
                          <div>
                            <strong>Condition Summary</strong>
                            {conditionDelta.active_labels.length > 0 ? (
                              <ul className="compact-list" data-testid="condition-summary">
                                {conditionDelta.active_labels.map((label) => (
                                  <li key={label}>
                                    <span className="row-title">{label}</span>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="muted" data-testid="condition-summary">No active sheet conditions.</p>
                            )}
                          </div>
                          <div className="shortcut-grid">
                            <span className="row-title">Fort {typeof adjustedDerived?.fort === "number" ? formatSigned(adjustedDerived.fort) : "--"}</span>
                            <span className="row-title" data-testid="stat-ref">
                              Ref {typeof adjustedDerived?.ref === "number" ? formatSigned(adjustedDerived.ref) : "--"}
                            </span>
                            <span className="row-title">Will {typeof adjustedDerived?.will === "number" ? formatSigned(adjustedDerived.will) : "--"}</span>
                            {keySkillShortcuts.map((skill) => (
                              <span key={skill.name} className="row-meta">
                                {skill.name}: {typeof skill.value === "number" ? formatSigned(skill.value) : "--"}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <p className="muted">Quick combat appears after loading a character.</p>
                      )}
                    </article>

                    <article className="panel">
                      <h4>Saves</h4>
                      <div className="derived-grid">
                        <div><strong>Fort</strong>: {typeof adjustedDerived?.fort === "number" ? formatSigned(adjustedDerived.fort) : "-"}</div>
                        <div><strong>Ref</strong>: {typeof adjustedDerived?.ref === "number" ? formatSigned(adjustedDerived.ref) : "-"}</div>
                        <div><strong>Will</strong>: {typeof adjustedDerived?.will === "number" ? formatSigned(adjustedDerived.will) : "-"}</div>
                      </div>
                    </article>

                    <article className="panel">
                      <h4>Attacks</h4>
                      {adjustedDerived?.attack_lines && adjustedDerived.attack_lines.length > 0 ? (
                        <ul className="compact-list">
                          {adjustedDerived.attack_lines.map((attack) => (
                            <li key={`${attack.name}-${attack.attack_bonus}-${attack.damage}`}>
                              <span className="row-title">{attack.name}</span>
                              <span className="row-meta">{formatSigned(attack.attack_bonus)} • {attack.damage}</span>
                              {attack.notes ? <span className="reason">{attack.notes}</span> : null}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted">No attack lines derived yet.</p>
                      )}
                    </article>

                    <article className="panel">
                      <h4>Skills</h4>
                      <ul className="compact-list">
                        {Object.entries(displaySkillTotals)
                          .sort(([a], [b]) => a.localeCompare(b))
                          .map(([name, value]) => (
                            <li key={name}>
                              <span className="row-title">{name}</span>
                              <span className="row-meta">{formatSigned(value)}</span>
                            </li>
                          ))}
                      </ul>
                    </article>

                    <article className="panel">
                      <h4>Feats</h4>
                      {activePayloadForSheet.feats.length > 0 ? (
                        <ul className="compact-list">
                          {activePayloadForSheet.feats.map((feat) => {
                            const prereq = activeDerived?.feat_prereq_results.find((result) => result.feat_name === feat.name);
                            return (
                              <li key={`${feat.name}-${feat.level_gained}`}>
                                <span className="row-title">{feat.name}</span>
                                <span className="row-meta">Level {feat.level_gained}</span>
                                {prereq ? (
                                  <span className={`pill ${prereq.valid ? "active" : "deferred"}`}>
                                    {prereq.valid ? "valid" : "invalid"}
                                  </span>
                                ) : null}
                              </li>
                            );
                          })}
                        </ul>
                      ) : (
                        <p className="muted">No feats selected.</p>
                      )}
                    </article>

                    <article className="panel">
                      <h4>Equipment</h4>
                      {activePayloadForSheet.equipment.length > 0 ? (
                        <ul className="compact-list">
                          {activePayloadForSheet.equipment.map((item) => (
                            <li key={`${item.name}-${item.kind}-${item.quantity}`}>
                              <span className="row-title">{item.name}</span>
                              <span className="row-meta">{item.kind} × {item.quantity}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted">No equipment listed.</p>
                      )}
                    </article>

                    <article className="panel">
                      <div className="section-head">
                        <h4>Spells / Extracts</h4>
                        <div className="actions">
                          <button type="button" className="ghost-btn" data-testid="rest-short" onClick={() => applyRest("short")}>
                            Short Rest
                          </button>
                          <button type="button" className="ghost-btn" data-testid="rest-full" onClick={() => applyRest("full")}>
                            Full Rest
                          </button>
                        </div>
                      </div>
                      {activeSheetState && spellLevels.length > 0 ? (
                        <ul className="compact-list" data-testid="spell-trackers">
                          {spellLevels.map(([level, tracker]) => (
                            <li key={level}>
                              <span className="row-title">Level {level}</span>
                              <div className="spell-counter-grid">
                                <span className="row-meta">Known</span>
                                <button type="button" className="ghost-btn" onClick={() => adjustSpellTracker(level, "known", -1)}>-</button>
                                <span>{tracker.known}</span>
                                <button type="button" className="ghost-btn" onClick={() => adjustSpellTracker(level, "known", 1)}>+</button>
                                <span className="row-meta">Prepared</span>
                                <button type="button" className="ghost-btn" onClick={() => adjustSpellTracker(level, "prepared", -1)}>-</button>
                                <span>{tracker.prepared}</span>
                                <button type="button" className="ghost-btn" onClick={() => adjustSpellTracker(level, "prepared", 1)}>+</button>
                                <span className="row-meta">Used</span>
                                <button
                                  type="button"
                                  className="ghost-btn"
                                  data-testid={`spell-used-dec-${level}`}
                                  onClick={() => adjustSpellTracker(level, "used", -1)}
                                >
                                  -
                                </button>
                                <span data-testid={`spell-used-${level}`}>{tracker.used}</span>
                                <button
                                  type="button"
                                  className="ghost-btn"
                                  data-testid={`spell-used-inc-${level}`}
                                  onClick={() => adjustSpellTracker(level, "used", 1)}
                                >
                                  +
                                </button>
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted">No spell/extract slots derived.</p>
                      )}
                    </article>
                  </div>
                </>
              )}
            </section>
          ) : null}
        </section>
      </div>

      {contentLoading ? <p className="muted footer-note">Loading content catalogs...</p> : null}
    </main>
  );
}
