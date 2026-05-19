"""HTTP-only access_token cookie helpers."""

from fastapi import Response

from backend.app.core.config_manager import settings


def set_access_token_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path='/',
    )


def clear_access_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key='access_token',
        path='/',
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
