# CI/CD (GitHub Actions)

Automated checks replace Travis CI. **Tox** remains the source of truth for what runs locally and in CI.

## Workflows

| Workflow | File | Triggers |
|----------|------|----------|
| **CI** | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | Push to `main`; PRs to `main`, `qa`, `release` |
| **CD** | [`.github/workflows/cd.yml`](../.github/workflows/cd.yml) | Push to `qa` or `release`; manual `workflow_dispatch` |

### CI job

1. PostgreSQL 15 service + test DB bootstrap (same as former Travis).
2. Python 3.11 + Node 20 (from `frontend-vue/.nvmrc`).
3. `tox -e lint,backend,frontend-streamlit,frontend-vue` (sequential — no `-p auto`)

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

```bash
tox -e lint,backend,frontend-streamlit,frontend-vue
```

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
