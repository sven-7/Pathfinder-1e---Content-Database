# AI_WORKFLOW — How to Work in This Repo

## Default Work Pattern (Do This Every Time)
1. Identify the smallest vertical slice that delivers user value.
2. Prefer extending existing patterns over introducing new frameworks.
3. Make UI changes with:
   - keyboard + mouse usability
   - touch targets (PWA/tablet)
   - print styles for sheet/panels

## Coding Standards
- Keep DB access behind a small data layer; avoid SQL scattered across routes.
- Don’t “parse PF1e text into logic” unless explicitly in scope; store raw prerequisites as text when needed.
- When rules change: add or extend pytest coverage and ensure known formula references remain correct.

## Regression Checklist

See `NON_REGRESSION_CHECKLIST.md` for full automated + manual checks.

Quick sanity: `python3 -m pytest tests/ -v` (71 tests must pass), then spot-check:
- Character creation works end-to-end
- Save character → open sheet → derived stats correct
- Level up → spells/talents/budgets behave
- Classic sheet prints cleanly