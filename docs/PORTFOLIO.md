# Portfolio repository guide

How to publish this codebase as a **standalone portfolio project** (no GitHub fork badge), while keeping UC license/attribution and optional ties to the Berkeley upstream repo.

---

## Context

- The system was **authored for UC Berkeley ETS** (original *Chabot*).
- This line is an **independent portfolio continuation** (Vue, providers, eval, LangGraph roadmap, etc.).
- **Not** an official or endorsed UC Berkeley product.

---

## Choose your Git strategy

| Approach | Fork badge | History | Best for |
|----------|------------|---------|----------|
| **A. New repo + copy + `git init`** | None | Fresh | Cleanest portfolio story |
| **B. Leave fork network** | Removed on same URL | Kept | Already pushed to your fork |
| **C. New repo + push existing history** | None | Kept | Want full timeline |

**Recommended:** **A** if most work is still uncommitted locally; **B** if you already use `github.com/you/chabot` with many pushes.

---

## A. New repository (recommended)

### 1. Create GitHub repo

- **New repository** — do **not** click Fork on `ets-berkeley-edu/chabot`.
- Empty repo (no README/license on GitHub — you push yours).

### 2. Copy tree

```bash
mkdir -p ~/Workbench/Projects/<your-portfolio-name>
cd /path/to/current/chabot

rsync -a --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.tox' \
  --exclude 'frontend-vue/node_modules' \
  --exclude 'frontend-vue/coverage' \
  --exclude 'frontend-vue/playwright-report' \
  --exclude 'frontend-vue/test-results' \
  --exclude 'frontend-vue/e2e/.auth' \
  --exclude 'frontend-vue/.env.local' \
  --exclude '.env' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  . ~/Workbench/Projects/<your-portfolio-name>/
```

### 3. Initialize Git and commit

```bash
cd ~/Workbench/Projects/<your-portfolio-name>
git init
git branch -M main
```

Commit in order per [changelog/PR_PLAN.md](./EXECUTION_PLAN.md) (hygiene → tooling → … → docs).

### 4. Push

```bash
git remote add origin git@github.com:<you>/<your-portfolio-name>.git
git push -u origin main
```

### 5. Old clone

Keep or archive the Berkeley-remote clone; do not use it as daily `origin` unless contributing upstream.

---

## B. Detach existing fork on GitHub

1. Open **your** fork on GitHub (under your user, not `ets-berkeley-edu`).
2. **Settings** → **Danger zone** → **Leave fork network**.
3. Confirm.

Same URL; **"forked from"** badge disappears. Update README for portfolio framing.

Optional local remote:

```bash
git remote add upstream https://github.com/ets-berkeley-edu/chabot.git   # fetch only
git remote -v
# origin → your repo
```

---

## C. Rename and rebrand (any approach)

| Layer | Action |
|-------|--------|
| GitHub repo name | e.g. `campus-rag-assistant` |
| README title | New name + attribution paragraph |
| Vue `index.html` / header | Display name |
| Internal API paths | Optional; `/api/chat` can stay for stability |

Do **not** remove root `LICENSE` or Regents headers in existing source files without UC OTL guidance.

### README attribution template

```markdown
# Campus RAG Assistant

Full-stack RAG chatbot with grounded answers and source citations.

Originally developed as *Chabot* for UC Berkeley ETS. This repository is an
independent portfolio continuation by [Your Name]. Not affiliated with or
endorsed by the University of California, Berkeley.
```

---

## License and IP (summary)

- Root **LICENSE** (UC Regents) applies to Berkeley-era and derived code.
- **Renaming or morphing** does not remove license obligations.
- **Portfolio / educational** public GitHub is typically consistent with the license if notice is preserved.
- **Commercial use** requires UC OTL — see LICENSE file.
- For certainty about portfolio hosting or new modules you own, contact ETS or [UC OTL](http://ipira.berkeley.edu/industry-info).

---

## Contributing back to Berkeley (optional)

You do **not** need to PR portfolio work (Vue, LangGraph) to ETS.

When useful:

- Cherry-pick **backend-only** fixes onto a branch from `upstream/main`.
- Open a **small PR** to `ets-berkeley-edu/chabot` — not a merge of your entire portfolio `main`.

Keep a separate clone or `upstream` remote for that workflow.

---

## Checklist before first public push

- [ ] No `.env`, `.env.local`, or real API keys
- [ ] `LICENSE` present; copyright headers intact
- [ ] README: mock quick start (`RAG_FORCE_MOCK` / mock providers)
- [ ] GitHub repo created with **New**, not Fork (or fork detached)
- [ ] `git remote -v` → only your portfolio `origin` for daily work
- [ ] Roadmap: [docs/roadmap/PORTFOLIO_PHASED_ROADMAP.md](./roadmap/PORTFOLIO_PHASED_ROADMAP.md)
