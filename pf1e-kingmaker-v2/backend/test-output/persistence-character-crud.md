# Persistence Character CRUD Test Output

## Local Pytest

Command:

```bash
PYTHONPATH='../../.venv/lib/python3.14/site-packages' python3 -m pytest -q
```

Result:

```text
34 passed, 2 warnings in 0.20s
```

## Docker Integration

Build/start API + DB:

```bash
docker compose up -d --build db api
```

Health (inside API container):

```text
{'ok': True, 'env': 'dev', 'version': '0.1.0'}
```

Created persisted entities (inside API container):

```json
{
  "campaign_id": "f50f823a-ee41-43b3-9307-42bae72f38fb",
  "party_id": "cdcc556a-8379-432e-846e-8215dc348e3b",
  "session_id": "2b0e5bdd-a007-40e5-a5ee-00822ae935f6",
  "encounter_id": "8005ff2b-68b5-4731-b8cc-6d0bfba48240",
  "character_id": "066253c3-552b-4535-a3ae-5f5293d79915"
}
```

After `docker compose restart api`, persisted reads + validate/derive:

```json
{
  "campaign_after_restart": "f50f823a-ee41-43b3-9307-42bae72f38fb",
  "party_after_restart": "cdcc556a-8379-432e-846e-8215dc348e3b",
  "encounter_after_restart": "8005ff2b-68b5-4731-b8cc-6d0bfba48240",
  "character_after_restart": "066253c3-552b-4535-a3ae-5f5293d79915",
  "validate_ok": true,
  "derive_total_level": 9
}
```
