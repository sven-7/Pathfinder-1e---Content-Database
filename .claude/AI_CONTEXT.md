# AI_CONTEXT — Pathfinder 1e Campaign Manager (Always-On Context)

> This repository is a **single cohesive Pathfinder 1E campaign manager app**, not a collection of disconnected scripts/tools.
> Every change should support an end-to-end, table-ready experience for both Players and GMs.

## Read Me First (Non-Negotiable)
1. **Read `README.md` first** and treat it as the authoritative vision + roadmap + “do not regress” list.
2. **Reference data + examples live in `/example_content`** (gitignored). Assume it exists locally during development and use it as ground truth for UX targets and parity checks.
3. The app must work as:
   - **Local dev web app**
   - **Progressive Web App (PWA)** usable on tablet at the table (offline-friendly, installable)
4. Maintain the project design principles:
   - situation-based UX, calculated final numbers, print-quality views, cohesive visual language

---

## Product Goals (User-Facing)
### Player Goals
- Create Characters (wizard)
- Manage Characters (library + edit/update)
- Level Up Characters (level-up wizard)
- Character Sheet:
  - Classic “parchment / RPG sheet” view (printable)
  - Modular quick-panels “cheat sheet” view for turns at the table

### GM Goals
- DM Party View of PCs
- DM Party View of NPCs
- Campaign Layer: roster, shared notes, shared loot, (later) encounter tracker

These map to the existing roadmap phases (Creator, Sheet, Cheat Sheet, DM View/Campaign, Encounter Tracker).

---

## UI/UX Direction (Important)
### Web-App / PWA (NOT just “a website”)
- Must be **installable** and **offline-friendly** for tablet use at the table.
- Design for:
  - iPad Safari / Chrome Android tablet
  - Large touch targets, responsive layout, minimal scrolling during combat
  - Fast navigation between “turn-time” panels

### “Apple-like” Modern UI + “Classic RPG Sheet” Aesthetic
We want a modern, clean, high-contrast UI with:
- crisp typography, thoughtful spacing, soft depth/shadows, and precise alignment
- a “system UI” feel in navigation/settings
- BUT the character sheet can preserve “classic RPG sheet” vibes (parchment, borders, iconography).

The classic sheet should be able to match the feel of the Kairon reference HTML (spell dots, resources, buffs/conditions, etc.).

### Two primary presentation modes
1. **Classic Sheet Mode (Print-first)**
2. **Modular Panel Mode (Play-first)** — rearrangeable panels, turn-time focus (combat/resources/skills/abilities)

---

## Data + Rules Engine Expectations
### Database
- SQLite-first is acceptable, but design supports migration/operation with PostgreSQL.
- Preserve HTML descriptions where source data includes HTML.
- Keep normalized core relationships; allow denormalized prerequisite text where the data is messy.

### Rules Engine
- Rules math must remain correct and regression-tested.
- Follow established formulas and known gaps from `bugs-and-roadmap.md` (e.g., trait bonus application).

---

## Engineering Constraints
- Primary stack: **Python + FastAPI + Web UI** (already working).
- Target: PWA-capable front-end (service worker + manifest + offline cache strategy).
- Prefer incremental refactors over rewrites.
- Keep the app usable offline once installed (at minimum: character library + sheet + rules math).

---

## Output Expectations for AI Coding Assistance
When implementing changes:
1. Propose the minimal set of files to touch.
2. Implement the change.
3. Add/extend tests when logic changes (especially rules).
4. Update the relevant docs:
   - `bugs-and-roadmap.md` (if a bug/phase status changes)
   - `README.md` only if roadmap/vision materially changes
5. Include a short “verification checklist” (how to confirm manually).

---

## Golden References (Local)
- `/example_content/kairon_v4_6.html` — target UX parity for the classic sheet
- `/example_content/*` — additional targets, screenshots, PDFs, and campaign examples (gitignored)