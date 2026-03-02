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

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [includeDeferred, setIncludeDeferred] = useState<boolean>(false);
  const [feats, setFeats] = useState<FeatRow[]>([]);
  const [races, setRaces] = useState<RaceRow[]>([]);
  const [policy, setPolicy] = useState<PolicySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

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
              <p className="muted">
                Top deferred reason:{" "}
                {Object.entries(policy.reason_counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "none"}
              </p>
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
    </main>
  );
}
