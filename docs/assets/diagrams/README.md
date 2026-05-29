# Diagram sources

This folder holds the **single source of truth** for architecture and flow diagrams as Mermaid `.mmd` files. Rendered PNGs (when needed for portfolio framing) live under `docs/assets/`.

## Convention

| File | Purpose |
|---|---|
| `*.mmd` | Mermaid source — edit here. Embed inline in markdown via the `pymdownx.snippets` fence below. |
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
mmdc -i docs/assets/diagrams/architecture_detailed_v3.mmd \
     -o docs/assets/architecture_detailed_v3.png \
     --backgroundColor transparent --width 2400
```

## Current diagrams

| File | Renders | Notes |
|---|---|---|
| `architecture_detailed_v3.mmd` | Detailed v3 architecture | Bands: Frontend / Edge / Backend API / AI &amp; Agents / Providers / External / Data &amp; Observability. Surfaces helpdesk agent and HITL ticket flow. |
