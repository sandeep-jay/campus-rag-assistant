"""Social OAuth client registration and profile parsing (Google, GitHub)."""

from __future__ import annotations

import re
from typing import Any

from authlib.integrations.starlette_client import OAuth

from backend.app.core.config_manager import settings

oauth = OAuth()

_USERNAME_SAFE = re.compile(r'[^a-zA-Z0-9_]+')


def _redirect_base() -> str:
    base = (settings.OAUTH_REDIRECT_BASE_URL or '').rstrip('/')
    if not base:
        raise ValueError('OAUTH_REDIRECT_BASE_URL is not configured')
    return base


def oauth_callback_url(provider: str) -> str:
    return f'{_redirect_base()}{settings.API_V1_STR}/auth/oauth/{provider}/callback'


def enabled_oauth_providers() -> list[str]:
    configured = {
        p.strip().lower()
        for p in (settings.OAUTH_ENABLED_PROVIDERS or '').split(',')
        if p.strip()
    }
    available: list[str] = []
    if 'google' in configured and settings.OAUTH_GOOGLE_CLIENT_ID and settings.OAUTH_GOOGLE_CLIENT_SECRET:
        available.append('google')
    if 'github' in configured and settings.OAUTH_GITHUB_CLIENT_ID and settings.OAUTH_GITHUB_CLIENT_SECRET:
        available.append('github')
    return available


_REGISTERED: set[str] = set()


def ensure_oauth_client(provider: str) -> None:
    """Register Authlib client on first use (after settings/.env are loaded)."""
    if provider in _REGISTERED:
        return
    if provider == 'google':
        if not (settings.OAUTH_GOOGLE_CLIENT_ID and settings.OAUTH_GOOGLE_CLIENT_SECRET):
            return
        oauth.register(
            name='google',
            client_id=settings.OAUTH_GOOGLE_CLIENT_ID,
            client_secret=settings.OAUTH_GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )
    elif provider == 'github':
        if not (settings.OAUTH_GITHUB_CLIENT_ID and settings.OAUTH_GITHUB_CLIENT_SECRET):
            return
        oauth.register(
            name='github',
            client_id=settings.OAUTH_GITHUB_CLIENT_ID,
            client_secret=settings.OAUTH_GITHUB_CLIENT_SECRET,
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )
    _REGISTERED.add(provider)


def suggest_username(email: str, provider: str, provider_subject: str) -> str:
    local = email.split('@')[0]
    base = _USERNAME_SAFE.sub('_', local).strip('_') or 'user'
    base = base[:40]
    suffix = provider_subject[:12]
    return f'{base}_{provider}_{suffix}'[:64]


async def fetch_oauth_profile(provider: str, token: dict[str, Any]) -> dict[str, str]:
    if provider == 'google':
        userinfo = token.get('userinfo')
        if not userinfo:
            raise ValueError('Google OAuth response missing userinfo')
        email = userinfo.get('email')
        if not email:
            raise ValueError('Google account has no email')
        return {
            'email': email,
            'provider_subject': userinfo['sub'],
            'display_name': userinfo.get('name') or email.split('@')[0],
        }

    if provider == 'github':
        client = oauth.github
        resp = await client.get('user', token=token)
        resp.raise_for_status()
        profile = resp.json()
        subject = str(profile['id'])
        email = profile.get('email')
        if not email:
            emails_resp = await client.get('user/emails', token=token)
            emails_resp.raise_for_status()
            for item in emails_resp.json():
                if item.get('primary') and item.get('verified'):
                    email = item['email']
                    break
            if not email:
                for item in emails_resp.json():
                    if item.get('verified'):
                        email = item['email']
                        break
        if not email:
            raise ValueError('GitHub account has no verified email')
        return {
            'email': email,
            'provider_subject': subject,
            'display_name': profile.get('login') or profile.get('name') or email.split('@')[0],
        }

    raise ValueError(f'Unsupported OAuth provider: {provider}')
