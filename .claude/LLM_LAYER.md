# LLM_LAYER.md

Defines AI integration discipline. **Deferred to Phase 17.**

---

# Status

Phase 17 (deferred). Do not implement AI features until Phases 12-16 are complete.
The rules engine, campaign layer, equipment system, and combat tracker must be
mature before adding an AI interface on top.

---

# Architecture Decision: RAG-Only, No Fine-Tuning

PF1e rules are a retrieval problem, not a knowledge problem. The content DB
(51MB SQLite, 2,921 spells, 1,807 feats, ~4,300 class features) IS the knowledge base.

Fine-tuning is rejected because:
- Requires thousands of curated Q&A pairs
- Hallucinated rules answers become more confident, not more correct
- Must retrain on every content import
- Retrieval + constraints achieves the same goal without training cost

---

# Model

- Local LLM via Ollama (Mistral 7B or Llama 3 8B recommended)
- Embeddings stored in pgvector (PostgreSQL already in stack)
- All answers must cite retrieved entities
- Retrieval mandatory — no parametric-only answers about rules

---

# Retrieval Pattern

1. Embed user query
2. Retrieve top K rule entities from pgvector (feats, spells, class features, etc.)
3. Provide retrieved text as context
4. Constrained generation — answer must reference retrieved entities

If no relevant entities retrieved:
Return "No rule evidence found."

---

# Endpoints

## /api/ask
"What does Studied Combat do?" -> Retrieve class feature text, summarize.
LLM explains; does not invent.

## /api/suggest
"What feats for a TWF Investigator?" -> Deterministic prereq check filters candidates,
LLM ranks and explains the shortlist.

## /api/validate
"Is this build legal?" -> `check_prerequisites()` for each feat/talent,
LLM formats the pass/fail report with rule citations.

---

# Prohibited Behavior

- No rule invention
- No math computation (BAB, saves, HP, AC — all deterministic in rules_engine)
- No legality decisions (route to rules_engine, LLM explains result)
- No hidden Pathfinder knowledge beyond what's in the content DB

All legality decisions must route to rules_engine.

---

# Prerequisites for Phase 17

These phases build the systems the AI layer interfaces with:

| Phase | What it provides for AI |
|-------|------------------------|
| 13 | Prerequisite enforcement — gives /validate real teeth |
| 12 | Campaign model — gives AI party-aware context |
| 14 | Combat tracker — gives AI tactical context |
| 15 | Full equipment data — completes the retrieval corpus |
| 16 | Party inventory — shared state for AI to reason over |

---

# Quick Proof-of-Concept (Optional, Pre-Phase 17)

If exploring early, the cheapest spike is:
1. `pip install ollama` + pull `mistral:7b`
2. Add a `/api/ask` endpoint using existing SQLite FTS5 `search_index`
3. Pass top 5 FTS results as context to local model
4. Evaluate answer quality before committing to full vector pipeline

This is a weekend spike, not a phase.

---

End
