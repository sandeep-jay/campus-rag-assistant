"""Tests for the helpdesk escalation router and supporting services."""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
from starlette.testclient import TestClient

from backend.app.core.config_manager import settings
from backend.app.services.helpdesk import github as github_module


@pytest.fixture()
def enable_helpdesk(monkeypatch):
    monkeypatch.setattr(settings, 'HELPDESK_ENABLED', True)
    monkeypatch.setattr(settings, 'RAG_FORCE_MOCK', True)
    monkeypatch.setattr(settings, 'LLM_PROVIDER', 'mock')
    monkeypatch.setattr(settings, 'GITHUB_TOKEN', _SecretLike('demo-token'))
    monkeypatch.setattr(settings, 'GITHUB_REPO', 'demo-org/demo-repo')
    monkeypatch.setattr(settings, 'GITHUB_DEFAULT_LABELS', 'it-helpdesk,demo')
    monkeypatch.setattr(settings, 'HELPDESK_DEDUP_WINDOW_SECONDS', 300)
    github_module._dedup_cache._store.clear()


class _SecretLike:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


@pytest.fixture()
def disable_helpdesk(monkeypatch):
    monkeypatch.setattr(settings, 'HELPDESK_ENABLED', False)


def test_summarize_returns_404_when_disabled(client: TestClient, test_user_token: str, disable_helpdesk):
    response = client.post(
        '/api/helpdesk/summarize',
        json={'conversation': []},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 404


def test_draft_ticket_returns_404_when_disabled(client: TestClient, test_user_token: str, disable_helpdesk):
    response = client.post(
        '/api/helpdesk/draft-ticket',
        json={'conversation': []},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 404


def test_summarize_requires_auth(client: TestClient, enable_helpdesk):
    response = client.post('/api/helpdesk/summarize', json={'conversation': []})
    assert response.status_code == 401


def test_draft_ticket_requires_auth(client: TestClient, enable_helpdesk):
    response = client.post('/api/helpdesk/draft-ticket', json={'conversation': []})
    assert response.status_code == 401


def test_create_issue_requires_auth(client: TestClient, enable_helpdesk):
    response = client.post('/api/helpdesk/create-issue', json={'draft': _draft()})
    assert response.status_code == 401


def test_summarize_returns_mock_recap(client: TestClient, test_user_token: str, enable_helpdesk):
    payload = {
        'conversation': [
            {'role': 'user', 'content': 'Oracle Financials 403 on budget reports'},
            {'role': 'assistant', 'content': "I couldn't find information about this."},
        ]
    }
    response = client.post(
        '/api/helpdesk/summarize',
        json=payload,
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    summary_obj = response.json()['summary']
    assert isinstance(summary_obj['summary'], str)
    assert summary_obj['summary'].strip()
    assert 'severity' not in summary_obj
    assert 'category' not in summary_obj


def test_draft_ticket_returns_mock_draft(client: TestClient, test_user_token: str, enable_helpdesk):
    payload = {
        'conversation': [
            {'role': 'user', 'content': 'Oracle Financials 403 on budget reports'},
            {'role': 'assistant', 'content': "I couldn't find information about this."},
        ]
    }
    response = client.post(
        '/api/helpdesk/draft-ticket',
        json=payload,
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    draft = response.json()['draft']
    assert draft['title']
    assert draft['severity'] in {'low', 'medium', 'high', 'critical'}
    assert draft['category'] in {'network', 'access', 'application', 'hardware', 'account', 'other'}
    assert draft['impact'] in {'Single user', 'Team', 'Campus-wide'}


def test_draft_ticket_redacts_email_before_calling_llm(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    captured: dict[str, list[dict]] = {}

    async def _fake_ainvoke(llm, prompt):
        captured['prompt'] = prompt

        class _Resp:
            content = json.dumps(
                {
                    'title': 'redacted-email issue',
                    'description': 'User cannot log in.',
                    'severity': 'medium',
                    'category': 'access',
                    'steps_to_reproduce': None,
                    'impact': 'Single user',
                }
            )

        return _Resp()

    class _FakeProvider:
        is_mock = False

        def get_llm(self):
            return object()

    payload = {
        'conversation': [
            {'role': 'user', 'content': 'login fails for me at alice@example.com'},
            {'role': 'assistant', 'content': "I couldn't find information."},
        ]
    }
    with (
        patch('backend.app.services.helpdesk.agent.get_llm_provider', return_value=_FakeProvider()),
        patch('backend.app.services.helpdesk.agent._ainvoke', _fake_ainvoke),
    ):
        response = client.post(
            '/api/helpdesk/draft-ticket',
            json=payload,
            headers={'Authorization': f'Bearer {test_user_token}'},
        )
    assert response.status_code == 200, response.text
    sent = captured['prompt'][-1]['content']
    assert 'alice@example.com' not in sent
    assert '[REDACTED]' in sent


def test_summarize_redacts_email_before_calling_llm(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    captured: dict[str, list[dict]] = {}

    async def _fake_ainvoke(llm, prompt):
        captured['prompt'] = prompt

        class _Resp:
            content = 'The user reported login problems.\n\n- KB returned no answer.'

        return _Resp()

    class _FakeProvider:
        is_mock = False

        def get_llm(self):
            return object()

    payload = {
        'conversation': [
            {'role': 'user', 'content': 'login fails for me at alice@example.com'},
            {'role': 'assistant', 'content': "I couldn't find information."},
        ]
    }
    with (
        patch('backend.app.services.helpdesk.agent.get_llm_provider', return_value=_FakeProvider()),
        patch('backend.app.services.helpdesk.agent._ainvoke', _fake_ainvoke),
    ):
        response = client.post(
            '/api/helpdesk/summarize',
            json=payload,
            headers={'Authorization': f'Bearer {test_user_token}'},
        )
    assert response.status_code == 200, response.text
    sent = captured['prompt'][-1]['content']
    assert 'alice@example.com' not in sent
    assert '[REDACTED]' in sent


def _draft() -> dict:
    return {
        'title': 'Cannot access Oracle Financials',
        'description': 'A 403 error blocks budget report retrieval.',
        'severity': 'high',
        'category': 'access',
        'steps_to_reproduce': None,
        'impact': 'Team',
    }


def test_create_issue_calls_github_and_dedups(client: TestClient, test_user_token: str, enable_helpdesk):
    calls = {'count': 0}

    def _handler(request: httpx.Request) -> httpx.Response:
        calls['count'] += 1
        assert request.headers['Authorization'].startswith('token ')
        body = json.loads(request.content.decode('utf-8'))
        assert 'Severity' in body['body']
        return httpx.Response(
            201,
            json={'html_url': 'https://github.com/demo-org/demo-repo/issues/1', 'number': 1},
        )

    transport = httpx.MockTransport(_handler)

    async def _patched_create(draft_obj, *, user_id, transport=None):
        from backend.app.services.helpdesk.github import create_github_issue

        return await create_github_issue(draft_obj, user_id=user_id, transport=transport)

    with patch(
        'backend.app.api.helpdesk.create_github_issue',
        lambda d, *, user_id: _patched_create(d, user_id=user_id, transport=transport),
    ):
        first = client.post(
            '/api/helpdesk/create-issue',
            json={'draft': _draft()},
            headers={'Authorization': f'Bearer {test_user_token}'},
        )
        second = client.post(
            '/api/helpdesk/create-issue',
            json={'draft': _draft()},
            headers={'Authorization': f'Bearer {test_user_token}'},
        )

    assert first.status_code == 200, first.text
    assert first.json()['issue_number'] == 1
    assert first.json()['deduplicated'] is False
    assert second.status_code == 200
    assert second.json()['deduplicated'] is True
    assert calls['count'] == 1


def test_create_issue_github_error_returns_502(client: TestClient, test_user_token: str, enable_helpdesk):
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={'message': 'Forbidden'})

    transport = httpx.MockTransport(_handler)

    async def _patched_create(draft_obj, *, user_id, transport=None):
        from backend.app.services.helpdesk.github import create_github_issue

        return await create_github_issue(draft_obj, user_id=user_id, transport=transport)

    with patch(
        'backend.app.api.helpdesk.create_github_issue',
        lambda d, *, user_id: _patched_create(d, user_id=user_id, transport=transport),
    ):
        response = client.post(
            '/api/helpdesk/create-issue',
            json={'draft': _draft()},
            headers={'Authorization': f'Bearer {test_user_token}'},
        )
    assert response.status_code == 502, response.text
