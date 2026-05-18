# Evaluation strategy (RAGAS + LangSmith)

How to judge additions to this project — for portfolio work, LangGraph migration, and retrieval upgrades.

---

## Two tools, two jobs

| | **RAGAS** | **LangSmith** |
|--|-----------|----------------|
| **What** | Open-source RAG **metric library** | **Platform** for traces, datasets, experiments |
| **Question answered** | "Did quality improve or regress?" | "Why was this request slow/wrong?" |
| **In this repo** | `backend/tests/eval/test_rag_quality.py`, `golden_dataset.json` | `simple_tracer.py`, `LANGCHAIN_TRACING_V2` |
| **CI gate** | Yes — `RAGAS_QUALITY_GATE=1` on release/nightly | Optional — traces for debug |
| **Same thing?** | **No** — complementary |

LangSmith can run evaluators (including RAG-like judges), but **do not treat LangSmith scores as RAGAS** without calibrating on the same dataset.

---

## RAGAS metrics (defaults)

| Metric | Default min | Interpretation |
|--------|-------------|----------------|
| **faithfulness** | 0.85 | Answer grounded in retrieved context |
| **answer_relevancy** | 0.80 | Answer addresses the question |
| **context_recall** | 0.75 | Retrieval covers ground truth |
| **context_precision** | 0.70 | Retrieved chunks are on-topic |

Env overrides: `RAGAS_FAITHFULNESS_MIN`, `RAGAS_ANSWER_RELEVANCY_MIN`, etc.

### Run locally

```bash
pytest backend/tests/eval/test_rag_quality.py -v
# from repo root: PYTHONPATH=. pytest backend/tests/eval/ -v
# Note: tox.ini has no [testenv:eval] yet — use pytest or add tox env later
```

Requires judge LLM: `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, or `RAGAS_LLM_PROVIDER`.

---

## When to run what

| Event | RAGAS | LangSmith |
|-------|-------|-----------|
| Every PR | Optional — unit tests with mocked RAG | Dev only |
| Pre-release / portfolio milestone | Full golden set via `pytest backend/tests/eval/`; compare to baseline | Trace screenshot for README |
| LangGraph parity (Phase 4) | **Required** — chain vs `RAG_ENGINE=langgraph`, ±0.02 | Per-node spans |
| Retrieval change (Phase 5) | Primary metric + faithfulness guardrail | Compare runs |
| Nightly staging | Full gate with secrets | SLO debugging |

---

## Scorecard (per feature)

| Field | Value |
|-------|--------|
| **Change** | e.g. multi-query retrieval node |
| **Roadmap phase** | Portfolio Phase 5 |
| **Primary metric** | context_recall |
| **Guardrails** | faithfulness ≥ 0.85; p95 latency < X ms |
| **Baseline** | commit / scores CSV |
| **Result** | +0.04 recall; faithfulness 0.86 |
| **Ship** | yes / flag-only / no |

### Ship rules

- **LangGraph parity:** ship if RAGAS within ε of chain and tests green.
- **Retrieval / prompts:** ship if primary metric improves and guardrails hold.
- **Agentic (Phase 6):** flag-only until staging week is stable.

---

## LangGraph-specific evaluation

1. Baseline RAGAS on `RAG_ENGINE=chain` (or current default).
2. Run same golden set on `RAG_ENGINE=langgraph`.
3. Compare all four metrics; investigate faithfulness regressions first.
4. Use LangSmith to see whether regressions are condense vs retrieve vs generate.

---

## Growing the golden set

1. Start with domain Q&A in `golden_dataset.json`.
2. Add failures from manual testing and (anonymized) bad traces.
3. Tag items: `"tags": ["ambiguous", "multi-hop"]` for targeted runs.

---

## Related

- [roadmap/PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md)
- [roadmap/LANGGRAPH.md](./roadmap/LANGGRAPH.md)
