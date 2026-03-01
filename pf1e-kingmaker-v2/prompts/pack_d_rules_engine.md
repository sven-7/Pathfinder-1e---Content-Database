# Pack D: Rules Engine

## Objective
Implement deterministic derivation and legality checks for Milestone 1 slice.

## Tasks
1. BAB/saves/HP/AC/CMB/CMD/initiative.
2. Feat prerequisite evaluation.
3. Trait/feat stat delta application with source attribution.
4. Golden tests for Kairon L9.
5. Add item/armor/weapon effects to derived stats with explicit stacking behavior.
6. Add rule override layer (table/house rules) with deterministic precedence:
   - base rules
   - source errata patches
   - campaign overrides
   - character overrides

## Required Outputs
- Passing pytest rules suite.
- Structured derivation breakdown payload.
- Override application trace in response breakdown.
