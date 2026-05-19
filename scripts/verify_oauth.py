#!/usr/bin/env python3
"""Verify OAuth implementation (run: python scripts/verify_oauth.py)."""
from __future__ import annotations

import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env.test')
load_dotenv(ROOT / '.env', override=True)
os.environ.setdefault('LANGCHAIN_TRACING_V2', 'false')
os.environ.setdefault('LANGSMITH_TRACING', 'false')
os.environ.setdefault('RATE_LIMIT_ENABLED', 'false')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ['DATABASE_URL'] = (
    f"postgresql://{os.environ.get('POSTGRES_USER', 'chatbot')}:"
    f"{os.environ.get('POSTGRES_PASSWORD', 'chatbot')}@"
    f"{os.environ.get('POSTGRES_HOST', 'localhost')}:"
    f"{os.environ.get('POSTGRES_PORT', '5432')}/"
    f"{os.environ.get('POSTGRES_DB', 'chatbot_test')}"
)

from fastapi import Response
from sqlalchemy.orm import sessionmaker

from backend.app.api import oauth_routes
from backend.app.core.auth_cookies import set_access_token_cookie
from backend.app.core.config_manager import settings
from backend.app.core.security import create_access_token
from backend.app.db.database import Base, engine
from backend.app.services.db import DatabaseService
from backend.app.services.oauth_service import (
    enabled_oauth_providers,
    oauth_callback_url,
    suggest_username,
)


def main() -> int:
    failures: list[str] = []

    def check(ok: bool, msg: str) -> None:
        if not ok:
            failures.append(msg)

    check(enabled_oauth_providers() == [], 'no providers without secrets')
    try:
        oauth_callback_url('google')
        check(False, 'callback requires OAUTH_REDIRECT_BASE_URL')
    except ValueError:
        pass
    settings.OAUTH_REDIRECT_BASE_URL = 'http://localhost:8000'
    check(
        oauth_callback_url('google') == 'http://localhost:8000/api/auth/oauth/google/callback',
        'callback URL',
    )
    check('google' in suggest_username('a@b.com', 'google', 'sub1'), 'username')

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    db = DatabaseService(session)
    oauth_email = f'oauth-{uuid.uuid4().hex[:8]}@example.com'
    oauth_sub = f'gid-{uuid.uuid4().hex[:8]}'
    user = db.get_or_create_oauth_user(oauth_email, 'google', oauth_sub, 'OAuth')
    check(user.hashed_password is None and user.auth_provider == 'google', 'oauth user')
    check(
        db.get_or_create_oauth_user(oauth_email, 'google', oauth_sub, 'OAuth').id == user.id,
        'idempotent',
    )
    uid = uuid.uuid4().hex[:8]
    db.create_user(f'local_{uid}', f'local_{uid}@example.com', 'testpassword123')
    check(db.authenticate_user(f'local_{uid}', 'testpassword123') is not None, 'local auth')
    try:
        db.get_or_create_oauth_user(f'local_{uid}@example.com', 'google', 'other', 'x')
        check(False, 'email conflict')
    except ValueError:
        pass
    session.close()

    paths = [getattr(r, 'path', '') for r in oauth_routes.router.routes]
    check('/{provider}' in paths and '/{provider}/callback' in paths, 'oauth routes')

    resp = Response()
    set_access_token_cookie(resp, create_access_token({'sub': 'u'}, timedelta(minutes=5)))
    cookie = next(v for k, v in resp.raw_headers if k == b'set-cookie')
    check(b'httponly' in cookie.lower(), 'httponly cookie')

    if failures:
        print('FAILED:', *failures, sep='\n  ')
        return 1
    print('OK: OAuth verification passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
