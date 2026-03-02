# Changelog

## 2026-03-02 - Phase 7 DM Foundation Slice

- Merged integration baseline from `codex/frontend-character-workflow` into `codex/dm-kingmaker-foundations`.
- Added campaign domain V1 backend contracts for:
  - `Campaign`
  - `Party`
  - `PartyMember`
  - `Session`
  - `Encounter`
- Added V2 API scaffolding endpoints:
  - `/api/v2/campaigns/*`
  - `/api/v2/parties/*`
  - `/api/v2/sessions/*`
- Added rule-override storage and deterministic merge resolution with fixed precedence:
  - `global -> campaign -> character`
- Added minimal DM frontend shell with campaign create/list/open and party roster read panel.
- Added backend API/contract tests and deterministic override precedence tests.

### Test Evidence

- `python3 -m pytest -q tests/test_api_v2_contracts_static.py` (run in `pf1e-kingmaker-v2/backend`)  
  Result: `5 passed in 0.00s`
- `python3 -m pytest -q tests/test_campaign_api_v2.py tests/test_api_v2.py` (run in `pf1e-kingmaker-v2/backend`)  
  Result: `2 skipped in 0.06s` (runtime deps missing in current environment)
- `python3 -m pytest -q tests/test_rule_override_precedence.py` (run in `pf1e-kingmaker-v2/backend`)  
  Result: `1 skipped in 0.00s` (runtime deps missing in current environment)
- `npm run build` (run in `pf1e-kingmaker-v2/frontend`)  
  Result: Vite production build succeeded.

### Environment Note

- `pip install -r requirements.txt` failed in this sandbox due blocked external package index access, so FastAPI/Pydantic runtime tests could not be executed here.
