#!/usr/bin/env python3
"""Register accounts from users.json against the running API (stdlib only).

Uses BASE_URL (default http://127.0.0.1:8000). Safe to re-run: treats
already-registered responses as success.

Registers use ``{username}@example.com`` (Pydantic EmailStr rejects ``*.local``).

Spacing between calls avoids ``auth-register`` rate limits (see
``RATE_LIMIT_REGISTER_PER_MINUTE``).

Example::

    ./scripts/run-backend-loadtest.sh
    python3 load-tests/seed_users.py
    k6 run --env BASE_URL=http://127.0.0.1:8000 load-tests/k6-auth-chat-session.js
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _register(base: str, username: str, email: str, password: str) -> tuple[int, str]:
    body = json.dumps({"username": username, "email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{base}/api/auth/register",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def main() -> int:
    base = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    pace = float(os.environ.get("SEED_REGISTER_PACE_SECONDS", "7"))
    path = _ROOT / "users.json"
    users = json.loads(path.read_text(encoding="utf-8"))["users"]
    failures = 0
    for i, u in enumerate(users):
        if i:
            time.sleep(pace)
        username = u["username"]
        password = u["password"]
        email = f"{username}@example.com"

        code, body = _register(base, username, email, password)
        if code == 429:
            wait = pace * 2
            print(f"rate limited on {username}; sleeping {wait}s then retrying once", file=sys.stderr)
            time.sleep(wait)
            code, body = _register(base, username, email, password)

        if code == 200:
            print(f"registered {username}")
            continue
        if code == 400 and (
            "already registered" in body.lower()
            or "Username already" in body
            or "Email already" in body
        ):
            print(f"exists {username}")
            continue
        print(f"FAILED {username} HTTP {code}: {body[:300]}", file=sys.stderr)
        failures += 1
    if failures:
        print(f"Done with {failures} failure(s).", file=sys.stderr)
        return 1
    print(f"OK: {len(users)} load-test user(s) ready at {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
