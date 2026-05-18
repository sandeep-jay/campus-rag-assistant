# Portfolio phased roadmap

**Last updated:** 2026-05-18  
**Audience:** Independent continuation of the RAG chatbot (portfolio edition).  
**Supersedes for portfolio work:** execution order and priorities here; campus-scale items remain in [PHASED_IMPROVEMENT_ROADMAP.md](./PHASED_IMPROVEMENT_ROADMAP.md).

**Publish and platform wiring are complete** on [`main`](https://github.com/sandeep-jay/campus-rag-assistant). Remaining work: **RAGAS gates**, **LangGraph**, retrieval quality, optional LangGraph streaming/agentic.

---

## Goals

| Goal | How we measure success |
|------|-------------------------|
| **Portfolio-ready demo** | Clone → mock mode → login → chat with sources in <15 min |
| **Credible AI engineering** | Providers, RAGAS harness, LangSmith traces, optional LangGraph |
| **JD alignment** | LangGraph, eval discipline, full-stack Vue — without Phase-5 agent swarms |
| **Clean repo story** | New repo or detached fork; README attribution; LICENSE retained |

---

## Phase map (high level)

```mermaid
flowchart LR
  P0[Phase0_Publish]
  P1[Phase1_CommitAndDemo]
  P2[Phase2_PlatformProviders]
  P3[Phase3_EvalAndObs]
  P4[Phase4_LangGraphParity]
  P5[Phase5_RAGQuality]
  P6[Phase6_AgenticOptional]
  P0 --> P1 --> P2 --> P3 --> P4 --> P5 --> P6
```

| Phase | Focus | Status |
|-------|--------|--------|
| **0–2** | Publish repo, logical PR history, platform + providers + tox | **Done** (PR1–#9 on `main`) |
| **3** | RAGAS golden set; LangSmith; metrics/SLOs sketch | **Next** |
| **4** | LangGraph parity graph (`RAG_ENGINE`); per-node traces | Planned |
| **5** | Retrieval quality nodes (multi-query, rerank, filters) | Planned |
| **6** | Bounded agentic graph; LangGraph SSE | Optional — after RAGAS stable |

Campus production concerns (Redis HA, tenant budgets, Elastic Beanstalk) stay in [PHASED_IMPROVEMENT_ROADMAP.md](./PHASED_IMPROVEMENT_ROADMAP.md) Phases 1–4 org track.

---

## Completed on `main` (phases 0–2)

- **Repo:** [campus-rag-assistant](https://github.com/sandeep-jay/campus-rag-assistant); README attribution under [License](../../README.md#license); Regents `LICENSE` retained.
- **Platform:** request context, Prometheus metrics, rate limits, dev-only routes.
- **RAG:** provider registry wired in `rag.py` (AWS / Azure / mock); RAGAS harness under `backend/tests/eval/`.
- **Clients:** Vue 3 SPA, Streamlit; Alembic migrations; k6 load tests.
- **CI locally:** `tox -e lint,backend,frontend-streamlit,frontend-vue`.

---

## Phase 3 — Evaluation and observability (RAGAS + LangSmith)

**Goal:** Prove quality and debuggability — **not** interchangeable tools.

| Tool | Role |
|------|------|
| **RAGAS** | CI/release **quality gates** on golden dataset (`backend/tests/eval/`) |
| **LangSmith** | **Tracing** per request/node (`LANGCHAIN_TRACING_V2`, `@trace_rag`) |

See [EVALUATION.md](../EVALUATION.md).

### 3a. RAGAS

- Grow `golden_dataset.json` (5–20 real domain Q&A).
- Baseline scores with `tox -e eval` or `pytest backend/tests/eval/`.
- Gate defaults: faithfulness ≥ 0.85, answer_relevancy ≥ 0.80, context_recall ≥ 0.75, context_precision ≥ 0.70 (`RAGAS_QUALITY_GATE=1` on release branches).

### 3b. LangSmith

- Screenshot/trace of one chat turn in README.
- Name runs by `session_id` / `message_id` when wiring request context.

### 3c. Ops sketch

- Document `X-Request-ID`, metrics URL, mock vs live providers in `.env.example`.
- Optional: k6 smoke (login + chat) per [LOAD_TESTING.md](../LOAD_TESTING.md).

**Exit criteria:** Eval runs locally; trace visible; README "Quality" section.

---

## Phase 4 — LangGraph (deterministic parity)

**Goal:** Explicit RAG pipeline for tests, traces, and future nodes — **same** `{ message, metadata }` contract.

**Not in scope:** Multi-agent swarms; unbounded tool loops.

### 4a. Module layout

```
backend/app/services/graph/
  state.py      # question, chat_history, documents, answer, metadata
  nodes.py      # condense, retrieve, generate, format
  graph.py      # StateGraph: linear edges
  runner.py     # run_rag_graph() → process_query shape
```

Each node calls **LangChain** primitives (`llm.invoke`, `retriever.invoke`) via providers.

### 4b. Feature flag

```bash
RAG_ENGINE=chain      # default until RAGAS parity
RAG_ENGINE=langgraph
```

### 4c. Exit criteria

- Unit tests per node + graph runner tests.
- RAGAS within **±0.02** of chain on full golden set.
- LangSmith shows **condense / retrieve / generate** spans.
- Then flip default to `langgraph`; remove chain in follow-up when confident.

Detail: [LANGGRAPH.md](./LANGGRAPH.md).

See [LANGGRAPH.md](./LANGGRAPH.md) for rollout detail.

---

## Phase 5 — RAG quality (graph nodes + retrieval)

**Goal:** Measurable retrieval improvements — primary quality ROI after publish.

| Item | Graph placement | Primary RAGAS metric |
|------|-----------------|----------------------|
| Metadata filters | Before / during retrieve | context_precision |
| Multi-query + fusion | Between condense and retrieve | context_recall |
| Rerank (FlashRank / managed) | After retrieve, before generate | context_precision |
| Chunking / ingestion docs | Outside runtime | context_recall |

Add nodes to the **same** LangGraph; do not reintroduce monolithic chain.

**Exit criteria:** Primary metric improves on golden set; faithfulness guardrail holds.

Aligns with org roadmap Phase 2 in [PHASED_IMPROVEMENT_ROADMAP.md](./PHASED_IMPROVEMENT_ROADMAP.md).

---

## Phase 6 — Optional: streaming and bounded agentic

**Only after Phase 5 RAGAS stable week-over-week.**

### 6a. LangGraph streaming

> **Status:** LangChain path already exposes `POST /api/chat/stream` (SSE) with Vue consumer and buffered fallback. Phase 6a wires the same contract to a LangGraph graph.

- `graph.astream_events` + `get_streaming_llm()`
- Keep Vue / E2E aligned with existing `/api/chat/stream` event shape

### 6b. Bounded agentic (`RAG_AGENTIC_ENABLED=false` default)

```text
route_query → condense → retrieve → grade_documents
  → (rewrite once max) → generate → format
```

- **Not** multi-agent — conditional edges with hard caps.
- Extra LLM calls: monitor p95 latency and cost.

### 6c. JD keywords without overbuilding

- One optional **tool** (e.g. `search_kb`) if needed for demos.
- README: deterministic default; agentic opt-in.

---

## Evaluation scorecard (per change)

| Field | Example |
|-------|---------|
| Change | LangGraph parity / multi-query node |
| Phase | 4 / 5 |
| Primary metric | context_recall |
| Guardrails | faithfulness ≥ 0.85; p95 < 3s |
| Command | `tox -e eval` with `RAG_ENGINE=langgraph` |
| Ship? | yes / flag-only / no |

---

## What to defer (portfolio)

| Defer | Why |
|-------|-----|
| Full multi-agent (researcher/critic/writer) | Cost, flakiness, weak demo |
| Knowledge-graph RAG | Only if hybrid RAG fails eval |
| Semantic cache | After exact cache + baselines |
| Production Redis HA / tenant budgets | Org roadmap, not portfolio v1 |
| Stripping UC LICENSE | Requires OTL permission; keep for public repo |

---

## Suggested timeline (solo, part-time)

| Weeks | Focus |
|-------|--------|
| 1 | Phase 3: RAGAS baseline + LangSmith trace in README |
| 2 | Phase 4: LangGraph parity + eval gate |
| 3+ | Phase 5–6 as needed for target roles |

---

## Related docs

- [EVALUATION.md](../EVALUATION.md) — RAGAS vs LangSmith
- [LANGGRAPH.md](./LANGGRAPH.md) — graph design and flags
- [PHASED_IMPROVEMENT_ROADMAP.md](./PHASED_IMPROVEMENT_ROADMAP.md) — campus / scale track
- [README.md](../../README.md) — quick start and attribution
