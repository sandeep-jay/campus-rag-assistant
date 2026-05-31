# Doc assets

Screenshots and architecture diagrams for the root README and live demos. Assets are organized by **version** (`v1` upstream baseline, `v2` RAG platform, `v3` helpdesk agent).

## Architecture diagrams

### v3 (current)

| File | Use |
|------|-----|
| [architecture/v3/overview.png](architecture/v3/overview.png) | README Overview + [ARCHITECTURE.md](../ARCHITECTURE.md) (primary) |
| [architecture/v3/detailed.png](architecture/v3/detailed.png) | README Overview + ARCHITECTURE.md detail |
| [architecture/v3/topology.png](architecture/v3/topology.png) | Full RAG + agent subgraph topology |

### v2 (RAG platform)

| File | Use |
|------|-----|
| [architecture/v2/overview.png](architecture/v2/overview.png) | v2 high-level overview (historical) |
| [architecture/v2/detailed.png](architecture/v2/detailed.png) | v2 component detail (historical) |

### v1 (upstream baseline)

| File | Use |
|------|-----|
| [architecture/v1/architecture.png](architecture/v1/architecture.png) | Upstream [chabot](https://github.com/ets-berkeley-edu/chabot) reference |

## Product UI — v3 (helpdesk agent)

| File | Description |
|------|-------------|
| [product/v3/chat-overview.png](product/v3/chat-overview.png) | Full chat UI: sidebar, Ask/Agent toggle, KB answer |
| [product/v3/chat-sources-kb.png](product/v3/chat-sources-kb.png) | KB source citations (Sources tab) — README pick |
| [product/v3/chat-sources-kb-context.png](product/v3/chat-sources-kb-context.png) | Sources panel with chat context above |
| [product/v3/chat-sources-content-kb.png](product/v3/chat-sources-content-kb.png) | Retrieved chunk excerpts (Content tab) |
| [product/v3/agent-no-kb-match-options.png](product/v3/agent-no-kb-match-options.png) | No KB match + Summarize / Get help / Create ticket chips |
| [product/v3/agent-hitl-impact-question.png](product/v3/agent-hitl-impact-question.png) | HITL clarifying question (impact radio) |
| [product/v3/agent-proposed-solution.png](product/v3/agent-proposed-solution.png) | Multi-step trace + outcome chips |
| [product/v3/agent-ticket-draft.png](product/v3/agent-ticket-draft.png) | Review support ticket modal |
| [product/v3/github-issues-created.png](product/v3/github-issues-created.png) | GitHub Issues list (filed tickets) |

## Product UI — v2 (RAG chat)

| File | Description |
|------|-------------|
| [product/v2/chat-empty-state.png](product/v2/chat-empty-state.png) | Welcome screen + suggested prompts |
| [product/v2/chat-assistant-response.png](product/v2/chat-assistant-response.png) | Full chat with structured KB answer |
| [product/v2/chat-sources-kb.png](product/v2/chat-sources-kb.png) | KB source citations (v2 UI) |
| [product/v2/chat-sources-content-kb.png](product/v2/chat-sources-content-kb.png) | Retrieved chunk excerpts (v2 UI) |
| [product/v2/chat-web-research-answer.png](product/v2/chat-web-research-answer.png) | Web mode answer + disclaimer |
| [product/v2/chat-sources-web.png](product/v2/chat-sources-web.png) | Web search source list |

## Auth

| File | Description |
|------|-------------|
| [auth/v3/sign-in.png](auth/v3/sign-in.png) | Sign-in page (v3 branding) — README pick |
| [auth/v1/sign-in.png](auth/v1/sign-in.png) | Sign-in page (v2 branding) |
| [auth/v1/register.png](auth/v1/register.png) | Registration form |

## Observability (`observability/`)

| File | Description |
|------|-------------|
| [langsmith-trace-kb-waterfall.png](observability/langsmith-trace-kb-waterfall.png) | **README** — KB path waterfall |
| [langsmith-trace-kb-tree.png](observability/langsmith-trace-kb-tree.png) | KB path tree (slides / deep dive) |
| [langsmith-trace-web-waterfall.png](observability/langsmith-trace-web-waterfall.png) | Web research waterfall |
| [langsmith-trace-web-tree.png](observability/langsmith-trace-web-tree.png) | Web research tree |
| [langsmith-runs-table.png](observability/langsmith-runs-table.png) | Project runs table (ops appendix) |

## Product demo script (~3–4 min, v3)

| Step | Asset | Talking point |
|------|-------|----------------|
| 1 | [auth/v3/sign-in.png](auth/v3/sign-in.png) | GitHub OAuth or local account |
| 2 | [product/v3/chat-overview.png](product/v3/chat-overview.png) | Ask vs Agent mode; KB answer with sidebar |
| 3 | [product/v3/chat-sources-kb.png](product/v3/chat-sources-kb.png) | Transparent citations (ServiceNow KB links) |
| 4 | [product/v3/agent-no-kb-match-options.png](product/v3/agent-no-kb-match-options.png) | Switch to Agent; unresolved query → action chips |
| 5 | [product/v3/agent-hitl-impact-question.png](product/v3/agent-hitl-impact-question.png) | Agent asks one targeted clarifying question |
| 6 | [product/v3/agent-proposed-solution.png](product/v3/agent-proposed-solution.png) | Multi-step trace; user picks outcome |
| 7 | [product/v3/agent-ticket-draft.png](product/v3/agent-ticket-draft.png) | HITL ticket review with redaction warning |
| 8 | [product/v3/github-issues-created.png](product/v3/github-issues-created.png) | Filed issue in demo GitHub repo |
| 9 *(optional)* | [langsmith-trace-kb-waterfall.png](observability/langsmith-trace-kb-waterfall.png) | LangGraph spans (technical audience) |

### README picks (static gallery)

| Placement | File |
|-----------|------|
| Hero / first impression | `product/v3/chat-overview.png` |
| Architecture overview | `architecture/v3/overview.png` |
| Architecture detail | `architecture/v3/detailed.png` |
| Sources | `product/v3/chat-sources-kb.png` |
| Helpdesk agent | `product/v3/agent-ticket-draft.png` |
| Phase 6b web (v2 UI) | `product/v2/chat-web-research-answer.png` |
| Quality / observability | `observability/langsmith-trace-kb-waterfall.png` |

### Demo-only (not in README)

- `product/v3/chat-sources-content-kb.png` — Content tab depth
- `product/v2/chat-sources-content-kb.png` — v2 Content tab
- `observability/langsmith-trace-kb-tree.png` — redundant with waterfall
- `observability/langsmith-runs-table.png` — ops monitoring
- `auth/v1/register.png` — same flow as sign-in
