"""Social OAuth login routes (Google, GitHub)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlparse

from authlib.integrations.base_client.errors import MismatchingStateError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.auth_cookies import set_access_token_cookie
from backend.app.core.config_manager import settings
from backend.app.core.rate_limit import limit_login
from backend.app.core.security import create_access_token
from backend.app.db.database import get_db
from backend.app.services.db import DatabaseService
from backend.app.services.oauth_handoff import consume_handoff_code, create_handoff_code
from backend.app.services.oauth_service import (
    enabled_oauth_providers,
    ensure_oauth_client,
    fetch_oauth_profile,
    oauth,
    oauth_callback_url,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class OAuthHandoffRequest(BaseModel):
    code: str = Field(min_length=16, max_length=256)


def _is_development() -> bool:
    env = (settings.APP_ENV or '').lower()
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
            'OAuth should hit the API directly (port 8000); see OAUTH_REDIRECT_BASE_URL.',
            redirect_host,
            request_host,
            provider,
        )


def _frontend_handoff_url(code: str) -> str:
    base = settings.FRONTEND_URL.rstrip('/')
    return f'{base}/oauth/handoff?code={code}'


def _frontend_login_url(error: str | None = None) -> str:
    base = settings.FRONTEND_URL.rstrip('/')
    if error:
        return f'{base}/login?oauth_error={error}'
    return f'{base}/login'


@router.post('/handoff', dependencies=[Depends(limit_login)])
async def oauth_handoff_complete(body: OAuthHandoffRequest) -> JSONResponse:
    """Exchange a one-time OAuth handoff code for an access_token cookie (Vue on :5173)."""
    access_token = consume_handoff_code(body.code)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid or expired handoff code',
        )
    response = JSONResponse({'status': 'ok'})
    set_access_token_cookie(response, access_token)
    return response


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
    except MismatchingStateError:
        logger.warning(
            'OAuth state mismatch for provider=%s (stale session, refresh, or host mismatch)',
            provider,
        )
        return RedirectResponse(
            url=_frontend_login_url('state_mismatch'),
            status_code=status.HTTP_302_FOUND,
        )
    except Exception:
        logger.exception('OAuth callback failed for provider=%s', provider)
        return RedirectResponse(
            url=_frontend_login_url('failed'),
            status_code=status.HTTP_302_FOUND,
        )

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
    handoff = create_handoff_code(access_token)
    return RedirectResponse(url=_frontend_handoff_url(handoff), status_code=status.HTTP_302_FOUND)
