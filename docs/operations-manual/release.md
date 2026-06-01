# Release and environment branches

Campus RAG Assistant uses **environment branches** to trigger stack-specific CI/CD (QA Elastic Beanstalk, production, Vue builds, optional RAGAS gates).

## Branch map

| Branch | Role | Typical CI/CD |
|--------|------|----------------|
| `main` | Integration; feature PRs merge here | [CI](../../.github/workflows/ci.yml): `tox` on PR/push; [Docs](../../.github/workflows/docs.yml): GitHub Pages deploy on docs changes |
| `qa` | QA / staging snapshot | [CD](../../.github/workflows/cd.yml): build Vue + optional EB deploy |
| `release` | Production-ready line | CD + optional RAGAS gate (`RAGAS_QUALITY_GATE=1`) |

**Source of truth:** `main`. Do not land feature work only on `qa` or `release`.

## Promotion flow

Promote by moving branch pointers to a known commit (fast-forward or reset), not by divergent commits on env branches.

```text
main  ──promote──►  qa  ──after QA sign-off──►  release  ──tag──►  v3.0.0
```

Released tags so far: [`v1.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v1.0) (upstream chabot baseline, alias of the historical `v0.1` fork tag), [`v2.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v2.0) (RAG platform transformation), [`v3.0.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v3.0.0) (helpdesk agent). High-level summaries: [release-notes/](../release-notes/index.md).

### Commands (from repo root)

Ensure `main` is clean and up to date, then:

!!! warning "Maintainer-only branch promotion"
    These commands move environment branch pointers and use `git reset --hard`. Run them only from a clean working tree after confirming the target commit, and never use them on feature branches or unmerged work.

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
git tag -a v3.0.0 -m "Campus RAG Assistant v3.0.0 — bounded helpdesk agent, v3 architecture refresh"
git push origin v3.0.0

# Then publish the GitHub Release pointing at the tag and release notes:
gh release create v3.0.0 \
  --title "v3.0.0 — Helpdesk agent + docs refresh" \
  --notes-file docs/release-notes/index.md
```

Use **annotated tags** (`-a`) for releases. Prefer semver (`v3.0.0`, `v3.0.1`) for patch releases. When backfilling a historical release tag for the release ladder (as we did for `v1.0` aliasing `v0.1`), tag the same commit the legacy tag points to.

## Hotfixes

1. Branch from `release` (or `main` if release is not yet updated).
2. Fix, merge to `main`.
3. Re-promote `main` → `qa` → validate → `release` → new tag.

## Multi-stack deploy

A single promoted commit should drive **all** environment artifacts for that stack. The GitHub Pages documentation site deploys from `main` via [docs.yml](../../.github/workflows/docs.yml), independent of `qa` / `release` API deployments:

- FastAPI on Elastic Beanstalk (`run_services.sh` / Procfile)
- Vue static build with `VITE_API_URL` matching that environment
- `alembic upgrade head` before app start (see [OPERATIONS.md](./operations.md))

## Version tags vs branch tips

| Mechanism | Use |
|-----------|-----|
| `release` branch | Moving pointer; triggers “current prod line” pipelines |
| `v2.x.y` tag | Immutable rollback reference, GitHub Releases, changelog |

Tag the same commit `release` points to after promotion.

## Related docs

- [release-notes/](../release-notes/index.md) — high-level summaries for each tag
- [CI.md](./ci-cd.md) — GitHub Actions variables, secrets, workflows
- [changelog/CHANGELOG.md](../../changelog/CHANGELOG.md) — fine-grained per-PR changelog
- [OPERATIONS.md](./operations.md) — deploy order, metrics
- [LOAD_TESTING.md](./load-testing.md) — pre-release load validation
- [EVALUATION.md](../EVALUATION.md) — RAGAS gates on release
