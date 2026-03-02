import { useEffect, useMemo, useState } from "react";

type Health = {
  ok: boolean;
  env: string;
  version: string;
};

type FeatRow = {
  id: number;
  name: string;
  feat_type: string;
  prerequisites: string;
  benefit: string;
  source_book: string;
  ui_enabled?: number | boolean;
  ui_tier?: string;
  policy_reason?: string;
};

type RaceRow = {
  id: number;
  name: string;
  race_type: string;
  size: string;
  base_speed: number;
  source_book: string;
  ui_enabled?: number | boolean;
  ui_tier?: string;
  policy_reason?: string;
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

type CharacterDraft = {
  name: string;
  race: string;
  class_name: string;
  class_level: number;
  ability_scores: AbilityScores;
  feat_input: string;
};

type SavedCharacter = CharacterDraft & {
  id: string;
  created_at: string;
  modified_at: string;
};

type AttackLine = {
  name: string;
  attack_bonus: number;
  damage: string;
  notes?: string;
};

type FeatPrereqResult = {
  feat_name: string;
  level_gained: number;
  valid: boolean;
  missing: string[];
};

type DerivedStats = {
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
  spell_slots?: Record<string, number>;
  skill_totals?: Record<string, number>;
  attack_lines?: AttackLine[];
  feat_prereq_results?: FeatPrereqResult[];
};

type DeriveResponse = {
  derived: DerivedStats;
};

const STORAGE_KEY = "pf1e.v2.character.workflow";
const ABILITY_KEYS = ["str", "dex", "con", "int", "wis", "cha"] as const;

const DEFAULT_DRAFT: CharacterDraft = {
  name: "Kairon",
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
  feat_input: "Weapon Finesse, Weapon Focus, Rapid Shot",
};

function isDeferredRow(row: { ui_enabled?: number | boolean; ui_tier?: string }): boolean {
  return row.ui_tier === "deferred" || row.ui_enabled === 0 || row.ui_enabled === false;
}

function generateCharacterId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function toSafeNumber(value: unknown, fallback: number): number {
  const candidate = typeof value === "number" ? value : Number.parseInt(String(value), 10);
  return Number.isFinite(candidate) ? candidate : fallback;
}

function parseStoredCharacters(raw: string | null): SavedCharacter[] {
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .map((entry) => {
        const objectValue = typeof entry === "object" && entry !== null ? (entry as Record<string, unknown>) : {};
        const abilitySource =
          typeof objectValue.ability_scores === "object" && objectValue.ability_scores !== null
            ? (objectValue.ability_scores as Record<string, unknown>)
            : {};
        const classLevel = Math.max(1, Math.min(20, toSafeNumber(objectValue.class_level, DEFAULT_DRAFT.class_level)));
        const createdAt = typeof objectValue.created_at === "string" ? objectValue.created_at : new Date().toISOString();
        const modifiedAt =
          typeof objectValue.modified_at === "string" ? objectValue.modified_at : typeof objectValue.created_at === "string" ? objectValue.created_at : new Date().toISOString();

        return {
          id: typeof objectValue.id === "string" ? objectValue.id : generateCharacterId(),
          name: typeof objectValue.name === "string" && objectValue.name.trim().length > 0 ? objectValue.name : "Unnamed",
          race: typeof objectValue.race === "string" ? objectValue.race : DEFAULT_DRAFT.race,
          class_name: typeof objectValue.class_name === "string" ? objectValue.class_name : DEFAULT_DRAFT.class_name,
          class_level: classLevel,
          ability_scores: {
            str: Math.max(1, toSafeNumber(abilitySource.str, DEFAULT_DRAFT.ability_scores.str)),
            dex: Math.max(1, toSafeNumber(abilitySource.dex, DEFAULT_DRAFT.ability_scores.dex)),
            con: Math.max(1, toSafeNumber(abilitySource.con, DEFAULT_DRAFT.ability_scores.con)),
            int: Math.max(1, toSafeNumber(abilitySource.int, DEFAULT_DRAFT.ability_scores.int)),
            wis: Math.max(1, toSafeNumber(abilitySource.wis, DEFAULT_DRAFT.ability_scores.wis)),
            cha: Math.max(1, toSafeNumber(abilitySource.cha, DEFAULT_DRAFT.ability_scores.cha)),
          },
          feat_input: typeof objectValue.feat_input === "string" ? objectValue.feat_input : "",
          created_at: createdAt,
          modified_at: modifiedAt,
        };
      })
      .sort((a, b) => b.modified_at.localeCompare(a.modified_at));
  } catch {
    return [];
  }
}

function loadStoredCharacters(): SavedCharacter[] {
  if (typeof window === "undefined") {
    return [];
  }
  return parseStoredCharacters(window.localStorage.getItem(STORAGE_KEY));
}

function draftFromSaved(character: SavedCharacter): CharacterDraft {
  return {
    name: character.name,
    race: character.race,
    class_name: character.class_name,
    class_level: character.class_level,
    ability_scores: { ...character.ability_scores },
    feat_input: character.feat_input,
  };
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

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [includeDeferred, setIncludeDeferred] = useState<boolean>(false);
  const [feats, setFeats] = useState<FeatRow[]>([]);
  const [races, setRaces] = useState<RaceRow[]>([]);
  const [policy, setPolicy] = useState<PolicySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  const [savedCharacters, setSavedCharacters] = useState<SavedCharacter[]>(() => loadStoredCharacters());
  const [activeCharacterId, setActiveCharacterId] = useState<string | null>(null);
  const [draft, setDraft] = useState<CharacterDraft>(DEFAULT_DRAFT);
  const [draftDirty, setDraftDirty] = useState<boolean>(false);
  const [workflowNotice, setWorkflowNotice] = useState<string>("");
  const [libraryBootstrapped, setLibraryBootstrapped] = useState<boolean>(false);

  const [deriveLoading, setDeriveLoading] = useState<boolean>(false);
  const [deriveError, setDeriveError] = useState<string>("");
  const [derivedStats, setDerivedStats] = useState<DerivedStats | null>(null);

  const base = import.meta.env.VITE_API_BASE ?? "http://localhost:8100";

  useEffect(() => {
    fetch(`${base}/health`)
      .then((response) => response.json())
      .then((json: Health) => setHealth(json))
      .catch(() => setHealth(null));
  }, [base]);

  useEffect(() => {
    const query = includeDeferred ? "?include_deferred=true" : "";
    setLoading(true);
    setError("");

    Promise.all([
      fetch(`${base}/api/v2/content/feats${query}`).then((response) => response.json()),
      fetch(`${base}/api/v2/content/races${query}`).then((response) => response.json()),
      fetch(`${base}/api/v2/content/policy-summary`).then((response) => response.json()),
    ])
      .then(([featRows, raceRows, policySummary]: [FeatRow[], RaceRow[], PolicySummary]) => {
        setFeats(featRows);
        setRaces(raceRows);
        setPolicy(policySummary);
      })
      .catch(() => {
        setError("Unable to load content data from API.");
        setFeats([]);
        setRaces([]);
        setPolicy(null);
      })
      .finally(() => setLoading(false));
  }, [base, includeDeferred]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(savedCharacters));
  }, [savedCharacters]);

  useEffect(() => {
    if (libraryBootstrapped) {
      return;
    }
    if (savedCharacters.length === 0) {
      setLibraryBootstrapped(true);
      return;
    }
    const first = savedCharacters[0];
    setActiveCharacterId(first.id);
    setDraft(draftFromSaved(first));
    setLibraryBootstrapped(true);
  }, [libraryBootstrapped, savedCharacters]);

  useEffect(() => {
    if (races.length === 0) {
      return;
    }
    const hasRace = races.some((race) => race.name === draft.race);
    if (!hasRace) {
      setDraft((prev) => ({ ...prev, race: races[0].name }));
    }
  }, [draft.race, races]);

  const topDeferredReason = policy
    ? Object.entries(policy.reason_counts)
        .filter(([reason]) => reason !== "allowlisted")
        .sort((a, b) => b[1] - a[1])[0]?.[0] ?? "none"
    : "none";

  const visibleFeats = useMemo(
    () => (includeDeferred ? feats : feats.filter((feat) => !isDeferredRow(feat))),
    [feats, includeDeferred]
  );
  const visibleRaces = useMemo(
    () => (includeDeferred ? races : races.filter((race) => !isDeferredRow(race))),
    [includeDeferred, races]
  );

  const selectedRaceRow = races.find((race) => race.name === draft.race) ?? null;
  const selectedRaceHiddenByMode = Boolean(selectedRaceRow && isDeferredRow(selectedRaceRow) && !includeDeferred);

  const raceOptions = useMemo(() => {
    if (!selectedRaceRow) {
      return visibleRaces;
    }
    if (visibleRaces.some((race) => race.name === selectedRaceRow.name)) {
      return visibleRaces;
    }
    return [selectedRaceRow, ...visibleRaces];
  }, [selectedRaceRow, visibleRaces]);

  const activeCharacter = activeCharacterId
    ? savedCharacters.find((character) => character.id === activeCharacterId) ?? null
    : null;

  const sortedCharacters = useMemo(
    () => [...savedCharacters].sort((a, b) => b.modified_at.localeCompare(a.modified_at)),
    [savedCharacters]
  );

  function updateDraftField<K extends keyof CharacterDraft>(key: K, value: CharacterDraft[K]) {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setDraftDirty(true);
    setWorkflowNotice("");
  }

  function updateAbility(key: keyof AbilityScores, value: string) {
    const parsed = Math.max(1, toSafeNumber(value, draft.ability_scores[key]));
    setDraft((prev) => ({
      ...prev,
      ability_scores: {
        ...prev.ability_scores,
        [key]: parsed,
      },
    }));
    setDraftDirty(true);
    setWorkflowNotice("");
  }

  function startNewCharacter() {
    const fallbackRace = visibleRaces[0]?.name ?? races[0]?.name ?? DEFAULT_DRAFT.race;
    setActiveCharacterId(null);
    setDraft({ ...DEFAULT_DRAFT, race: fallbackRace });
    setDraftDirty(false);
    setDerivedStats(null);
    setDeriveError("");
    setWorkflowNotice("Started a new character draft.");
  }

  function loadCharacter(characterId: string) {
    const match = sortedCharacters.find((character) => character.id === characterId);
    if (!match) {
      return;
    }
    setActiveCharacterId(match.id);
    setDraft(draftFromSaved(match));
    setDraftDirty(false);
    setDerivedStats(null);
    setDeriveError("");
    setWorkflowNotice(`Loaded ${match.name}.`);
  }

  function saveCharacter(mode: "update" | "new" = "update") {
    const timestamp = new Date().toISOString();
    const normalizedName = draft.name.trim() || "Unnamed";
    const canUpdate = mode === "update" && activeCharacterId !== null && savedCharacters.some((character) => character.id === activeCharacterId);

    if (canUpdate && activeCharacterId) {
      setSavedCharacters((prev) =>
        prev
          .map((character) =>
            character.id === activeCharacterId
              ? {
                  ...character,
                  ...draft,
                  name: normalizedName,
                  modified_at: timestamp,
                }
              : character
          )
          .sort((a, b) => b.modified_at.localeCompare(a.modified_at))
      );
      setDraft((prev) => ({ ...prev, name: normalizedName }));
      setDraftDirty(false);
      setWorkflowNotice("Character saved.");
      return;
    }

    const id = generateCharacterId();
    const createdCharacter: SavedCharacter = {
      id,
      ...draft,
      name: normalizedName,
      created_at: timestamp,
      modified_at: timestamp,
    };

    setSavedCharacters((prev) => [createdCharacter, ...prev].sort((a, b) => b.modified_at.localeCompare(a.modified_at)));
    setActiveCharacterId(id);
    setDraft((prev) => ({ ...prev, name: normalizedName }));
    setDraftDirty(false);
    setWorkflowNotice(mode === "new" ? "Character saved as a new entry." : "Character created.");
  }

  async function deriveCharacter() {
    setDeriveError("");
    setDeriveLoading(true);

    try {
      const featNames = draft.feat_input
        .split(",")
        .map((name) => name.trim())
        .filter((name) => name.length > 0);

      const payload = {
        name: draft.name.trim() || "Unnamed",
        race: draft.race || "Tiefling",
        ability_scores: draft.ability_scores,
        class_levels: [{ class_name: draft.class_name.trim() || "Investigator", level: draft.class_level }],
        feats: featNames.map((name, index) => ({
          name,
          level_gained: Math.max(1, Math.min(draft.class_level, 1 + index * 2)),
          method: "general",
        })),
        traits: [],
        skills: {},
        equipment: [],
        conditions: [],
      };

      const response = await fetch(`${base}/api/v2/rules/derive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`derive_failed_${response.status}`);
      }

      const body: DeriveResponse = await response.json();
      setDerivedStats(body.derived);
      setWorkflowNotice("Derived stats refreshed from API.");
    } catch {
      setDeriveError("Could not derive character stats from API.");
      setDerivedStats(null);
    } finally {
      setDeriveLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <h1>PF1e Character Workflow</h1>
        <p>Create, edit, save, load, and derive slice stats with deferred-content controls for player vs DM/dev mode.</p>
      </header>

      <div className="workflow-layout">
        <aside className="workflow-sidebar">
          <section className="card controls">
            <div className="section-head">
              <h2>Content Mode</h2>
              <span className={`pill ${includeDeferred ? "deferred" : "active"}`}>{includeDeferred ? "DM/Dev" : "Player"}</span>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={includeDeferred}
                onChange={(event) => setIncludeDeferred(event.target.checked)}
              />
              <span>Include Deferred Content</span>
            </label>
            <p className="muted">
              Player mode hides deferred rows. DM/dev mode exposes deferred entries and policy metadata.
            </p>
          </section>

          <section className="card status">
            <h2>API + Policy</h2>
            {health ? (
              <p>
                Connected: env={health.env}, version={health.version}
              </p>
            ) : (
              <p>Not connected to API yet.</p>
            )}
            {policy ? (
              <div className="status-stack">
                <p>Accepted rows: {policy.accepted_total}</p>
                <p>Active rows: {policy.active_total}</p>
                <p>Deferred rows: {policy.deferred_total}</p>
                <p className="muted">Top deferred reason: {topDeferredReason}</p>
              </div>
            ) : null}
          </section>

          <section className="card character-library">
            <div className="section-head">
              <h2>Character Library</h2>
              <button type="button" className="ghost-btn" onClick={startNewCharacter}>
                New Draft
              </button>
            </div>
            {sortedCharacters.length === 0 ? (
              <p className="muted">No saved characters yet. Create one and click save.</p>
            ) : (
              <ul className="character-list">
                {sortedCharacters.map((character) => (
                  <li key={character.id}>
                    <button
                      type="button"
                      className={`character-item ${activeCharacterId === character.id ? "active" : ""}`}
                      onClick={() => loadCharacter(character.id)}
                    >
                      <span className="row-title">{character.name}</span>
                      <span className="row-meta">
                        {character.race} • {character.class_name} {character.class_level}
                      </span>
                      <span className="row-meta">Updated {formatTimestamp(character.modified_at)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>

        <section className="workflow-main">
          <section className="card creator">
            <div className="section-head creator-head">
              <h2>Character Editor</h2>
              <div className="editor-actions">
                <button type="button" className="ghost-btn" onClick={() => saveCharacter("new")}>
                  Save As New
                </button>
                <button type="button" className="primary-btn" onClick={() => saveCharacter("update")}>
                  {activeCharacter ? "Save Character" : "Create Character"}
                </button>
              </div>
            </div>

            <p className={`editor-state ${draftDirty ? "dirty" : ""}`}>
              {draftDirty
                ? "Unsaved changes in current draft."
                : activeCharacter
                  ? `Loaded ${activeCharacter.name}.`
                  : "Editing a new unsaved draft."}
            </p>
            {workflowNotice ? <p className="notice">{workflowNotice}</p> : null}

            <div className="form-grid">
              <label>
                Name
                <input value={draft.name} onChange={(event) => updateDraftField("name", event.target.value)} />
              </label>
              <label>
                Race
                <select value={draft.race} onChange={(event) => updateDraftField("race", event.target.value)}>
                  {raceOptions.map((race) => (
                    <option key={race.name} value={race.name}>
                      {race.name}
                      {isDeferredRow(race) ? " (deferred)" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Class
                <input value={draft.class_name} onChange={(event) => updateDraftField("class_name", event.target.value)} />
              </label>
              <label>
                Level
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={draft.class_level}
                  onChange={(event) => {
                    const parsedLevel = toSafeNumber(event.target.value, draft.class_level);
                    updateDraftField("class_level", Math.max(1, Math.min(20, parsedLevel)));
                  }}
                />
              </label>
            </div>

            {selectedRaceHiddenByMode ? (
              <p className="warning-text">
                Current race is deferred content. Enable DM/dev mode to browse other deferred races.
              </p>
            ) : null}

            <div className="abilities">
              {ABILITY_KEYS.map((key) => (
                <label key={key}>
                  {key.toUpperCase()}
                  <input
                    type="number"
                    min={1}
                    value={draft.ability_scores[key]}
                    onChange={(event) => updateAbility(key, event.target.value)}
                  />
                </label>
              ))}
            </div>

            <label className="full-width">
              Feats (comma separated)
              <input
                list="feat-suggestions"
                value={draft.feat_input}
                onChange={(event) => updateDraftField("feat_input", event.target.value)}
              />
            </label>
            <datalist id="feat-suggestions">
              {visibleFeats.map((feat) => (
                <option key={`${feat.id}-${feat.name}`} value={feat.name} />
              ))}
            </datalist>
            <p className="muted">Feat suggestions available in current mode: {visibleFeats.length}</p>

            <div className="derive-actions">
              <button className="primary-btn derive-btn" onClick={deriveCharacter} disabled={deriveLoading}>
                {deriveLoading ? "Deriving..." : "Derive Stats"}
              </button>
              {derivedStats && draftDirty ? <span className="stale-pill">Derived stats may be outdated</span> : null}
            </div>

            {deriveError ? <p className="error">{deriveError}</p> : null}

            {derivedStats ? (
              <div className="derived-panel">
                <h3>Derived Snapshot</h3>
                <div className="derived-grid">
                  <div>
                    <strong>Level</strong>: {derivedStats.total_level}
                  </div>
                  <div>
                    <strong>BAB</strong>: {derivedStats.bab}
                  </div>
                  <div>
                    <strong>Fort</strong>: {derivedStats.fort}
                  </div>
                  <div>
                    <strong>Ref</strong>: {derivedStats.ref}
                  </div>
                  <div>
                    <strong>Will</strong>: {derivedStats.will}
                  </div>
                  <div>
                    <strong>HP</strong>: {derivedStats.hp_max}
                  </div>
                  <div>
                    <strong>AC</strong>: {derivedStats.ac_total}
                  </div>
                  <div>
                    <strong>Touch</strong>: {derivedStats.ac_touch}
                  </div>
                  <div>
                    <strong>Flat</strong>: {derivedStats.ac_flat_footed}
                  </div>
                  <div>
                    <strong>CMB</strong>: {derivedStats.cmb}
                  </div>
                  <div>
                    <strong>CMD</strong>: {derivedStats.cmd}
                  </div>
                  <div>
                    <strong>Init</strong>: {derivedStats.initiative}
                  </div>
                </div>

                {derivedStats.attack_lines && derivedStats.attack_lines.length > 0 ? (
                  <div className="subpanel">
                    <h4>Attack Lines</h4>
                    <ul className="compact-list">
                      {derivedStats.attack_lines.map((attack) => (
                        <li key={`${attack.name}-${attack.attack_bonus}-${attack.damage}`}>
                          <span className="row-title">{attack.name}</span>
                          <span className="row-meta">
                            +{attack.attack_bonus} • {attack.damage}
                          </span>
                          {attack.notes ? <span className="reason">{attack.notes}</span> : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {derivedStats.feat_prereq_results && derivedStats.feat_prereq_results.length > 0 ? (
                  <div className="subpanel">
                    <h4>Feat Validation</h4>
                    <ul className="compact-list prereq-list">
                      {derivedStats.feat_prereq_results.map((result) => (
                        <li key={`${result.feat_name}-${result.level_gained}`}>
                          <span className="row-title">{result.feat_name}</span>
                          <span className={`pill ${result.valid ? "active" : "deferred"}`}>
                            {result.valid ? "valid" : "invalid"}
                          </span>
                          {!result.valid && result.missing.length > 0 ? (
                            <span className="reason">Missing: {result.missing.join(", ")}</span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="muted derive-placeholder">Run derive to compute defensive stats, attacks, and feat prerequisites.</p>
            )}
          </section>

          <section className="grid content-grid">
            <article className="card">
              <div className="section-head">
                <h2>Feats ({visibleFeats.length})</h2>
                <span className={`pill ${includeDeferred ? "deferred" : "active"}`}>{includeDeferred ? "all tiers" : "active only"}</span>
              </div>
              {loading ? <p>Loading feats...</p> : null}
              {error ? <p className="error">{error}</p> : null}
              <ul className="compact-list">
                {visibleFeats.slice(0, 14).map((feat) => (
                  <li key={`${feat.id}-${feat.name}`}>
                    <span className="row-title">{feat.name}</span>
                    <span className="row-meta">{feat.source_book}</span>
                    {isDeferredRow(feat) ? <span className="pill deferred">deferred</span> : null}
                    {feat.policy_reason ? <span className="reason">{feat.policy_reason}</span> : null}
                  </li>
                ))}
              </ul>
            </article>

            <article className="card">
              <div className="section-head">
                <h2>Races ({visibleRaces.length})</h2>
                <span className={`pill ${includeDeferred ? "deferred" : "active"}`}>{includeDeferred ? "all tiers" : "active only"}</span>
              </div>
              {loading ? <p>Loading races...</p> : null}
              {error ? <p className="error">{error}</p> : null}
              <ul className="compact-list">
                {visibleRaces.slice(0, 14).map((race) => (
                  <li key={`${race.id}-${race.name}`}>
                    <span className="row-title">{race.name}</span>
                    <span className="row-meta">{race.source_book}</span>
                    {isDeferredRow(race) ? <span className="pill deferred">deferred</span> : null}
                    {race.policy_reason ? <span className="reason">{race.policy_reason}</span> : null}
                  </li>
                ))}
              </ul>
            </article>
          </section>
        </section>
      </div>
    </main>
  );
}
