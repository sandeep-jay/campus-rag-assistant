"""Request correlation id middleware and logging filter."""

import logging
import uuid

import pytest
from starlette.testclient import TestClient

from backend.app.core.request_context import (
    REQUEST_ID_HEADER,
    RequestIdFilter,
    normalize_request_id,
    request_id_ctx,
)
from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_normalize_request_id_rejects_unsafe() -> None:
    rid = normalize_request_id('bad injection')
    uuid.UUID(rid)
    assert rid != 'bad injection'


def test_request_id_filter_uses_contextvar() -> None:
    token = request_id_ctx.set('corr-test-1')
    try:
        rec = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='hello',
            args=(),
            exc_info=None,
        )
        assert RequestIdFilter().filter(rec)
        assert rec.request_id == 'corr-test-1'
    finally:
        request_id_ctx.reset(token)


def test_health_returns_x_request_id(client: TestClient) -> None:
    response = client.get('/api/health')
    assert response.status_code == 200
    rid = response.headers.get('x-request-id')
    assert rid
    uuid.UUID(rid)


def test_echoes_valid_client_request_id(client: TestClient) -> None:
    sent = '550e8400-e29b-41d4-a716-446655440000'
    response = client.get('/api/health', headers={'X-Request-ID': sent})
    assert response.status_code == 200
    assert response.headers.get('x-request-id') == sent.lower()


def test_invalid_request_id_replaced(client: TestClient) -> None:
    response = client.get('/api/health', headers={'X-Request-ID': 'bad\ninjection'})
    assert response.status_code == 200
    got = response.headers.get('x-request-id')
    assert got is not None
    assert '\n' not in got
    uuid.UUID(got)


def test_request_id_header_constant() -> None:
    assert REQUEST_ID_HEADER == 'X-Request-ID'
