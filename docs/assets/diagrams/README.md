# Diagram sources

Single source of truth for architecture and flow diagrams as Mermaid `.mmd` files. Rendered PNGs (when needed for portfolio framing) live one folder up under `docs/assets/`.

## Reviewer narrative — which diagram answers which question

| Reviewer enters with question | Diagram | File |
|---|---|---|
| "What runs where? Is this really multicloud?" | **System architecture (detailed v3)** — three provider lanes are the visual centerpiece, CI/CD gates and tenant config are surfaced. | `architecture_detailed_v3.mmd` |
| "How sophisticated is the RAG pipeline?" | **AI engineering depth** — every retrieval / eval lever named: multi-query + RRF, metadata filters, rerank backends, web path, RAGAS gates, LangSmith spans, scenario eval. | `rag_pipeline_v3.mmd` |
| "Is this really agentic, or just a chain of LLM calls?" | **Helpdesk agent orchestration** — sequence diagram on a time axis: supervisor picks next_action, tool returns observation, multi-turn pause/resume across SSE, HITL confirm gate, redaction at the boundary, scenario eval guard. | `helpdesk_agent_orchestration_v3.mmd` |
| "What stops the agent from running forever or filing the wrong ticket?" | **Helpdesk agent state machine** — four explicit terminal outcomes (`resolved` · `linked` · `filed` · `aborted`), every transition labeled with the API call or guard. | `helpdesk_agent_state_v3.mmd` |
| "Quick high-level overview" | **Overview PNG** — bands without detail; lives in README. | `../architecture_v3.png` |

The set is intentionally split. One diagram cannot show *multicloud* + *AI engineering levers* + *agent loop on a time axis* + *state machine guarantees* without becoming illegible. Senior architecture decks normally split along these axes.

## Convention

| File | Purpose |
|---|---|
| `*.mmd` | Mermaid source — edit here. Embed inline in markdown via the snippet pattern below. |
| `../architecture_v3.png` (and prior versions) | High-resolution rendered overview asset for README / portfolio framing |

## Embedding inline in mkdocs

Use a `mermaid` fence with a snippet include so the markdown stays a single line and the `.mmd` is the source of truth:

````markdown
```mermaid
--8<-- "docs/assets/diagrams/architecture_detailed_v3.mmd"
```
````

`pymdownx.snippets` is already enabled in `mkdocs.yml`.

## Rendering to PNG (optional)

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i docs/assets/diagrams/architecture_detailed_v3.mmd -o docs/assets/architecture_detailed_v3.png --backgroundColor transparent --width 2400
mmdc -i docs/assets/diagrams/rag_pipeline_v3.mmd -o docs/assets/rag_pipeline_v3.png --backgroundColor transparent --width 2400
mmdc -i docs/assets/diagrams/helpdesk_agent_orchestration_v3.mmd -o docs/assets/helpdesk_agent_orchestration_v3.png --backgroundColor transparent --width 2400
mmdc -i docs/assets/diagrams/helpdesk_agent_state_v3.mmd -o docs/assets/helpdesk_agent_state_v3.png --backgroundColor transparent --width 2400
```

## Style conventions

The detailed diagrams use `classDef` lane colors so multicloud and AI-engineering categories render with consistent semantics:

| Class | Used for | Visual cue |
|---|---|---|
| `awsLane` | AWS provider services | dark blue / orange stroke |
| `azureLane` | Azure provider services | dark blue / Azure blue stroke |
| `mockLane` | Local / CI mock path | dashed gray stroke |
| `registryNode` | Provider registry node | purple — the multicloud pivot |
| `stage` | RAG pipeline stages | mid-blue |
| `evalNode` | RAGAS / LangSmith / scenario eval | magenta |
| `tenantNode` | per-tenant prompt hydration | green |
| `webNode` | Opt-in web research | dashed orange |
| `terminal` (state diagram) | Four explicit agent outcomes | green |
