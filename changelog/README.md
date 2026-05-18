# Changelog

| Location | Purpose |
|----------|---------|
| [**../CHANGELOG.md**](../CHANGELOG.md) | **Running log** — edit `[Unreleased]` for every merge-worthy change |
| [**archive/**](./archive/) | **Frozen session notes** — detailed history, not edited after archive |

## Workflow

1. While developing: add bullets under **`CHANGELOG.md` → [Unreleased]**.
2. When you merge a milestone: rename `[Unreleased]` to `## [YYYY-MM-DD] — title` in **CHANGELOG.md** and start a new `[Unreleased]`.
3. Optional: after a large session, copy a detailed draft into `archive/YYYY-MM-DD-<topic>.md` (one file per session). Do not rewrite archives later.

## Archive index

| File | Summary |
|------|---------|
| [2026-05-01-logging-correlation-request-id.md](./archive/2026-05-01-logging-correlation-request-id.md) | Request ID middleware, JSON logs, auth log hygiene |
| [2026-05-01-rag-streaming-ratelimit.md](./archive/2026-05-01-rag-streaming-ratelimit.md) | Providers, Vue, rate limits, RAGAS, Alembic (also describes SSE/FlashRank **planned**, not all on `main`) |

Older local files in gitignored `changelog/*.md` at this folder root are duplicates; **archive/** is canonical on git.
