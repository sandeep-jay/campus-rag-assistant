"""Social OAuth login routes (Google, GitHub)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.app.core.auth_cookies import set_access_token_cookie
from backend.app.core.config_manager import settings
from backend.app.core.rate_limit import limit_login
from backend.app.core.security import create_access_token
from backend.app.db.database import get_db
from backend.app.services.db import DatabaseService
from backend.app.services.oauth_service import (
    enabled_oauth_providers,
    ensure_oauth_client,
    fetch_oauth_profile,
    oauth,
    oauth_callback_url,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_development() -> bool:
    env = (getattr(settings, 'APP_ENV', None) or settings.ENVIRONMENT or '').lower()
    return env in ('development', 'dev', 'local')


def _warn_oauth_redirect_host_mismatch(request: Request, provider: str) -> None:
    if not _is_development():
        return
    base = (settings.OAUTH_REDIRECT_BASE_URL or '').strip()
    if not base:
        return
    redirect_host = urlparse(base).hostname
    request_host = request.url.hostname
    if redirect_host and request_host and redirect_host != request_host:
        logger.warning(
            'OAuth redirect host "%s" does not match request host "%s" (provider=%s). '
            'Use the same host in the browser, OAUTH_REDIRECT_BASE_URL, and the provider '
            'callback URL (localhost ≠ 127.0.0.1).',
            redirect_host,
            request_host,
            provider,
        )


def _frontend_chat_url() -> str:
    base = settings.FRONTEND_URL.rstrip('/')
    return f'{base}/chat'


@router.get('/{provider}', dependencies=[Depends(limit_login)])
async def oauth_start(provider: str, request: Request) -> RedirectResponse:
    provider = provider.lower()
    if provider not in enabled_oauth_providers():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f'OAuth provider "{provider}" is not configured. '
                'Set OAUTH_* client id/secret and OAUTH_REDIRECT_BASE_URL in .env, then restart the API.'
            ),
        )
    ensure_oauth_client(provider)
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'OAuth client not configured: {provider}',
        )
    redirect_uri = oauth_callback_url(provider)
    _warn_oauth_redirect_host_mismatch(request, provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get('/{provider}/callback', dependencies=[Depends(limit_login)])
async def oauth_callback(
    provider: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    provider = provider.lower()
    if provider not in enabled_oauth_providers():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f'OAuth provider "{provider}" is not configured. '
                'Set OAUTH_* client id/secret and OAUTH_REDIRECT_BASE_URL in .env, then restart the API.'
            ),
        )
    ensure_oauth_client(provider)
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'OAuth client not configured: {provider}',
        )

    try:
        token = await client.authorize_access_token(request)
        profile = await fetch_oauth_profile(provider, token)
    except Exception as exc:
        logger.exception('OAuth callback failed for provider=%s', provider)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='OAuth sign-in failed',
        ) from exc

    db_service = DatabaseService(db)
    try:
        user = db_service.get_or_create_oauth_user(
            email=profile['email'],
            provider=provider,
            provider_subject=profile['provider_subject'],
            display_name=profile['display_name'],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    access_token = create_access_token(
        data={'sub': user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    redirect = RedirectResponse(url=_frontend_chat_url(), status_code=status.HTTP_302_FOUND)
    set_access_token_cookie(redirect, access_token)
    return redirect
