import { useEffect, useState } from "react";

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
};

type DeriveResponse = {
  derived: DerivedStats;
};

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [includeDeferred, setIncludeDeferred] = useState<boolean>(false);
  const [feats, setFeats] = useState<FeatRow[]>([]);
  const [races, setRaces] = useState<RaceRow[]>([]);
  const [policy, setPolicy] = useState<PolicySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [characterName, setCharacterName] = useState<string>("Kairon");
  const [selectedRace, setSelectedRace] = useState<string>("Tiefling");
  const [className, setClassName] = useState<string>("Investigator");
  const [classLevel, setClassLevel] = useState<number>(9);
  const [abilityScores, setAbilityScores] = useState<AbilityScores>({
    str: 12,
    dex: 18,
    con: 12,
    int: 17,
    wis: 18,
    cha: 14,
  });
  const [featInput, setFeatInput] = useState<string>("Weapon Finesse, Weapon Focus, Rapid Shot");
  const [deriveLoading, setDeriveLoading] = useState<boolean>(false);
  const [deriveError, setDeriveError] = useState<string>("");
  const [derivedStats, setDerivedStats] = useState<DerivedStats | null>(null);

  const base = import.meta.env.VITE_API_BASE ?? "http://localhost:8100";

  useEffect(() => {
    fetch(`${base}/health`)
      .then((r) => r.json())
      .then((json: Health) => setHealth(json))
      .catch(() => setHealth(null));
  }, [base]);

  useEffect(() => {
    const query = includeDeferred ? "?include_deferred=true" : "";
    setLoading(true);
    setError("");

    Promise.all([
      fetch(`${base}/api/v2/content/feats${query}`).then((r) => r.json()),
      fetch(`${base}/api/v2/content/races${query}`).then((r) => r.json()),
      fetch(`${base}/api/v2/content/policy-summary`).then((r) => r.json()),
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
    if (!selectedRace && races.length > 0) {
      setSelectedRace(races[0].name);
    }
  }, [races, selectedRace]);

  const topDeferredReason = policy
    ? Object.entries(policy.reason_counts)
        .filter(([reason]) => reason !== "allowlisted")
        .sort((a, b) => b[1] - a[1])[0]?.[0] ?? "none"
    : "none";

  function updateAbility(key: keyof AbilityScores, value: string) {
    const parsed = Number.parseInt(value, 10);
    setAbilityScores((prev) => ({
      ...prev,
      [key]: Number.isFinite(parsed) ? parsed : prev[key],
    }));
  }

  async function deriveCharacter() {
    setDeriveError("");
    setDeriveLoading(true);
    setDerivedStats(null);
    try {
      const featNames = featInput
        .split(",")
        .map((name) => name.trim())
        .filter((name) => name.length > 0);

      const payload = {
        name: characterName.trim() || "Unnamed",
        race: selectedRace || "Tiefling",
        ability_scores: abilityScores,
        class_levels: [{ class_name: className.trim() || "Investigator", level: classLevel }],
        feats: featNames.map((name, index) => ({
          name,
          level_gained: Math.max(1, Math.min(classLevel, 1 + index * 2)),
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
    } catch {
      setDeriveError("Could not derive character stats from API.");
    } finally {
      setDeriveLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <h1>PF1e Kingmaker V2</h1>
        <p>Data-first rebuild with deterministic ingestion and V2 contracts.</p>
      </header>

      <section className="card controls">
        <h2>Content View</h2>
        <label className="toggle">
          <input
            type="checkbox"
            checked={includeDeferred}
            onChange={(e) => setIncludeDeferred(e.target.checked)}
          />
          <span>Show Deferred Content (DM/Dev)</span>
        </label>
        <p className="muted">
          Players should keep this off. DM/dev mode includes deferred rows and policy metadata.
        </p>
      </section>

      <section className="grid">
        <article className="card">
          <h2>Phase 0</h2>
          <p>Monorepo, Docker, CI, FastAPI + React shells.</p>
        </article>
        <article className="card">
          <h2>Phase 1</h2>
          <p>Deterministic extract/parse/validate/load pipeline with provenance.</p>
        </article>
        <article className="card">
          <h2>Milestone 1</h2>
          <p>Kairon slice with strict quality gates and golden checks.</p>
        </article>
      </section>

      <section className="status card">
        <h2>API Health</h2>
        {health ? (
          <p>
            Connected: env={health.env}, version={health.version}
          </p>
        ) : (
          <p>Not connected to API yet.</p>
        )}
      </section>

      <section className="grid content-grid">
        <article className="card">
          <h2>Policy Summary</h2>
          {policy ? (
            <>
              <p>Total accepted rows: {policy.accepted_total}</p>
              <p>Active rows: {policy.active_total}</p>
              <p>Deferred rows: {policy.deferred_total}</p>
              <p className="muted">Top deferred reason: {topDeferredReason}</p>
            </>
          ) : (
            <p>{loading ? "Loading policy summary..." : "No policy summary available."}</p>
          )}
        </article>

        <article className="card">
          <h2>Feats ({feats.length})</h2>
          {loading ? <p>Loading feats...</p> : null}
          {error ? <p className="error">{error}</p> : null}
          <ul className="compact-list">
            {feats.slice(0, 12).map((feat) => (
              <li key={`${feat.id}-${feat.name}`}>
                <span className="row-title">{feat.name}</span>
                <span className="row-meta">{feat.source_book}</span>
                {includeDeferred && feat.ui_tier ? <span className={`pill ${feat.ui_tier}`}>{feat.ui_tier}</span> : null}
                {includeDeferred && feat.policy_reason ? <span className="reason">{feat.policy_reason}</span> : null}
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h2>Races ({races.length})</h2>
          {loading ? <p>Loading races...</p> : null}
          {error ? <p className="error">{error}</p> : null}
          <ul className="compact-list">
            {races.slice(0, 12).map((race) => (
              <li key={`${race.id}-${race.name}`}>
                <span className="row-title">{race.name}</span>
                <span className="row-meta">{race.source_book}</span>
                {includeDeferred && race.ui_tier ? <span className={`pill ${race.ui_tier}`}>{race.ui_tier}</span> : null}
                {includeDeferred && race.policy_reason ? <span className="reason">{race.policy_reason}</span> : null}
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="card creator">
        <h2>Character Creator (Slice)</h2>
        <p className="muted">Minimal creator wired to `/api/v2/rules/derive` for deterministic stat output.</p>

        <div className="form-grid">
          <label>
            Name
            <input value={characterName} onChange={(e) => setCharacterName(e.target.value)} />
          </label>
          <label>
            Race
            <select value={selectedRace} onChange={(e) => setSelectedRace(e.target.value)}>
              {races.map((race) => (
                <option key={race.name} value={race.name}>
                  {race.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Class
            <input value={className} onChange={(e) => setClassName(e.target.value)} />
          </label>
          <label>
            Level
            <input
              type="number"
              min={1}
              max={20}
              value={classLevel}
              onChange={(e) => setClassLevel(Math.max(1, Math.min(20, Number.parseInt(e.target.value || "1", 10))))}
            />
          </label>
        </div>

        <div className="abilities">
          {(["str", "dex", "con", "int", "wis", "cha"] as const).map((key) => (
            <label key={key}>
              {key.toUpperCase()}
              <input
                type="number"
                min={1}
                value={abilityScores[key]}
                onChange={(e) => updateAbility(key, e.target.value)}
              />
            </label>
          ))}
        </div>

        <label className="full-width">
          Feats (comma separated)
          <input value={featInput} onChange={(e) => setFeatInput(e.target.value)} />
        </label>

        <button className="derive-btn" onClick={deriveCharacter} disabled={deriveLoading}>
          {deriveLoading ? "Deriving..." : "Derive Stats"}
        </button>

        {deriveError ? <p className="error">{deriveError}</p> : null}

        {derivedStats ? (
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
        ) : null}
      </section>
    </main>
  );
}
