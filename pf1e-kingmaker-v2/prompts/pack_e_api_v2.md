# Pack E: API V2

## Objective
Expose stable, versioned endpoints backed by V2 contracts.

## Endpoints
- `GET /api/v2/content/*`
- `POST /api/v2/characters/*`
- `POST /api/v2/rules/derive`

## Required Behavior
- No direct SQL in route handlers; repository/service layer only.
- Include source provenance in content responses.
- Include derivation breakdown and feat-prereq legality output.
- Include explicit fields for short and long text on feats/spells.
- Keep single-user runtime simple, but keep contracts forward-compatible with campaign/user ownership fields.

## Required Outputs
- OpenAPI docs.
- Contract tests.
- Example curl commands.
