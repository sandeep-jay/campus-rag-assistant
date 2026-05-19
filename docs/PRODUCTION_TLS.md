# Production HTTPS and HTTP/2

TLS termination and HTTP/2 for browsers are handled **outside this application** by infrastructure provisioned with **Terraform** (not in this repo).

## Request path

```
Browser --HTTPS (HTTP/2 or HTTP/1.1)--> ALB (ACM certificate)
       --HTTP/1.1--> Nginx on EB instance (port 80)
       --HTTP/1.1--> Uvicorn / FastAPI (127.0.0.1:8000)
```

- **HTTP/2** and **HTTP/1.1 fallback** are negotiated by the **Application Load Balancer** on the HTTPS listener. No application code is required.
- **Uvicorn** and **instance Nginx** stay on plain HTTP/1.1. Do not add `listen 443` or certificates on the EC2 instance unless you intentionally change the architecture.

## Terraform responsibilities

| Resource | Purpose |
|----------|---------|
| **ACM** | TLS certificate for the public hostname (same region as the ALB) |
| **Route 53** | `A` / `AAAA` alias to the Elastic Beanstalk environment load balancer |
| **ALB** | HTTPS listener on **443** with the ACM cert; optional HTTP **80** → redirect to **443** |
| **EB environment** | App deploy target; set env vars (see below) |

After apply, the public API base URL should look like: `https://api.example.com`.

## Application configuration (EB env / secrets)

Set on the EB environment (via Terraform or console):

| Variable | Example | Notes |
|----------|---------|--------|
| `AUTH_COOKIE_SECURE` | `true` | Required so `access_token` cookies are `Secure` over HTTPS |
| `AUTH_COOKIE_SAMESITE` | `lax` | Default; adjust if cross-site frontend |
| `OAUTH_REDIRECT_BASE_URL` | `https://api.example.com` | Must match the host users hit for OAuth callbacks |
| `FRONTEND_URL` | `https://app.example.com` | CORS and post-login redirect |
| `OAUTH_GOOGLE_CLIENT_ID` / `SECRET` | (from Google Cloud console) | Social login |
| `OAUTH_GITHUB_CLIENT_ID` / `SECRET` | (from GitHub OAuth app) | Social login |

## OAuth redirect URIs (provider consoles)

Register these against your **public HTTPS** API host:

- `https://<api-host>/api/auth/oauth/google/callback`
- `https://<api-host>/api/auth/oauth/github/callback`

## Verification

```bash
# HTTP/2 (if curl supports it)
curl -I --http2 https://<api-host>/api/health

# HTTP/1.1 fallback on same URL
curl -I --http1.1 https://<api-host>/api/health
```

## Optional instance Nginx tweaks

Only if cookies or redirects show `http` incorrectly, or SSE streams stall:

- Forward `X-Forwarded-Proto` from the ALB
- `proxy_buffering off` on `/api/` for streaming

See [`.ebextensions/00_ami.config`](../.ebextensions/00_ami.config) for the current Nginx template.


## Local OAuth development (Vite + GitHub)

OAuth `state` is stored in a **session cookie** on the browser host. The callback URL must use the **same hostname** as the tab where you clicked "Continue with GitHub".

### Checklist

| Item | Local example |
|------|----------------|
| Browser URL | `http://127.0.0.1:5173` (see [`scripts/run-frontend-vue.sh`](../scripts/run-frontend-vue.sh)) |
| `FRONTEND_URL` | `http://127.0.0.1:5173` |
| `OAUTH_REDIRECT_BASE_URL` | `http://127.0.0.1:5173` (Vue origin, **not** `:8000`) |
| GitHub OAuth app callback | `http://127.0.0.1:5173/api/auth/oauth/github/callback` |

`localhost` and `127.0.0.1` are different hosts for cookies. If the app runs on `127.0.0.1` but `OAUTH_REDIRECT_BASE_URL` uses `localhost`, GitHub redirects to `localhost` and the session cookie is missing → `MismatchingStateError`.

Restart the API after changing `.env`. Start a **new** OAuth flow after an error (do not refresh the callback URL).

### Symptom → fix

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| `MismatchingStateError` / `mismatching_state` | Host or port mismatch between OAuth start and callback | Align browser URL, `OAUTH_REDIRECT_BASE_URL`, and provider callback; use `127.0.0.1` consistently if Vite binds to it |
| Same error on refresh | OAuth `code`/`state` already used or session missing | Open `/login` and try GitHub again once |
| 503 on `/api/auth/oauth/github` | Missing `OAUTH_*` credentials | Set client id/secret in `.env` and restart API |


## Out of scope in this repo

- Terraform modules for Route 53, ACM, or ALB
- Local mkcert / dev HTTP/2 proxy (use plain `http://localhost:8000` for daily dev unless you add a proxy yourself)
