# RAGAS eval baseline — 2026-05-19

Bootstrap of `backend/tests/eval/golden_dataset.json` from live AWS Bedrock Knowledge Base (OpenSearch-backed index, `RAG_ENGINE=langgraph`).

## Dataset

| Item | Value |
|------|--------|
| Seed questions | 12 (`seed_questions.json`) |
| Promoted rows | 10 |
| Dropped | SpeedGrader audio feedback; Gradebook excuse (model out-of-scope despite retrieval) |

## Bootstrap command

```bash
./venv/bin/python scripts/bootstrap_golden_dataset.py
```

## RAGAS score comparison

| Metric | Threshold | Baseline (no Phase 5) | Phase 5 (initial) | **Phase 5 tuned** | Gate |
|--------|-----------|------------------------|-------------------|-------------------|------|
| faithfulness | ≥ 0.85 | 0.662 | 0.712 | **0.754** | fail |
| answer_relevancy | ≥ 0.80 | 0.675 | 0.801 | **0.789** | fail |
| context_recall | ≥ 0.75 | 0.600 | 0.750 | **0.800** | **pass** |
| context_precision | ≥ 0.70 | 0.600 | 0.505 | **0.504** | fail |

**Phase 5 tuned run** (~3m 12s): `./scripts/run_eval_phase5.sh` — keyword rerank, `MULTI_QUERY_COUNT=2`, reciprocal-rank fusion, prefilter (`RERANK_PREFILTER_MAX=10`, no keyword-overlap drop).

**Tuning notes:** FlashRank + single extra query regressed relevancy/recall vs keyword + two queries. `RERANK_TOP_N=2` raised precision to ~0.62 but hurt recall; keep `RERANK_TOP_N=3` for the balanced profile.

## Commands

```bash
# Default eval (Phase 5 flags off)
tox -e eval

# Phase 5 retrieval stack (tuned)
./scripts/run_eval_phase5.sh

# Strict gates
RAGAS_QUALITY_GATE=1 ./scripts/run_eval_phase5.sh
```

## Related

- [EVALUATION.md](./EVALUATION.md)
- [roadmap/PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md)
- `scripts/bootstrap_golden_dataset.py`
