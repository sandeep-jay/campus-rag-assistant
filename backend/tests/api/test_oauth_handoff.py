"""OAuth handoff code exchange (dev cross-port login)."""

from datetime import timedelta

from fastapi import status
from starlette.testclient import TestClient

from backend.app.core.config_manager import settings
from backend.app.core.security import create_access_token
from backend.app.services.oauth_handoff import consume_handoff_code, create_handoff_code


def test_oauth_handoff_exchange_sets_cookie(client: TestClient) -> None:
    jwt = create_access_token(
        data={'sub': 'handoff-user'},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    code = create_handoff_code(jwt)
    response = client.post('/api/auth/oauth/handoff', json={'code': code})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['status'] == 'ok'
    # httponly cookie
    assert 'access_token' in response.cookies
    assert consume_handoff_code(code) is None  # one-time use


def test_oauth_handoff_invalid_code(client: TestClient) -> None:
    response = client.post('/api/auth/oauth/handoff', json={'code': 'invalid-code-not-in-store'})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
