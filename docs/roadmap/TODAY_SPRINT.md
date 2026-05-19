# Today sprint — LangGraph parity (live AWS) + web research

**Date:** 2026-05-18  
**Goal:** LangGraph **KB path** proven on **live AWS** (Bedrock + Knowledge Base), then opt-in web tool.

**Order (strict):** Scaffold → **KB LangGraph** → **live AWS smoke** → unit tests (mock) → web branch → UI/docs.

> **Do not start web or RAGAS until KB graph returns real KB sources on AWS.**

---

## What “done today” means

| Must ship | Nice if time | Skip today |
|-----------|--------------|------------|
| `RAG_ENGINE=langgraph` + **live AWS** KB chat with real `sources` | Chain vs graph same question (manual compare) | RAGAS `tox -e eval` |
| Linear graph: condense → retrieve → generate → format | LangSmith trace screenshot | LangGraph SSE |
| `tox -e lint,backend` green (CI uses **mock**) | Vue `research_mode` toggle | Delete chain path |
| Web: mock tool + API field | Web: Tavily live | Phase 5 rerank |

**CI stays mock** — live AWS is **manual acceptance** before you call parity done.

---

## Live AWS setup (before Block B smoke)

In `.env` (not committed):

```bash
RAG_FORCE_MOCK=false
LLM_PROVIDER=aws
RETRIEVER_PROVIDER=aws
AWS_REGION=us-west-2
AWS_PROFILE_NAME=default          # or keys / SSO
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-haiku-20241022-v1:0
BEDROCK_KNOWLEDGE_BASE_ID=<your-kb-id>

RAG_ENGINE=chain                    # baseline first, then langgraph
LANGCHAIN_TRACING_V2=true           # optional, per-node spans
```

**Preflight:**

```bash
aws sts get-caller-identity --profile "$AWS_PROFILE_NAME"
# Start API, one chain chat — must return non-empty sources
./scripts/run-backend-venv.sh
```

If chain fails on AWS, fix credentials/KB before building the graph.

---

## Hour-by-hour plan (~8–10h with live AWS)

| Block | Time | Deliverable |
|-------|------|-------------|
| **A. Scaffold** | 0:00–0:45 | `langgraph`, `RAG_ENGINE`, `graph/` package |
| **B. KB graph** | 0:45–3:00 | nodes + runner + `process_query` branch |
| **B2. Live AWS smoke** | 3:00–4:00 | **Same 2–3 questions** on `chain` then `langgraph`; real sources both times |
| **C. Tests** | 4:00–5:00 | Mock unit tests (`tox -e lint,backend`) |
| **D. Web** | 5:00–6:30 | Only after B2 passes — mock web + API; Tavily optional |
| **E–F. UI + docs** | 6:30–8:00 | Vue toggle, README, changelog |

**+1–2h buffer** for Bedrock latency, condense/prompt drift, or KB empty results.

---

## Live acceptance checklist (KB path)

- [ ] `RAG_ENGINE=chain` — answer + `metadata.sources` from your KB (not mock text)
- [ ] `RAG_ENGINE=langgraph` — same question, sources present, answer coherent
- [ ] Source fields populated: `kb_url` / `kb_number` / `short_description` where KB provides them
- [ ] No regression: empty sources, 500s, or obvious hallucination vs chain on same prompt
- [ ] Optional: LangSmith shows condense → retrieve → generate spans on graph run

**Parity bar for today:** qualitative match + sources overlap — **not** RAGAS ±0.02.

---

## Implementation checklist

### A. Scaffold

- [ ] `langgraph` in `requirements.txt`
- [ ] `RAG_ENGINE` in `default.py` + `.env.example`
- [ ] `backend/app/services/graph/__init__.py`

### B. KB LangGraph (before web)

- [ ] `state.py`, `nodes.py`, `graph.py`, `runner.py`
- [ ] Reuse `RAGService` prompt templates + `_format_source_documents` + `_normalize_answer_formatting`
- [ ] `rag.py`: `process_query` → `run_rag_graph` when `RAG_ENGINE=langgraph`
- [ ] Mock path in `RAGService` unchanged for unit tests

### B2. Live AWS validation

- [ ] Chain baseline on 2–3 real questions
- [ ] Graph same questions — document in PR/changelog if minor wording diff OK
- [ ] Keep default `RAG_ENGINE=chain` until you are satisfied

### C. Tests (mock only in CI)

- [ ] `backend/tests/services/graph/` — mocked LLM/retriever
- [ ] Do **not** require AWS in `tox -e backend`

### D. Web (after B2)

- [ ] `research_mode` on API; graph branch
- [ ] Mock web for CI; Tavily only if key ready
- [ ] KB live + web live are independent — web does not replace KB smoke

---

## Cut list

| If behind | Drop |
|-----------|------|
| Hour 4 | Web entirely — ship AWS graph only |
| Hour 6 | Vue — curl with `research_mode` |
| Always | RAGAS, graph SSE, flip default to langgraph |

**Never cut:** live AWS KB smoke for graph if you claim “live parity” in README.

---

## After today

1. Phase 3 lite — optional RAGAS on AWS for chain vs graph  
2. Phase 5 — rerank on graph  
3. LangGraph SSE on AWS streaming LLM  

---

## Related

- [LANGGRAPH.md](./LANGGRAPH.md)
- [WEB_RESEARCH.md](./WEB_RESEARCH.md)
- [PORTFOLIO_PHASED_ROADMAP.md](./PORTFOLIO_PHASED_ROADMAP.md)
- [OPERATIONS.md](../OPERATIONS.md) — cloud-backed RAG
