# CI/CD (GitHub Actions)

Automated checks replace Travis CI. **Tox** remains the source of truth for what runs locally and in CI.

## Workflows

| Workflow | File | Triggers |
|----------|------|----------|
| **CI** | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | Push to `main`; PRs to `main`, `qa`, `release` |
| **CD** | [`.github/workflows/cd.yml`](../.github/workflows/cd.yml) | Push to `qa` or `release`; manual `workflow_dispatch` |
| **Docs** | [`.github/workflows/docs.yml`](../.github/workflows/docs.yml) | PRs touching docs/site files; push to `main`; manual `workflow_dispatch` |
| **No tool attribution** | [`.github/workflows/no-tool-attribution.yml`](../.github/workflows/no-tool-attribution.yml) | PRs to any protected branch |

### CI jobs

`ci.yml` runs three jobs in parallel on pull requests (two on `main` pushes):

1. **`tox (lint, backend, frontends)`**
   - PostgreSQL 15 service + test DB bootstrap (same as former Travis).
   - Python 3.11 + Node 20 (from `frontend-vue/.nvmrc`).
   - `tox -e lint,backend,frontend-streamlit,frontend-vue` (sequential — no `-p auto`).
   - The backend env runs `backend/tests/core/test_env_template.py`, which
     fails the build if any `Settings` field is missing from `.env.example`
     or any `SecretStr` field carries a real-looking uncommented value.

2. **`gitleaks (history + diff)`**
   - Installs a pinned `gitleaks` binary (8.30.x) and runs
     `gitleaks detect --log-opts="--all --reflog --no-merges" --exit-code 1`
     over the full history. Fails the build on any credential pattern hit.
   - Mirrors the local `tox -e secrets` env and the `.githooks/pre-push`
     gate — see [SECURITY.md](./SECURITY.md#secret-leak-defense-in-depth).

3. **`dependency review (new high/critical CVEs)`**
   - Runs only on pull requests using `actions/dependency-review-action@v4`.
   - Fails when a dependency change introduces a new advisory at `high` or
     `critical` severity. Existing alerts remain in the manual Dependabot
     alert queue; Dependabot auto-update PRs stay disabled.

4. **`no tool attribution`**
   - Runs on pull requests and scans the PR title, PR body, and commit messages
     with `.githooks/tool_attribution_guard.py --check`.
   - Fails before squash merge if an AI-tool authorship footer or generated-by
     line appears in metadata that local git hooks cannot sanitize.

### Docs site

`docs.yml` builds the MkDocs Material site with `mkdocs build --strict` on pull requests that touch docs, `mkdocs.yml`, or root license/notice/changelog files. On push to `main`, the same workflow deploys to GitHub Pages using `actions/deploy-pages`. Enable repository Pages source **GitHub Actions** before the first deploy. After the first successful merge, add the `Docs / build` job to the `Protect main` required checks.

### CD pipeline

On `qa` / `release` push (after branch promotion — see [RELEASE.md](./RELEASE.md)):

1. **CI gate** — reusable `ci.yml` workflow.
2. **Build Vue** — `npm ci` + `npm run build`; uploads `frontend-vue/dist` artifact.
3. **Deploy API** (optional) — Elastic Beanstalk when `EB_DEPLOY_ENABLED` is set.
4. **RAGAS gate** (optional) — `tox -e eval` on `release` when `RAGAS_QUALITY_GATE=1`.

Without AWS configuration, CD still validates builds; deploy and RAGAS jobs are skipped.

## Repository configuration

### Variables (`Settings` → `Secrets and variables` → `Actions` → **Variables**)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL_QA` | API base URL baked into QA frontend build |
| `VITE_API_URL_RELEASE` | API base URL for production frontend build |
| `EB_DEPLOY_ENABLED` | Set to `true` to run Elastic Beanstalk deploy job |
| `AWS_REGION` | e.g. `us-west-2` (optional; defaults to `us-west-2`) |
| `RAGAS_QUALITY_GATE` | Set to `1` to run `tox -e eval` on `release` (slow; needs judge LLM secrets in env) |

### Secrets

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | Deploy credentials |
| `AWS_SECRET_ACCESS_KEY` | Deploy credentials |
| `EB_APPLICATION_NAME` | Elastic Beanstalk application |
| `EB_ENVIRONMENT_NAME_QA` | QA environment name |
| `EB_ENVIRONMENT_NAME_RELEASE` | Production environment name |

For RAGAS on release, add Bedrock/judge keys as secrets or environment-scoped variables expected by `tox -e eval` (see [EVALUATION.md](./EVALUATION.md)).

### GitHub Environments

CD uses GitHub **environments** `qa` and `production` on deploy jobs (approval rules optional).

## Local parity

**Fast CI check** (Vue only, no Streamlit): `tox -e lint,backend,frontend-vue` — matches [PRODUCT_ROADMAP.md](./roadmap/PRODUCT_ROADMAP.md). Full CI parity includes `frontend-streamlit` as in `.github/workflows/ci.yml`.

```bash
tox -e lint,backend,frontend-streamlit,frontend-vue,docs,secrets
# Dependency review runs in GitHub only because it compares PR dependency diffs
```

The local `.githooks/pre-push` hook runs the same gitleaks scan before any
push leaves your machine — install with `./scripts/install-hooks.sh`.

## Branch flow

```text
PR → main     →  CI
promote → qa  →  CD (build + optional deploy)
promote → release  →  CD (+ optional RAGAS gate)
```

See [RELEASE.md](./RELEASE.md) for promotion commands and tagging.

## CI gotchas (frontend-vue)

| Issue | Fix |
|-------|-----|
| `nvm: command not found` on GHA | Tox skips `nvm use` when `CI=true`; Node comes from `setup-node` |
| `Cannot find module @rollup/rollup-linux-x64-gnu` | Use `HUSKY=0 npm ci` (not `--ignore-scripts`); `@rollup/rollup-*` pinned in `frontend-vue` optionalDependencies |
| Slow `frontend-vue` tox setup | Env no longer installs root `requirements.txt` — Node/npm only |

## Migrating from Travis

`.travis.yml` is removed. Enable Actions under repo **Settings → Actions** if disabled. Add branch protection: require **CI / tox** on `main`.
