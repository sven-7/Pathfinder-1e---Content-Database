import { useEffect, useState } from "react";

type Health = {
  ok: boolean;
  env: string;
  version: string;
};

export function App() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    const base = import.meta.env.VITE_API_BASE ?? "http://localhost:8100";
    fetch(`${base}/health`)
      .then((r) => r.json())
      .then((json: Health) => setHealth(json))
      .catch(() => setHealth(null));
  }, []);

  return (
    <main className="app-shell">
      <header className="hero">
        <h1>PF1e Kingmaker V2</h1>
        <p>Data-first rebuild with deterministic ingestion and V2 contracts.</p>
      </header>

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
    </main>
  );
}
