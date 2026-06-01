# Campus AI Assistant — Agentic Rebuild (refined)

Refinement of the user's draft plan after a full current-state audit. Phasing stays close to the original; the substantive changes are: Phase 1 splits into 1a/1b to reduce mechanical risk, Phase 0 supersedes ADR-005 instead of editing it, Phase 4 ships two eval envs (mock-CI + live-nightly), and Phase 5 ships a live LLM router (per AskQuestion answer).

## Verified facts the plan rests on

- RAG pipeline is a real `StateGraph` ([backend/app/services/graph/graph.py](../../backend/app/services/graph/graph.py) lines 22-46). Helpdesk has **no** `StateGraph` — `helpdesk_graph/nodes.py` exposes only `supervisor_next_action` (3-branch `if/elif`) and `classify_ticket_facts` (keyword matching); orchestration is hand-coded in [backend/app/services/helpdesk_graph/runner.py](../../backend/app/services/helpdesk_graph/runner.py).
- Impact question is unconditional: `_pause_for_impact` is called for every fresh helpdesk question after the no-duplicate branch in `runner.py`.
- Budgets unenforced: `turns_taken` incremented at 3 sites (`runner.py:226`, `:359`, `:528`), never read. No `HELPDESK_AGENT_MAX_*` in [backend/app/config/default.py](../../backend/app/config/default.py).
- Custom JSON-SQLite checkpoint in [backend/app/services/helpdesk_graph/checkpoint.py](../../backend/app/services/helpdesk_graph/checkpoint.py), not LangGraph `SqliteSaver`.
- SSE status is canned in [backend/app/api/helpdesk.py](../../backend/app/api/helpdesk.py) (`Starting helpdesk agent…`, `Checking existing issues…`); real progress only in final `AgentTurn.debug_trace`.
- Redaction gap: `helpdesk_graph/tools.py` does **not** call `redact_text` on the query before GitHub Search / Tavily.
- ADR-005 `Status: Accepted` cites `test_helpdesk_agent_scenarios.py`; [backend/tests/eval/](../../backend/tests/eval/) only has `test_rag_quality.py`.
- `langgraph==0.2.76` and `langgraph-checkpoint==2.0.26` are installed; neither `langgraph-checkpoint-postgres` nor `langgraph-checkpoint-sqlite` is — Phase 1b adds both (Postgres default, SQLite as dev fallback, Memory for tests).
- App already runs Postgres (`DATABASE_URL=postgresql://...`, `psycopg2-binary==2.9.9`, `SQLALCHEMY_POOL_SIZE=5`) and multi-worker uvicorn (`run_services.sh` `WORKERS=${API_WORKERS:-${UVICORN_WORKERS:-2}}`) — a file-based SQLite checkpoint would lock-contend across workers and die on ephemeral-disk redeploys, which is the deciding reason to default the saver to Postgres.
- `_idempotency_key` header is received by `/agent/start` but discarded.

## Target architecture

```mermaid
flowchart TB
  userTurn([user turn]) --> router{CampusRouter<br/>classify_domain}
  router -->|helpdesk| helpdesk
  router -->|kb_answer| rag[RAG StateGraph]
  router -.->|future| futureAgents[research, syllabus,<br/>accessibility]

  subgraph helpdesk [Helpdesk StateGraph]
    direction TB
    supervisor{{Supervisor LLM<br/>SupervisorDecision}}
    supervisor --> toolNode[ToolNode:<br/>retry_kb, web_search,<br/>search_dups, file_ticket*]
    supervisor --> classifier[Classifier LLM]
    supervisor --> clarifier[Clarifier LLM]
    supervisor --> writer[Writer LLM]
    supervisor --> solution[Solution LLM]
    toolNode --> supervisor
    classifier --> supervisor
    clarifier --> awaitUser([interrupt: await_user])
    awaitUser --> supervisor
    writer --> awaitConfirm([interrupt: await_confirm])
    awaitConfirm -->|HITL confirm| toolNode
    supervisor --> terminals[resolved · linked · filed · aborted]
  end

  helpdesk -. AsyncPostgresSaver checkpointer<br/>thread_id = chat_session_id .- helpdesk
```

`file_ticket` is reachable only via `/agent/confirm`. Closed `NextAction` enum is enforced in code, not just prompt.

## Non-negotiable invariants (carried from the draft, unchanged)

Closed action enum + allow-list, structured outputs everywhere, hard budgets in code, HITL gate on side effects, untrusted-content guard, redaction on tool I/O, per-node model selection, deterministic mock plans, every node a LangSmith span, typed state reducers, idempotency keys on writes.

## Phases and PRs

### Phase -1 — Docker Compose Postgres + fresh start (PR 0)

Pure infra. No backend code change. Lays the substrate that Phase 1b depends on.

- **`docker-compose.yml` at repo root.** `postgres:14` (matches the local Homebrew 14.17 and the production target), named volume `pgdata`, healthcheck (`pg_isready -U chatbot -d chatbot_dev`), restart policy `unless-stopped`, env `POSTGRES_USER=chatbot` / `POSTGRES_PASSWORD=chatbot` / `POSTGRES_DB=chatbot_dev` so the repo's development `DATABASE_URL=postgresql://chatbot:chatbot@127.0.0.1:5432/chatbot_dev` in [.env.example](../../.env.example) and [backend/app/config/development.py](../../backend/app/config/development.py) points at the container unchanged. Expose `5432:5432`.
- **Init SQL** in `scripts/init-db.sql` (`docker-entrypoint-initdb.d` mount) only for any non-default grants; the env vars alone create the role + DB.
- **`scripts/run-backend-venv.sh`** gains a one-liner that ensures the `db` service is up before launching uvicorn (`docker compose --env-file /dev/null up -d db` + wait-for healthcheck), with a `SKIP_DOCKER_DB=1` escape hatch for users still on Homebrew Postgres.
- **Cutover steps** (documented in `docs/operations-manual/operations.md`, not enforced by code):
  1. `pg_dump chatbot_dev > /tmp/chatbot_dev_pre_docker.sql` (optional — preserve local history first; use `chatbot` instead if older sessions still live in the default database).
  2. `brew services stop postgresql@14` (or `pg_ctl stop`) to free port 5432.
  3. `docker compose --env-file /dev/null up -d db`.
  4. `alembic upgrade head` against the fresh container.
  5. Optional `psql -h localhost -U chatbot -d chatbot_dev -f /tmp/chatbot_dev_pre_docker.sql` if you want history.
- **Docs.** Update README Quick Start and `docs/operations-manual/operations.md` so the documented dev setup is `docker compose --env-file /dev/null up -d db` first, `./scripts/run-backend-venv.sh` second. Keep the Homebrew Postgres path in a "Fallback" subsection for one release; remove it in the Phase 1b PR once the Postgres-backed checkpointer is in.
- **CI parity callout.** No change to GitHub Actions yet (it already uses a Postgres service container), but this makes the local-vs-CI gap visibly smaller for any reviewer reading the diff.
- Acceptance: `docker compose --env-file /dev/null up -d db && alembic upgrade head && PIP_SYNC=0 ./scripts/run-backend-venv.sh` boots the app cleanly against the container, `/api/health` returns ok, mock-mode chat works end-to-end, existing pytest suite passes. The repo no longer requires Homebrew Postgres to develop.

### Phase 0 — Guardrails + truth-in-docs (PR 1)

- **0.1 Budgets in config + enforcement.** Add `HELPDESK_AGENT_MAX_TURNS=8`, `..._MAX_QUESTIONS=2`, `..._MAX_TOOL_RETRIES=2`, `..._MAX_TOKENS_PER_SESSION=20000`, `..._DEADLINE_SECONDS=60.0` to [backend/app/config/default.py](../../backend/app/config/default.py). Enforce at every site that increments `turns_taken` (`runner.py:226`, `:359`, `:528`) plus at the top of `start_session`/`resume_session`. On cap, force `_draft_from_state(...)` → `await_user_confirm` with `debug_trace` note `budget_exhausted`. Never raise to user.
- **0.2 Redact tool inputs.** Import `redact_text` from [backend/app/services/helpdesk/redaction.py](../../backend/app/services/helpdesk/redaction.py); call it inside [backend/app/services/helpdesk_graph/tools.py](../../backend/app/services/helpdesk_graph/tools.py) `retry_kb`, `web_search`, `search_existing_issues` before any outbound use. Add a test that an injected `AKIA…` token never appears in the GitHub `q=` or Tavily query.
- **0.3 ADR-006 supersession.** Do **not** edit ADR-005 (`Status: Accepted`, immutable by convention). Add `docs/adr/ADR-006-live-llm-supervisor-migration.md` `Status: Proposed`, listing exactly what's currently built vs. what Phase 1–4 will build. Update README + `docs/roadmap/HELPDESK_AGENT.md` so present-tense claims about LLM supervisor / SqliteSaver / specialists / budgets / eval are moved under a "Target state (in progress)" heading and cross-reference ADR-006.
- Acceptance: `tox -e backend -- -k helpdesk` green, runaway-session test ends in a draft, redaction test passes, no doc claims an unbuilt feature.

### Phase 1a — Compile a StateGraph, behavior unchanged (PR 2)

- New `backend/app/services/helpdesk_graph/graph.py` mirroring `graph/graph.py`. Nodes: `supervisor`, `tools` (LangGraph `ToolNode`), `clarifier`, `classifier`, `writer`, `solution`, `await_user`, `await_confirm`, terminals. `START → supervisor`; conditional edges from `supervisor` keyed on `next_action`; tool/specialist nodes route back to `supervisor`.
- Supervisor node delegates to the existing `supervisor_next_action` (extended to the full enum) — no LLM yet.
- Specialist nodes wrap existing helpers (`_propose_solution_or_draft`, `_draft_from_state`, etc.) so behavior is unchanged.
- Rewire [backend/app/services/helpdesk_graph/runner.py](../../backend/app/services/helpdesk_graph/runner.py) entry points to `graph.ainvoke(...)`. Keep custom `checkpoint.py` and the existing `awaiting_user` field for now.
- Keep `AgentTurn` schema and `/api/helpdesk/agent/*` signatures byte-identical.
- Acceptance: all existing helpdesk API tests pass unchanged; LangSmith shows a real graph tree; mock-mode demo unchanged.

### Phase 1b — AsyncPostgresSaver + interrupt() swap (PR 3)

Postgres default (per AskQuestion answer), with SQLite + Memory fallbacks. Schema owned by Alembic, not `AsyncPostgresSaver.setup()`.

**Why Postgres default:** the app already runs `WORKERS>=2` uvicorn workers — file-based SQLite would lock-contend across processes and lose state on container redeploys. Postgres is already the system of record for `chat_session.id` (the planned `thread_id`), so the checkpoint sits in the same backup / pool-metrics / secrets surface as the rest of the app.

- **Dependencies.** Add to `requirements.txt`:
  - `langgraph-checkpoint-postgres==2.0.9` (requires `langgraph-checkpoint>=2.0.7,<3` — compatible with the repo's `2.0.26`).
  - `langgraph-checkpoint-sqlite` pinned to a compatible 2.0.x line (kept for dev fallback).
  - `psycopg[binary,pool]>=3.2,<4` (`langgraph-checkpoint-postgres` uses psycopg3; runs alongside the existing `psycopg2-binary` which stays for SQLAlchemy). Update `tox` envs.
- **Backend selector.** New setting `HELPDESK_AGENT_CHECKPOINT_BACKEND: Literal['postgres','sqlite','memory'] = 'postgres'`. New saver factory in [backend/app/services/helpdesk_graph/checkpoint.py](../../backend/app/services/helpdesk_graph/checkpoint.py):
  - `postgres`: `AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)` — async to match the runner; reuses the existing DSN.
  - `sqlite`: `AsyncSqliteSaver` at `HELPDESK_AGENT_CHECKPOINT_PATH` (zero-infra demo mode).
  - `memory`: `MemorySaver()` for pytest.
- **Alembic migration owns the schema.** New revision creates `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` matching the AsyncPostgresSaver shape (transcribed from `AsyncPostgresSaver.setup()` once and committed). Do **not** call `setup()` at app startup; the app trusts Alembic. Document this in the revision message + `docs/operations-manual/operations.md` so the next saver-version bump is a real migration, not a silent table mutation.
- **TTL/GC.** `AsyncPostgresSaver` doesn't prune. Add a periodic sweep (background task or cron) that deletes `checkpoints` rows older than `HELPDESK_AGENT_CHECKPOINT_TTL_SECONDS` (default 86400). Same code shape used by the SQLite backend.
- **Pause/resume primitive.** Replace `_pause_for_impact`'s `awaiting_user` + custom-resume dance with `langgraph.types.interrupt()` inside `await_user` / `await_confirm`. `/agent/resume` and `/agent/confirm` feed the resume value via `Command(resume=...)`.
- **Tests.** Default `backend/tests/conftest.py` to monkeypatch `HELPDESK_AGENT_CHECKPOINT_BACKEND='memory'`; one integration test runs against a real Postgres (the same DB the existing pytest setup already uses). [backend/tests/api/test_helpdesk.py:39](../../backend/tests/api/test_helpdesk.py) updated accordingly.
- **Rollback flag.** Keep `HELPDESK_AGENT_USE_LANGGRAPH_CHECKPOINT=true|false` (default `true`); the hand-rolled `checkpoint.py` path stays for one release for instant rollback.
- Acceptance: pause/close-tab/resume works through the Postgres checkpointer; `alembic upgrade head` / `downgrade -1` round-trips cleanly; existing API tests pass unchanged with the memory saver; one integration test exercises the Postgres path end-to-end.

### Phase 2 — Make it agentic (PRs 4 + 5)

- **2.1 + 2.2 (PR 4): tools as `@tool`, LLM supervisor behind flag.** Wrap `retry_kb`, `web_search`, `search_existing_issues`, `file_ticket` as `@tool` with Pydantic arg schemas; respect existing per-tool feature flags (a disabled tool is not bindable). Define `SupervisorDecision(next_action: NextAction, reason: str, args: dict = {})`. New adapter `backend/app/services/helpdesk_graph/llm.py` exposes `supervisor_decide(state) -> SupervisorDecision` and `classify(state) -> TicketClassification` so providers/{aws,azure,mock}.py differences are hidden. Use `with_structured_output(SupervisorDecision)`. Validate against the enum + allow-list; on invalid → safe default (`write_draft → await_user_confirm`). One parse-failure repair retry, then fallback to `supervisor_next_action`. Gated by `HELPDESK_AGENT_LLM_SUPERVISOR=true|false` (default `false`).
- **2.3 (PR 5): help-first as a code rule.** When `turns_taken==0` and no solution attempted, the supervisor allow-list excludes `ask_user`. Reflect the rule in `SUPERVISOR_PROMPT` so the model agrees rather than fights the gate.
- **2.4 (PR 5): LLM classifier specialist.** Replace `classify_ticket_facts` with a `classifier` node returning `TicketClassification(severity, category, impact, confidence)` via structured output. Deterministic keyword classifier retained as low-confidence/parse-failure fallback and as the mock-mode return value.
- **2.5 (PR 5): conditional clarification.** Clarifier runs only when supervisor picks `ask_user`, which it should pick only when classifier `confidence < CLARIFY_CONFIDENCE_FLOOR` AND the missing fact changes severity or routing. When asked, batch multiple gaps into one turn and phrase as confirmation of inferred value. Respect `HELPDESK_AGENT_MAX_QUESTIONS`.
- **2.6 (PR 5): writer specialist.** Reuse `WRITER_PROMPT`/`draft_ticket` as a graph node; keep redaction pre-call.
- **Mock parity (both PRs).** Mock supervisor → scripted decision sequence tied to sentinel queries. Mock classifier → keyword classifier. Mock clarifier → fixed question text per intent. Mock writer → existing `_mock` draft path.
- **Idempotency (PR 5).** Honor `Idempotency-Key` on `/agent/confirm`: dedup by `(user_id, key)` for `HELPDESK_DEDUP_WINDOW_SECONDS`; double-click returns the prior `AgentTurn`.
- Acceptance: in mock mode, the 3 demo scenarios (§Demo) produce the expected action sequences; impact question appears in 0/2 clear scenarios and 1/1 ambiguous; a forced bad supervisor output cannot execute an out-of-enum action or reach `file_ticket` without `/agent/confirm`; budgets terminate gracefully.

### Phase 3 — Real-event SSE + UI trace + metrics (PR 6)

- Rewrite `/agent/start/stream` and `/agent/resume/stream` in [backend/app/api/helpdesk.py](../../backend/app/api/helpdesk.py) to stream from `graph.astream_events(version='v2')`. Filter to a small set: `on_chain_start`/`on_chain_end` for nodes the user cares about (`supervisor`, `clarifier`, `classifier`, `writer`, `solution`), and `on_tool_start`/`on_tool_end` for the four tools. Emit one SSE `step` event per filtered event with `{node, action, status, latency_ms, summary}`. Delete the canned status strings.
- Vue trace panel: collapsible "What the agent did" timeline in `frontend-vue/` (new component), consuming live `step` events and the persisted `debug_trace` on refresh. Columns: step → tool/specialist → outcome → latency.
- LangSmith tags: every node/tool span tagged `session:<id>`, `agent:helpdesk`, `decision:<next_action>`.
- Prometheus additions in [backend/app/core/metrics.py](../../backend/app/core/metrics.py): `chatbot_helpdesk_agent_tool_latency_seconds{tool}` (histogram), `..._tokens_total{node}`, `..._decision_total{next_action}`, `..._turns_taken` (histogram by outcome). Keep funnel/outcome/error counters.
- Structured logs at each node boundary correlated by `session_id` + `X-Request-ID`.
- Acceptance: `/agent/*/stream` shows real, time-ordered node/tool events; UI timeline matches LangSmith tree for the same session; new metrics on `/api/metrics`.

### Phase 4 — Trajectory eval split (PR 7)

- **Status:** Implemented in the current Phase 4 slice: mock `tox -e agent-eval` is wired into PR CI, and live `tox -e agent-eval-live` runs on schedule/manual workflow dispatch.
- **4.1 Dataset.** `backend/tests/eval/helpdesk_agent_scenarios.json`: `{id, conversation, expected_actions[], expect_question, expected_outcome}`. Cover: resolve-without-ticket, infer-don't-ask (campus-wide outage), ask-when-ambiguous, duplicate→linked, budget-exhaustion, injection-in-tool-output, HITL respected.
- **4.2 Mock-CI gate.** `backend/tests/eval/test_helpdesk_agent_scenarios.py` runs in mock mode and gates on: tool-recall, **over-ask rate**, false-escalation rate, unnecessary-loop count, resolve-without-ticket rate, HITL respected, injection resistance. New env `tox -e agent-eval` runs on every PR. Gate: no regression in over-ask/false-escalation/HITL/injection.
- **4.3 Live-nightly eval.** New env `tox -e agent-eval-live` requires AWS + LangSmith keys; runs the same dataset against the live LLM supervisor and emits the comparison table (LLM supervisor vs. retained deterministic `supervisor_next_action`). Schedule via GitHub Actions nightly + pre-release; **not** a PR gate (cost/time). The plan's "prove it beats the DAG" claim is honest only because this exists.
- **4.4** Keep RAGAS for retrieval quality unchanged. Optionally add a LangSmith dataset + evaluators for online runs.
- Acceptance: `tox -e agent-eval` runs on PRs and prints the metric table; `tox -e agent-eval-live` runs nightly with a comparison table; CI fails on regression of the four gated metrics.

### Phase 5 — Live campus router (PR 8)

Chosen scope: **live router** (per AskQuestion answer).

- **Status:** Implemented. Registry + router are off-by-default in PR CI; mock-mode router runs deterministically and the structured-output path routes through the configured provider once `CAMPUS_ROUTER_ENABLED=true`.
- **5.1 Capability registry.** New `backend/app/services/agents/registry.py` maps `domain → AgentSpec{name, subgraph_factory, tools, enabled_flag}`. `helpdesk` is registered at import time; the seam test in `backend/tests/services/agents/test_registry.py` adds a no-op `echo` agent and proves the router does not need to change.
- **5.2 Live LLM router node.** New `classify_domain(turn) -> RouterDecision{domain: 'helpdesk'|'kb_answer', confidence: float}` via structured output. Runs on every chat turn behind `CAMPUS_ROUTER_ENABLED=false` (default off, on for demo). Output combined with existing `kb_resolved` to gate the escalation chip in the UI: chip shows if `kb_resolved == false` OR `(router.domain == 'helpdesk' AND confidence ≥ ROUTER_HELPDESK_FLOOR)`. Mock-mode router returns `helpdesk` for the same demo sentinel queries the mock RAG path uses, so PR CI never calls a live LLM.
- **5.3 ADR-007.** `docs/adr/ADR-007-agent-registry-and-router.md` `Status: Proposed`. Pair with `docs/roadmap/AGENT_REGISTRY.md` describing the contract for a future syllabus / accessibility / research agent (subgraph factory + tools + flag + register).
- Acceptance: router enabled, escalations route to helpdesk and normal questions to RAG (both traced); adding a no-op `echo` agent to the registry in a test proves the seam without touching the router.

## Out of scope (deferred)

Specialist agents (research, T&L, syllabus, accessibility); RAG-side agentic rewrite loop (`RAG_AGENTIC_ENABLED`); multi-agent collaboration. FAISS local retriever (`RETRIEVER_PROVIDER=faiss` joining the existing aws/azure/mock registry) tracked as a future **ADR-008** for a no-cloud-but-real-retrieval demo path; not needed for the agentic rebuild because mock mode's deterministic sentinel hits are actually preferable for gating the trajectory eval in CI.

## Working agreement (carried forward)

Never break mock mode; small revertible PRs each behind a flag; test trajectories for every supervisor-routing or budget change; preserve `/agent/*` API signatures and `AgentTurn` schema; keep `HELPDESK_AGENT_LLM_SUPERVISOR=false` as instant fallback; update docs in the same PR as the capability.

## Demo (run with UI trace + LangSmith tab open, mock mode)

1. **Resolve without a ticket.** KB-answerable question → `retry_kb` → solution → user accepts → `resolved_by_agent`. The impact question never appears.
2. **Infer, don't ask.** *"Canvas is down for everyone"* → classifier infers campus-wide/critical high-confidence → no `ask_user` → pre-filled draft → user confirms → `filed`.
3. **Ask only when warranted.** Genuinely ambiguous report → one targeted confirmatory question → draft.

Reveal: LangSmith run tree shows supervisor decisions + tool spans; the trajectory eval table shows the LLM supervisor measurably beating the retained deterministic supervisor on over-ask and false-escalation.