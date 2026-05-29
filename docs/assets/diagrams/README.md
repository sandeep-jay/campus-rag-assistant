# Diagram sources

This folder holds the **single source of truth** for architecture and flow diagrams as Mermaid `.mmd` files. Rendered PNGs (when needed for portfolio framing) live under `docs/assets/`.

## Convention

| File | Purpose |
|---|---|
| `*.mmd` | Mermaid source — edit here. Embed inline in markdown via the `pymdownx.snippets` fence below. |
| `../architecture_v3.png` (and prior versions) | High-resolution rendered overview asset for README / portfolio framing |

## Diagram set

| File | Story it tells | Companion |
|---|---|---|
| `architecture_detailed_v3.mmd` | **System architecture** — what runs where. Multicloud lanes (AWS · Azure · Local/CI) are the visual centerpiece. CI/CD gates and tenant config are surfaced as portfolio-relevant signals. | High-level: `../architecture_v3.png` |
| `rag_pipeline_v3.mmd` | **AI engineering depth** — the LangGraph RAG with every retrieval/eval lever (multi-query + RRF, metadata filters, rerank backends, web path, RAGAS gates, LangSmith spans, scenario eval). | Helpdesk topology: `../../roadmap/HELPDESK_AGENT.md` |

The split exists because one diagram cannot show both "this works on three clouds" *and* "look at every retrieval lever" without becoming illegible. Reviewers entering from the README see the system diagram first; reviewers digging into AI quality see the RAG pipeline diagram.

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
mmdc -i docs/assets/diagrams/architecture_detailed_v3.mmd \
     -o docs/assets/architecture_detailed_v3.png \
     --backgroundColor transparent --width 2400
mmdc -i docs/assets/diagrams/rag_pipeline_v3.mmd \
     -o docs/assets/rag_pipeline_v3.png \
     --backgroundColor transparent --width 2400
```

## Style conventions

Both detailed diagrams use `classDef` lane colors so multicloud and AI-engineering categories render with consistent semantics:

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
