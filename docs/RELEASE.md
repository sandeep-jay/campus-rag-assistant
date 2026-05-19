# Release and environment branches

Campus RAG Assistant uses **environment branches** to trigger stack-specific CI/CD (QA Elastic Beanstalk, production, Vue builds, optional RAGAS gates).

## Branch map

| Branch | Role | Typical CI/CD |
|--------|------|----------------|
| `main` | Integration; feature PRs merge here | [CI](../.github/workflows/ci.yml): `tox` on PR/push |
| `qa` | QA / staging snapshot | [CD](../.github/workflows/cd.yml): build Vue + optional EB deploy |
| `release` | Production-ready line | CD + optional RAGAS gate (`RAGAS_QUALITY_GATE=1`) |

**Source of truth:** `main`. Do not land feature work only on `qa` or `release`.

## Promotion flow

Promote by moving branch pointers to a known commit (fast-forward or reset), not by divergent commits on env branches.

```text
main  ──promote──►  qa  ──after QA sign-off──►  release  ──tag──►  v2.0.0
```

### Commands (from repo root)

Ensure `main` is clean and up to date, then:

```bash
git fetch origin
git checkout main
git pull origin main

# QA ← main
git checkout qa
git reset --hard main
git push origin qa

# release ← qa (same commit as main after promotion)
git checkout release
git reset --hard qa
git push origin release

# Immutable release marker (on release branch tip)
git tag -a v2.0.0 -m "Campus RAG Assistant v2.0 — Vue SPA, LangGraph RAG, Phase 5 retrieval, web research, RAGAS baseline"
git push origin v2.0.0
```

Use **annotated tags** (`-a`) for releases. Prefer semver (`v2.0.0`, `v2.0.1`) for patch releases.

## Hotfixes

1. Branch from `release` (or `main` if release is not yet updated).
2. Fix, merge to `main`.
3. Re-promote `main` → `qa` → validate → `release` → new tag.

## Multi-stack deploy

A single promoted commit should drive **all** environment artifacts for that stack:

- FastAPI on Elastic Beanstalk (`run_services.sh` / Procfile)
- Vue static build with `VITE_API_URL` matching that environment
- `alembic upgrade head` before app start (see [OPERATIONS.md](./OPERATIONS.md))

## Version tags vs branch tips

| Mechanism | Use |
|-----------|-----|
| `release` branch | Moving pointer; triggers “current prod line” pipelines |
| `v2.x.y` tag | Immutable rollback reference, GitHub Releases, changelog |

Tag the same commit `release` points to after promotion.

## Related docs

- [CI.md](./CI.md) — GitHub Actions variables, secrets, workflows
- [changelog/CHANGELOG.md](../changelog/CHANGELOG.md) — release notes
- [OPERATIONS.md](./OPERATIONS.md) — deploy order, metrics
- [LOAD_TESTING.md](./LOAD_TESTING.md) — pre-release load validation
- [EVALUATION.md](./EVALUATION.md) — RAGAS gates on release
