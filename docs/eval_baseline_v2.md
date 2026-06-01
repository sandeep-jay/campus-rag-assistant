# RAGAS eval baseline — v2 retrieval stack

**Captured:** 2026-05-19 · **Scope:** v2 RAG platform (LangGraph KB path, Phase 5 retrieval tuning) — **before** the v3 helpdesk agent shipped.

This document records regression scores for the **v2 retrieval stack** on the 10-row golden set. It is the primary reference when comparing Phase 5 tuning profiles (`./scripts/run_eval_phase5.sh`) and Azure-vs-AWS judge sweeps. For release-by-release context see [release-notes/](./release-notes/index.md); for gate policy see [ADR-004](./adr/ADR-004-eval-gating-policy.md).

Bootstrap of `backend/tests/eval/golden_dataset.json` from live **AWS Bedrock Knowledge Base** (OpenSearch-backed index, `RAG_ENGINE=langgraph`). Golden `ground_truth` and `contexts` reflect **AWS-generation** at bootstrap time.

## Dataset

| Item | Value |
|------|--------|
| Seed questions | 12 (`seed_questions.json`) |
| Promoted rows | 10 |
| Dropped | SpeedGrader audio feedback; Gradebook excuse (model out-of-scope despite retrieval) |

## Bootstrap command

```bash
./venv/bin/python scripts/bootstrap_golden_dataset.py
./venv/bin/python scripts/promote_golden_draft.py
```

---

## RAGAS score comparison (AWS Bedrock — original baseline)

Historical runs on the same 10-row golden set with **AWS LLM** and Phase 5 LangGraph retrieval. These values are **retained** as the primary regression reference.

| Metric | Threshold | Baseline (no Phase 5) | Phase 5 (initial) | **Phase 5 tuned** | Gate |
|--------|-----------|------------------------|-------------------|-------------------|------|
| faithfulness | ≥ 0.85 | **0.662** | **0.712** | **0.754** | fail |
| answer_relevancy | ≥ 0.80 | **0.675** | **0.801** | **0.789** | fail |
| context_recall | ≥ 0.75 | **0.600** | **0.750** | **0.800** | **pass** |
| context_precision | ≥ 0.70 | **0.600** | **0.505** | **0.504** | fail |

**Phase 5 tuned (AWS)** (~3m 12s): keyword rerank, `MULTI_QUERY_COUNT=2`, RRF, `RERANK_TOP_N=3`, `RERANK_PREFILTER_MAX=10`, `RERANK_MIN_KEYWORD_OVERLAP=0` (historical `./scripts/run_eval_phase5.sh` profile).

**AWS tuning notes (retained):** FlashRank + single extra query regressed relevancy/recall vs keyword + two queries. `RERANK_TOP_N=2` raised precision to ~0.62 in spot checks but hurt recall; the table above uses `RERANK_TOP_N=3` as the balanced AWS profile.

---

## RAGAS runs — Azure OpenAI LLM + judge (same golden set)

Follow-up sweeps with `LLM_PROVIDER=azure`, `RETRIEVER_PROVIDER=aws`, same `golden_dataset.json` (AWS-bootstrap references). Judge: Azure GPT-4o via `LLM_PROVIDER` / `RAGAS_LLM_PROVIDER`. **Scores vary run-to-run** (~±0.05–0.15); point estimates from local runs 2026-05-19.

### Summary vs default gates

| Profile | faithfulness | answer_relevancy | context_recall | context_precision | Notes |
|---------|-------------:|-----------------:|---------------:|------------------:|-------|
| **Azure + chain** (best single run) | **0.838** | **0.980** | **0.833** | 0.500 | Pre–conftest-fix; `RETRIEVER_NUMBER_OF_RESULTS=4` |
| Azure + chain (`n=2`) | 0.642 | 0.886 | 0.600 | 0.508 | |
| Azure + chain (`n=3`) | 0.639 | 0.886 | 0.600 | 0.558 | |
| Azure + chain (`n=4`, repeat) | 0.617 | 0.885 | 0.600 | 0.458 | Judge variance |
| LangGraph P5 (`TOP_N=3`, `MQ=2`) | 0.768 | failed† | 0.600 | 0.558 | †per-metric test |
| LangGraph precision-balanced (`TOP_N=2`, `MQ=3`) | 0.651 | 0.885 | 0.600 | 0.542 | Current `run_eval_phase5.sh` |
| LangGraph `TOP_N=2`, `MQ=2`, overlap≥1 | 0.643 | 0.891 | 0.600 | 0.492 | |
| LangGraph no multi-query (`TOP_N=2`) | 0.638 | 0.886 | 0.600 | **0.583** | Best Azure precision |
| LangGraph FlashRank `TOP_N=2` | 0.684 | 0.886 | 0.550 | 0.492 | |
| LangGraph tight prefilter (overlap≥2) | 0.626 | 0.867 | 0.600 | 0.398 | |

**Gates:** faithfulness ≥ 0.85, answer_relevancy ≥ 0.80, context_recall ≥ 0.75, context_precision ≥ 0.70. **No Azure profile passed all four.**

### Recommended retrieval profile (precision-balanced)

| Setting | Value |
|---------|--------|
| `RAG_ENGINE` | `langgraph` |
| `RERANK_ENABLED` | `true` |
| `RERANK_BACKEND` | `keyword` |
| `RERANK_TOP_N` | `2` |
| `RERANK_CANDIDATE_K` | `15` |
| `RERANK_PREFILTER_MAX` | `10` |
| `RERANK_MIN_KEYWORD_OVERLAP` | `1` |
| `MULTI_QUERY_ENABLED` | `true` |
| `MULTI_QUERY_COUNT` | `3` |

---

## Findings — why these scores

### 1. Golden reference vs live stack

`ground_truth` was bootstrapped with **AWS Bedrock** answers. RAGAS **faithfulness** and **context_recall** compare live output to that reference. **Azure generation + Azure judge** shifts wording and chunk emphasis vs AWS references — scores move even when answers are acceptable. **Mitigation:** re-bootstrap with `LLM_PROVIDER=azure`.

### 2. `context_precision` is the bottleneck

RAGAS scores **each retrieved chunk** against the reference. Multi-query + RRF **improve recall** by merging more candidates; rerank trims to top-N but **irrelevant fused chunks** still depress precision (~**0.50–0.58** across AWS/Azure) while AWS Phase 5 tuned reaches **context_recall 0.80**.

- **`RERANK_TOP_N=2`**: modest precision gain, often lower recall/faithfulness.
- **Disable multi-query**: precision up to ~**0.583**, recall ~**0.60**.
- **Stricter keyword prefilter**: precision **drops** (~0.40) — over-filters hard queries.

### 3. Chain vs LangGraph in eval

Previously `backend/tests/conftest.py` forced `RAG_ENGINE=chain`, so `tox -e eval` skipped Phase 5 nodes despite `run_eval_phase5.sh`. The **best Azure relevancy/recall** run used **chain** + KB only — not comparable to AWS Phase 5 tuned. **Fix (2026-05-19):** when `RAGAS_EVAL=1`, conftest preserves `RAG_ENGINE` from env.

### 4. Judge variance

`answer_relevancy` can fail per-metric while `test_full_suite_report` shows high means (~0.88–0.98). Repeated identical configs varied (e.g. faithfulness **0.838** vs **0.617**). Use same session when A/B tuning.

### 5. Levers to move all metrics above gates

| Lever | Effect |
|-------|--------|
| Re-bootstrap golden with eval LLM | Align faithfulness / recall |
| Ingestion / chunking / KB hygiene | Precision + recall upstream |
| FlashRank A/B | Precision vs latency |
| Metadata filters | Precision on subset |
| Gate policy | Track without blocking CI — [EVALUATION.md](./EVALUATION.md) |

Only **context_recall** reliably passes under AWS Phase 5 tuned (**0.800**). Sub-threshold scores are **documented baselines**, not demo blockers.

---

## Commands

```bash
tox -e eval
./scripts/run_eval_phase5.sh
tox -e eval -- python -m pytest \
  backend/tests/eval/test_rag_quality.py::TestRAGQuality::test_full_suite_report \
  -v -s -m slow --log-cli-level=WARNING
RAGAS_QUALITY_GATE=1 ./scripts/run_eval_phase5.sh
```

**Eval hygiene:** `RAGAS_DO_NOT_TRACK=true` in tox; quieter vendor loggers in `backend/tests/eval/conftest.py`.

---

## Related

- [EVALUATION.md](./EVALUATION.md)
- [roadmap/PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md)
- `scripts/bootstrap_golden_dataset.py`, `scripts/promote_golden_draft.py`
