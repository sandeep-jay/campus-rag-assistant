# ADR-004: RAGAS eval gating policy

**Status:** Accepted  
**Date:** 2026-05-19

## Context

RAG quality must be **measured** without blocking every PR on live AWS and judge LLM cost. Hiring readers may misread sub-threshold RAGAS scores as “the product is broken” unless gates are framed as release controls, not marketing claims.

## Decision

Use **two complementary tools** with distinct roles:

| Tool | Role | CI gate |
|------|------|---------|
| **RAGAS** | Offline regression on golden dataset | `RAGAS_QUALITY_GATE=1` on release / local milestone only |
| **LangSmith** | Per-turn and per-node trace inspection | Optional; dev/staging |

**Gate policy**

| Event | `RAGAS_QUALITY_GATE` | Notes |
|-------|----------------------|--------|
| PR / `main` CI (`tox (lint, backend, frontends)`) | **0** | Eval not required; mock RAG |
| Local / release milestone | **1** | `tox -e eval` or `./scripts/run_eval_phase5.sh` |
| CD `release` workflow | **1** when secrets configured | See [CI.md](../CI.md) |

Sub-threshold metrics in [eval_baseline_2026-05-19.md](../eval_baseline_2026-05-19.md) are **documented baselines** with an active improvement path (ingestion, chunking, rerank, golden-set re-bootstrap)—not demo blockers.

## Consequences

**Positive**

- Honest engineering signal for senior reviewers.
- Fast PR CI without AWS judge spend.
- `context_recall` passing (0.80 AWS tuned) shows retrieval work landed; precision gap is named and actionable.

**Negative**

- 10-row golden set is corpus-specific and small—not production quality proof.
- Judge variance can move scores ±0.05–0.15 run-to-run.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Strict gates on every PR | Slow, expensive, flaky without AWS secrets |
| No RAGAS at all | Loses major portfolio differentiator |
| LangSmith scores as RAGAS substitute | Different datasets and judges; not calibrated |

## References

- [EVALUATION.md](../EVALUATION.md)
- [eval_baseline_2026-05-19.md](../eval_baseline_2026-05-19.md)
- `backend/tests/eval/`, `scripts/run_eval_phase5.sh`
- [CI.md](../CI.md)
