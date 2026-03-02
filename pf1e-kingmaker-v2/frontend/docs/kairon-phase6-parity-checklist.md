# Phase 6 Kairon UI Parity Checklist

Reference source: `example_content/kairon_v4_6.html` and `pf1e-kingmaker-v2/prompts/pack_g_kairon_parity.md`.

| Feature | Kairon Reference | Status | Notes |
| --- | --- | --- | --- |
| Per-character persisted sheet session state | `STATE_KEY`, `saveState()/loadState()` | PASS | Added character-scoped sheet state in browser storage (`pf1e.v2.frontend.sheet-state`) for conditions, resources, spell tracking, and quick combat data. |
| Resource trackers (HP variants + inspiration + consumables) | HP calculator + inspiration dots + consumable-style trackers | PASS | Added `HP current/temp/nonlethal`, `inspiration current/max`, and consumable counters with inline increment/decrement controls. |
| Condition toggles with deterministic stat deltas | `CONDITIONS`, `COND_SKILL_FX`, recalc path | PASS | Added deterministic in-sheet deltas for AC/saves/init/CMB/CMD/attack/skills plus derive-linked condition indicators. |
| Re-derive on derive-linked condition changes | derive-triggered recalculation workflow | PASS | Toggling derive-linked conditions triggers `/api/v2/rules/derive` + `/api/v2/characters/validate` refresh through existing API V2 flow. |
| Spell/extract tracking: prepared/known/used | formula/extract state dots and slot tracking | PASS | Added per-level counters (`known/prepared/used`) with quick `+/-` controls and persistent values per character. |
| Rest-type reset behavior for spell/extract usage | reset/session behavior | PASS | Added `Short Rest` (partial `used` recovery) and `Full Rest` (reset `used`, refill prepared to known, reset key resources). |
| Quick combat panel parity intent | combat callouts + roll shortcuts | PASS | Added initiative roll helper, attack preset selector, damage notes, condition summary, and key save/skill shortcuts. |
| Tablet-first responsive behavior | compact/layout behavior in reference sheet usage | PASS | Updated layout breakpoints so sheet panels stack cleanly on tablet widths and stay usable at `1024x1366`. |
| Playwright parity smoke coverage | flow-level validation | PASS | Expanded smoke flow to validate condition delta visibility, resource decrement/persistence, and reopen/reload state retention. |
