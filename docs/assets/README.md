# Doc assets

Screenshots for the portfolio README and live demos. Product UI and LangSmith traces live in subfolders; architecture PNGs stay at this level.

## Architecture

| File | Use |
|------|-----|
| [architecture_v2.png](architecture_v2.png) | README + [ARCHITECTURE.md](../ARCHITECTURE.md) (primary) |
| [architecture_detailed_v2.png](architecture_detailed_v2.png) | ARCHITECTURE.md detail |
| [architecture_v1.png](architecture_v1.png) | Upstream reference / comparison |

## Product UI (`product/`)

| File | Description |
|------|-------------|
| [chat-empty-state.png](product/chat-empty-state.png) | Welcome screen + suggested prompts |
| [chat-assistant-response.png](product/chat-assistant-response.png) | Full chat with structured KB answer |
| [chat-sources-kb.png](product/chat-sources-kb.png) | KB source citations (Sources tab) |
| [chat-sources-content-kb.png](product/chat-sources-content-kb.png) | Retrieved chunk excerpts (Content tab) |
| [chat-web-research-answer.png](product/chat-web-research-answer.png) | Web mode answer + disclaimer |
| [chat-sources-web.png](product/chat-sources-web.png) | Web search source list |

Embedded in the root [README](../../README.md#screenshots).

## Auth (`auth/`)

| File | Description |
|------|-------------|
| [sign-in.png](auth/sign-in.png) | Login + GitHub OAuth |
| [register.png](auth/register.png) | Registration form |

## Observability (`observability/`)

| File | Description |
|------|-------------|
| [langsmith-trace-kb-waterfall.png](observability/langsmith-trace-kb-waterfall.png) | **README** — KB path waterfall |
| [langsmith-trace-kb-tree.png](observability/langsmith-trace-kb-tree.png) | KB path tree (slides / deep dive) |
| [langsmith-trace-web-waterfall.png](observability/langsmith-trace-web-waterfall.png) | Web research waterfall |
| [langsmith-trace-web-tree.png](observability/langsmith-trace-web-tree.png) | Web research tree |
| [langsmith-runs-table.png](observability/langsmith-runs-table.png) | Project runs table (ops appendix) |

KB waterfall is in [README — Quality](../../README.md#quality-and-observability).

## Product demo script (~2–3 min)

| Step | Asset | Talking point |
|------|-------|----------------|
| 1 | [sign-in.png](auth/sign-in.png) | GitHub OAuth or local account; dev OAuth on API port 8000 |
| 2 | [chat-empty-state.png](product/chat-empty-state.png) | Scoped to campus KB; suggested prompts |
| 3 | [chat-assistant-response.png](product/chat-assistant-response.png) | Structured answer from bCourses KB |
| 4 | [chat-sources-kb.png](product/chat-sources-kb.png) | Transparent citations (ServiceNow KB URLs) |
| 5 | [chat-web-research-answer.png](product/chat-web-research-answer.png) | Opt-in **Search the web** + disclaimer |
| 6 | [chat-sources-web.png](product/chat-sources-web.png) | Web sources labeled WEB |
| 7 *(optional)* | [langsmith-trace-kb-waterfall.png](observability/langsmith-trace-kb-waterfall.png) | LangGraph spans (technical audience) |

### README picks (static gallery)

| Placement | File |
|-----------|------|
| Hero / first impression | `product/chat-empty-state.png` |
| Core RAG value | `product/chat-assistant-response.png` |
| Sources | `product/chat-sources-kb.png` |
| Phase 6b web | `product/chat-web-research-answer.png` |
| Quality / observability | `observability/langsmith-trace-kb-waterfall.png` |

### Demo-only (not in README)

- `product/chat-sources-content-kb.png` — Content tab depth
- `observability/langsmith-trace-kb-tree.png` — redundant with waterfall
- `observability/langsmith-runs-table.png` — ops monitoring
- `auth/register.png` — same flow as sign-in
