# CI/CD (GitHub Actions)

Automated checks replace Travis CI. **Tox** remains the source of truth for what runs locally and in CI.

## Workflows

| Workflow | File | Triggers |
|----------|------|----------|
| **CI** | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | Push to `main`; PRs to `main`, `qa`, `release`; optional manual `workflow_dispatch` |
| **CD** | [`.github/workflows/cd.yml`](../../.github/workflows/cd.yml) | Push to `qa` or `release`; manual `workflow_dispatch` |
| **Docs** | [`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) | PRs touching docs/site files; push to `main`; manual `workflow_dispatch` |
| **No tool attribution** | [`.github/workflows/no-tool-attribution.yml`](../../.github/workflows/no-tool-attribution.yml) | Pull requests; required on `main` by the `Protect main` ruleset |

### CI jobs

`ci.yml` runs three jobs in parallel on pull requests (two on `main` pushes):

1. **`tox (lint, backend, frontends)`**
   - PostgreSQL 15 service + test DB bootstrap (same as former Travis).
   - Python 3.11 + Node 20 (from `frontend-vue/.nvmrc`).
   - `tox -e lint,backend,agent-eval,frontend-streamlit,frontend-vue` (sequential — no `-p auto`).
   - The backend env runs `backend/tests/core/test_env_template.py`, which
     fails the build if any `Settings` field is missing from `.env.example`
     or any `SecretStr` field carries a real-looking uncommented value.
   - `agent-eval` runs the mock helpdesk trajectory dataset and gates
     over-ask, false-escalation, unnecessary-loop, HITL, and injection
     regressions without live provider credentials.

2. **`gitleaks (history + diff)`**
   - Installs a pinned `gitleaks` binary (8.30.x) and runs
     `gitleaks detect --log-opts="--all --reflog --no-merges" --exit-code 1`
     over the full history. Fails the build on any credential pattern hit.
   - Mirrors the local `tox -e secrets` env and the `.githooks/pre-push`
     gate — see [SECURITY.md](./security.md#secret-leak-defense-in-depth).

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

## Repository configuration

### Variables (`Settings` → `Secrets and variables` → `Actions` → **Variables**)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL_QA` | API base URL baked into QA frontend build |
| `VITE_API_URL_RELEASE` | API base URL for production frontend build |
| `EB_DEPLOY_ENABLED` | Set to `true` to run Elastic Beanstalk deploy job |
| `AWS_REGION` | e.g. `us-west-2` (optional; defaults to `us-west-2`) |
| `RAGAS_QUALITY_GATE` | Set to `1` to run `tox -e eval` on `release` (slow; needs judge LLM secrets in env) |
| `HELPDESK_ENABLED` | Enables ASK-mode helpdesk endpoints (`/summarize`, `/draft-ticket`, `/create-issue`) |
| `HELPDESK_AGENT_ENABLED` | Enables multi-turn AGENT-mode helpdesk LangGraph endpoints |

### Secrets

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | Deploy credentials |
| `AWS_SECRET_ACCESS_KEY` | Deploy credentials |
| `AWS_SESSION_TOKEN` | Optional temporary AWS credential for live eval/deploy sessions |
| `LANGSMITH_API_KEY` | Optional trace upload for `tox -e agent-eval-live` |
| `EB_APPLICATION_NAME` | Elastic Beanstalk application |
| `EB_ENVIRONMENT_NAME_QA` | QA environment name |
| `EB_ENVIRONMENT_NAME_RELEASE` | Production environment name |
| `GITHUB_TOKEN` (helpdesk) | Fine-grained PAT (`issues:write`) for the private demo repo issues are filed to |
| `GITHUB_REPO` | `owner/repo` of the private demo repo (e.g. `sandeep-jay/campus-helpdesk-demo`) |

For RAGAS on release, add Bedrock/judge keys as secrets or environment-scoped variables expected by `tox -e eval` (see [EVALUATION.md](../EVALUATION.md)).

### GitHub Environments

CD uses GitHub **environments** `qa` and `production` on deploy jobs (approval rules optional).

## Local parity

**Fast CI check** (Vue only, no Streamlit): `tox -e lint,backend,agent-eval,frontend-vue` — matches [PRODUCT_ROADMAP.md](../roadmap/PRODUCT_ROADMAP.md). Full CI parity includes `frontend-streamlit` as in `.github/workflows/ci.yml`.

```bash
tox -e lint,backend,agent-eval,frontend-streamlit,frontend-vue,secrets
# Optional: tox -e docs  (MkDocs strict build)
# dependency review (new high/critical CVEs) runs in GitHub only — compares PR dependency diffs
```

The local `.githooks/pre-push` hook runs the same gitleaks scan before any
push leaves your machine — install with `../../scripts/install-hooks.sh --global`
for commit-msg + pre-push protections on every repo, or omit `--global` for
repo-local hooks only.

## Branch flow

```text
PR → main     →  CI
promote → qa  →  CD (build + optional deploy)
promote → release  →  CD (+ optional RAGAS gate)
```

See [RELEASE.md](./release.md) for promotion commands and tagging.

## CI gotchas (frontend-vue)

| Issue | Fix |
|-------|-----|
| `nvm: command not found` on GHA | Tox skips `nvm use` when `CI=true`; Node comes from `setup-node` |
| `Cannot find module @rollup/rollup-linux-x64-gnu` | Use `HUSKY=0 npm ci` (not `--ignore-scripts`); `@rollup/rollup-*` pinned in `frontend-vue` optionalDependencies |
| Slow `frontend-vue` tox setup | Env no longer installs root `requirements.txt` — Node/npm only |

## Branch protection (rulesets)

The **`Protect main`** ruleset on the default branch requires these status checks before merge:

- `tox (lint, backend, frontends)`
- `gitleaks (history + diff)`
- `dependency review (new high/critical CVEs)`
- `no tool attribution`

A separate ruleset, **`Protect main, qa, release from deletion`**, blocks branch deletion on `main`, `qa`, and `release`.

Remote branches on `origin`: `main`, `qa`, `release`. Release tags: [`v1.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v1.0) (alias of `v0.1`), [`v2.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v2.0), [`v3.0.0`](https://github.com/sandeep-jay/campus-rag-assistant/releases/tag/v3.0.0). See [release-notes/](../release-notes/index.md) for high-level summaries and [RELEASE.md](./release.md) for the promotion process.
