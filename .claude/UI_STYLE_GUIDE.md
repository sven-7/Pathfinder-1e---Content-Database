# UI_STYLE_GUIDE — Modern PWA + Classic RPG Sheet

## Design North Star
- **Modern app shell** (Apple-like): clean, minimal, responsive, touch-first.
- **Classic sheet**: parchment / RPG framing is okay *inside* sheet mode.

## Layout Rules
- Avoid dense walls of text: prefer cards, sections, and collapsible panels.
- Use consistent spacing scale (e.g., 4/8/12/16/24).
- Touch targets: >= 44px height for primary controls.
- Tables: sticky headers where useful (skills, feats, spells).
- Navigation: “Home / Characters / Campaign / DM / Settings”.

## Typography
- App shell: modern readable font stack (system).
- Sheet mode can use thematic fonts, but must remain readable on tablet.

## Component Guidelines
- “Calculated final numbers” front-and-center; breakdowns in tooltips/drawers.
- Two sheet modes:
  1) Classic sheet (print-first)
  2) Modular panels (play-first, rearrangeable)

## PWA UX
- Offline indicator + last sync timestamp (when multi-user arrives).
- Fast load: avoid huge JS bundles; cache static assets.