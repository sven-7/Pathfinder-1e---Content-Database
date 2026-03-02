# API V2 (Character Domain)

This backend exposes OpenAPI for V2 at:

- `GET /openapi.json`
- `GET /docs` (Swagger UI)

## Versioned Endpoints

- `GET /api/v2/content/feats`
- `GET /api/v2/content/races`
- `GET /api/v2/content/policy-summary`
- `POST /api/v2/characters/validate`
- `POST /api/v2/rules/derive`
- `GET/POST /api/v2/campaigns`
- `GET /api/v2/campaigns/{campaign_id}`
- `GET/POST /api/v2/parties`
- `GET /api/v2/parties/{party_id}`
- `GET/POST /api/v2/sessions`
- `GET /api/v2/sessions/{session_id}`
- `GET/POST /api/v2/campaigns/rule-overrides/global`
- `GET/POST /api/v2/campaigns/{campaign_id}/rule-overrides`
- `GET /api/v2/campaigns/{campaign_id}/rule-overrides/resolve`

## Example curl Calls

```bash
curl -sS http://localhost:8000/openapi.json | jq '.info, .paths | keys'
```

```bash
curl -sS "http://localhost:8000/api/v2/content/feats?include_deferred=true" | jq '.[0:5]'
```

```bash
curl -sS -X POST "http://localhost:8000/api/v2/characters/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Kairon",
    "race":"Tiefling",
    "alignment":"Lawful Neutral",
    "ability_scores":{"str":12,"dex":18,"con":12,"int":17,"wis":18,"cha":14},
    "class_levels":[{"class_name":"Investigator","level":9}],
    "feats":[
      {"name":"Weapon Finesse","level_gained":1,"method":"general"},
      {"name":"Weapon Focus","level_gained":3,"method":"general"},
      {"name":"Rapid Shot","level_gained":5,"method":"general"}
    ],
    "traits":[
      {"name":"Reactionary","category":"Combat","effects":[{"key":"initiative","delta":2,"bonus_type":"trait","source":"Reactionary"}]}
    ],
    "skills":{"Perception":9},
    "equipment":[
      {"name":"Rapier","kind":"weapon","quantity":1},
      {"name":"Studded Leather","kind":"armor","quantity":1}
    ],
    "conditions":[]
  }' | jq
```

```bash
curl -sS -X POST "http://localhost:8000/api/v2/rules/derive" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Kairon",
    "race":"Tiefling",
    "alignment":"Lawful Neutral",
    "ability_scores":{"str":12,"dex":18,"con":12,"int":17,"wis":18,"cha":14},
    "class_levels":[{"class_name":"Investigator","level":9}],
    "feats":[
      {"name":"Weapon Finesse","level_gained":1,"method":"general"},
      {"name":"Weapon Focus","level_gained":3,"method":"general"},
      {"name":"Rapid Shot","level_gained":5,"method":"general"}
    ],
    "traits":[
      {"name":"Reactionary","category":"Combat","effects":[{"key":"initiative","delta":2,"bonus_type":"trait","source":"Reactionary"}]}
    ],
    "skills":{"Perception":9},
    "equipment":[
      {"name":"Rapier","kind":"weapon","quantity":1},
      {"name":"Studded Leather","kind":"armor","quantity":1}
    ],
    "conditions":[]
  }' | jq '.derived | {bab,fort,ref,will,ac_total,attack_lines,feat_prereq_results,breakdown}'
```

```bash
curl -sS -X POST "http://localhost:8000/api/v2/campaigns" \
  -H "Content-Type: application/json" \
  -d '{"name":"Stolen Lands","owner_id":"owner-stephen","status":"active","gm_id":"gm-stephen"}' | jq
```

```bash
curl -sS -X POST "http://localhost:8000/api/v2/parties" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id":"<campaign_id>","name":"Heroes of Restov","owner_id":"owner-stephen","members":[{"display_name":"Kairon","role":"pc"}]}' | jq
```

```bash
curl -sS -X POST "http://localhost:8000/api/v2/campaigns/rule-overrides/global" \
  -H "Content-Type: application/json" \
  -d '{"key":"ac_total","operation":"add","value":1,"source":"global-house-rule"}' | jq
curl -sS -X POST "http://localhost:8000/api/v2/campaigns/<campaign_id>/rule-overrides" \
  -H "Content-Type: application/json" \
  -d '{"key":"ac_total","operation":"set","value":16,"source":"campaign-setting"}' | jq
curl -sS "http://localhost:8000/api/v2/campaigns/<campaign_id>/rule-overrides/resolve?character_id=char-kairon" | jq
```
