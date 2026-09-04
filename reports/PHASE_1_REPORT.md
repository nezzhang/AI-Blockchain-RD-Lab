# Phase 1 Completion Report — Discovery

**Date:** 2026-09-04
**Status:** ✅ COMPLETE — discovery loop implemented, tested, demonstrated

## PHASE 1 STATUS

### Implemented

| Component | Location | Notes |
|-----------|----------|-------|
| Agent package restructure | `agents/base.py`, `agents/providers.py` | abstractions split from providers; public API unchanged |
| OpenAI-compatible provider | `providers.OpenAICompatProvider` | stdlib-only HTTP client, tier-based model routing (§31), retries + exponential backoff, 4xx fast-fail; registered as `openai` |
| Local provider | `providers.LocalLLMProvider` | local OpenAI-compatible servers (Ollama/vLLM/LM Studio/llama.cpp) |
| Provider configuration | `config/lab.yaml` `providers:` section | base URLs, models, tier_models, key env names — keys NEVER in config (§30) |
| Research configuration | `load_research()` + research.yaml | novelty classes, 20 §24 domains, discovery + dedup settings |
| Discovery schemas | `discovery/__init__.py` | `IdeaDraft` (raw LLM), `NormalizedIdea` (canonical), `IdeaBatch`, `DuplicateVerdict`, `DiscoveryRunSummary` |
| Discovery Agent | `discovery/agent.py` | §9 mission encoded in system prompt: mechanisms not tokens, forbidden novelty language, combinatorics with economic compatibility (§18) |
| Normalizer | `discovery/normalize.py` | deterministic: camelCase split, stopwords, keyword tokens, name keys, whitespace collapse |
| Deduplicator | `discovery/normalize.py` | deterministic: exact name-key collision + max(name-shingle Jaccard, keyword Jaccard) vs thresholds (0.95 exact / 0.60 near) |
| Discovery service | `discovery/service.py` | generate → normalize → dedup → store; per-batch failure isolation (§35); JSON evidence artifact in `ideas/active/` |
| Experiment #001 seed | `seeds.py` + `lab seed` | Population-Linked Supply (§25) enters as an ORDINARY candidate — hypothesis, not favorite (§24) |
| CLI | `discover`, `seed` | `--mock-fixtures` runs the full loop offline; real providers via config |
| Offline fixtures | `testing/fixtures_ideas.py` | 16 ideas across 20 domains incl. exact-dup and near-dup pairs |

### Evidence: End-to-End Run (offline fixtures)

```
$ lab seed
  seeded cand-f62dbd41e7be — Population-Linked Supply

$ lab discover --count 20 --mock-fixtures
  generated          16
  normalized         16
  duplicates removed  1   (exact name-key: "Demographic Reserve Rule")
  stored             15
  failed batches      1   (mock queue exhausted → graceful §35 stop)
```

- The exact duplicate ("Demographic Reserve Rule" twice) was caught by the
  name-key gate: 1 stored, 1 removed.
- The near duplicate ("Demographic **Dependency** Reserve Rule") measured
  **similarity 0.810** — above the 0.60 near threshold, below the 0.95 exact
  threshold — so both variants remain for human review, by design.
- The Population seed (Experiment #001) competes in the same dedup funnel as
  every other idea: a later fixture idea about population supply was
  correctly deduplicated against it in tests.

### Tests

```
91 passed in 0.53s
```

New coverage (23 new tests): IdeaDraft validation, normalizer (keywords,
name keys, whitespace, to_candidate), deduplicator (exact collision,
identical text, different ideas, near-duplicate signal, empty corpus),
Jaccard math, DiscoveryAgent (structured output via mock, prompt content,
forbidden novelty language in system prompt), DiscoveryService (end-to-end
store+dedup, LLM failure isolation, seed competes fairly), Experiment #001
seed shape, provider registry (openai/local).

### Lint

```
ruff check src tests → All checks passed!
```

### Type checking

```
mypy → Success: no issues found in 25 source files
```

### Deliberate Non-Goals (per §38)

- No prior-art research (Phase 2) — novelty classes remain E (insufficient evidence)
- No scoring of discovered candidates — needs research dimensions first
- No web search tooling for the discovery agent — fixed corpus + LLM knowledge
- No DuckDB analytics

### Known Limitations

1. Token-overlap dedup catches lexical duplicates; **semantic** duplicates
   ("Labor-Backed Escrow" vs "Invoice Financing Pool") need embeddings —
   deferred until a provider supports them cheaply (§31).
2. Mock provider fixtures are hand-written; real discovery quality depends
   entirely on the configured LLM (§2: code only tests, never proposes).
3. Near-duplicates (0.60–0.95) are stored, not quarantined — a
   `similarity` column for triage views arrives with Phase 6 ranking.
4. One discovery artifact per run overwrites nothing but accumulates in
   `ideas/active/` — pruning policy comes with Phase 8 (public research).

### Next phase

**PHASE 2 — RESEARCH**: Prior-Art Agent (queries, sources, dates, findings,
similar mechanisms per §12; FACT/INFERENCE/HYPOTHESIS labeling per §29),
Economist Agent (§9), Market Agent (§9), research source storage, and the
100→20 candidate filter.
