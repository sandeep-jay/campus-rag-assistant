# Security

Dependency audit, static analysis, and production hardening for Campus RAG Assistant.

## Regular checks

From repo root (project `venv` recommended):

```bash
./venv/bin/python -m pip install pip-audit bandit
./venv/bin/pip-audit
./venv/bin/bandit -r backend/app -ll
cd frontend-vue && npm audit

# Full-history credential scan (gitleaks must be installed locally)
tox -e secrets
```

Run `pip install -r requirements.txt` before `pip-audit` so the environment
matches production deps. Install `gitleaks` once per workstation:

```bash
brew install gitleaks         # macOS
sudo apt-get install gitleaks # Debian / Ubuntu
```

## Production hardening

| Item | Dev default | Production |
|------|-------------|------------|
| `SECRET_KEY` | sentinel `change-me-in-production` (SecretStr) | Strong random secret via env or `secrets_dir` |
| `BACKEND_CORS_ORIGINS` | `['*']` | Explicit frontend origin(s) only |
| `.env` | Local secrets (gitignored) | Use secrets manager / EB env / mounted file |
| OAuth | `127.0.0.1` alignment | HTTPS + registered callbacks — [PRODUCTION_TLS.md](./PRODUCTION_TLS.md) |
| `WEB_RESEARCH_ENABLED` | `false` | Enable only with Tavily key and policy review |

## Secret-leak defense in depth

Five independent layers must each pass before a credential can reach the
public git server. Any one of them is sufficient to catch a leak; together
they make accidental disclosure vanishingly unlikely.

| # | Layer | Where | What it does |
|---|---|---|---|
| 1 | **`.gitignore` catch-all** | `.gitignore` | `.env*` (with `.env.example` / `.env.test` whitelisted) plus pattern blocks for TLS/SSH keys, AWS/GCP/Azure credentials, `secrets/`, `credentials/`, `*.tfvars`, etc. |
| 2 | **CI guard for env template** | `backend/tests/core/test_env_template.py` | Every `Settings` field must appear in `.env.example`; no `SecretStr` field may carry a real-looking uncommented value. Fails `tox -e backend`. |
| 3 | **Local `pre-push` gitleaks hook** | `.githooks/pre-push` | Blocks `git push` if `gitleaks detect` finds a credential in the commits being uploaded. Wired by `./scripts/install-hooks.sh` (and `--global` for every repo on the workstation). |
| 4 | **CI `secrets-scan` job** | `.github/workflows/ci.yml` (job `secrets-scan`) + `tox -e secrets` | Runs `gitleaks detect --log-opts="--all --reflog --no-merges"` on every PR and push to `main`. Fails the build on any finding. |
| 5 | **GitHub Push Protection** | repo Settings → Code security & analysis | Even `git push --no-verify` is rejected by GitHub if the push contains a known-provider credential pattern (AWS, Google, Slack, Stripe, GitHub PATs, …). Secret Scanning, Push Protection, and Dependabot **alerts** are enabled on this repo. Dependabot **security updates** (auto-PRs that bump versions) are intentionally left **off** — they were observed to break the build mid-sprint, so vulnerabilities are triaged manually from the alert queue instead. |

### How to run gitleaks locally

```bash
# Catch a leak in the commits you are about to push (also enforced by the hook)
gitleaks detect --no-banner --redact --log-opts="@{u}..HEAD --no-merges"

# Full historical sweep (matches CI)
tox -e secrets

# Scan staged-but-uncommitted changes (catches a leak before you even commit)
gitleaks protect --staged --no-banner --redact
```

If `gitleaks` is missing, the local `pre-push` hook warns and lets the push
through — CI still enforces the check, so a missing local binary cannot leak
to origin.

### Bypass policy

Use `git push --no-verify` only after a manual review confirms the gitleaks
finding is a false positive. If you ever need to bypass, follow up by adding
the specific allowlist rule to a `.gitleaks.toml` rather than relying on
`--no-verify` long-term.

## Secrets management

Configuration loads in this precedence order (later wins):

1. Code defaults in `backend/app/config/default.py` (no real secrets — sentinels only).
2. `.env.{APP_ENV}` (e.g. `.env.test`) and `.env` at repo root (both gitignored).
3. `APP_LOCAL_CONFIGS=<dir>` for an out-of-tree override (gitignored by convention).
4. Process environment variables (set by your orchestrator).
5. **Docker / Kubernetes secret files** mounted at the path given by
   `BaseSettings.model_config.secrets_dir`. Each file's name maps to a setting
   field (e.g. `/run/secrets/SECRET_KEY`). Enable in prod by setting
   `secrets_dir` in `DefaultSettings.model_config` or via a deploy-wrapper
   environment variable.

### What is treated as a secret

The following `Settings` fields are typed as `pydantic.SecretStr`. They are
masked in `repr`, logs, exceptions, and `model_dump_json` output, and the
cleartext is only read at the boundary that needs it via
`.get_secret_value()`:

- `SECRET_KEY` (JWT signing — **must** be rotated and provisioned per
  environment; the in-tree default is a sentinel that startup checks reject
  in production).
- `AWS_SECRET_ACCESS_KEY` (when not using instance profiles / IRSA).
- `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_KEY`.
- `OAUTH_GOOGLE_CLIENT_SECRET`, `OAUTH_GITHUB_CLIENT_SECRET`.
- `LANGCHAIN_API_KEY`, `TAVILY_API_KEY`.

### Production checklist

- Provision secrets through your platform's secret store (AWS Secrets Manager,
  AWS SSM Parameter Store with `SecureString`, Azure Key Vault, Vault, etc.).
  Inject as environment variables or mount as files into `secrets_dir`.
- Prefer **instance roles** (EC2/EKS instance profiles, IRSA) over static AWS
  keys — leave `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` unset.
- Rotate `SECRET_KEY` on a schedule (and any time it may have leaked); JWTs
  signed with the old key will be invalidated, which is the desired behaviour.
- Keep `.env.example` placeholder-only. Two CI guards enforce this:
  `backend/tests/core/test_env_template.py` (no real-looking values for any
  `SecretStr` field, every field documented) and the `secrets-scan` job
  (gitleaks on full history). The local `.githooks/pre-push` hook runs the
  same gitleaks scan before a push leaves your machine.
- The pydantic settings model uses `extra='ignore'`, so typos in env var names
  are dropped instead of silently attached. In CI/prod you can switch to
  `extra='forbid'` to surface them as errors.
- Never commit `.env`, `.env.bak*`, `.env.*.local`, `*.pem`, `*.tfvars`,
  AWS/GCP credential files, or anything under `secrets/` — all are
  pattern-blocked in `.gitignore`.


### Dependency alert policy

Dependabot **alerts** are enabled, but Dependabot **security updates** (automatic
version-bump PRs) are disabled because they have broken the build during active
work. Triage alerts manually from the GitHub Security tab, batch related updates
into reviewable PRs, and let CI validate them. New PRs are guarded by the
`dependency review (new high/critical CVEs)` job, which fails if a dependency
change introduces a new high or critical advisory.

### If a secret leaks

1. **Rotate the credential at the provider immediately.** Treat any value
   that ever touched a public branch as compromised even if you rewrite
   history — crawlers and forks may already have it.
2. Invalidate downstream sessions (rotate `SECRET_KEY` if a JWT secret leaked).
3. Check the **GitHub Secret Scanning alerts** page for the repo; GitHub may
   already have notified the provider (AWS, GitHub, Stripe, …) and triggered
   automatic revocation.
4. Force-push history removal (`git filter-repo`) only as a last resort and
   only after step 1 — rewriting history doesn't make a leaked key safer, it
   only hides it from casual viewers.

## Dependency policy (2026-05-18)

Runtime bumps on `feature/security-deps`:

- **FastAPI / Starlette** — `fastapi>=0.115` (Starlette CVE fixes)
- **Auth** — `python-jose>=3.4`, `PyJWT>=2.12`
- **Uploads** — `python-multipart>=0.0.27`
- **HTTP** — `requests>=2.32.4`, `urllib3>=2.2`, `httpx>=0.27` (LangGraph 0.2.x)
- **LangGraph** — `langgraph==0.2.76`, `langgraph-checkpoint==2.0.26`

Dev-only packages (Streamlit, RAGAS, old pip/setuptools) may still appear in audits; track separately.

## Reporting

Open a GitHub security advisory or contact the maintainer in [README](../README.md).
