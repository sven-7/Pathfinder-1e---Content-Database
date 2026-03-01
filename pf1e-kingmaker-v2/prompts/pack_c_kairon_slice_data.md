# Pack C: Kairon Slice Data

## Objective
Load only Kairon-critical entities as first vertical slice.

## Scope
- Class: Investigator + progression.
- Race: Tiefling + racial traits.
- Feats: Weapon Finesse, Weapon Focus, Rapid Shot (+ Kairon feats).
- Traits: Reactionary and selected campaign traits.
- Spells/Extracts relevant to Kairon.
- Core equipment rows used by Kairon sheet.
- Data source order: AON first, d20 fallback only when needed.
- Text requirement: include short summaries and full detail bodies.

## Required Outputs
- Insert counts by table.
- Missing-entity report.
- Fixture export JSON used for regression tests.
- Golden fixture comparison output against `kairon_v4_6.html` + `Kairon - Level 9.pdf`.
