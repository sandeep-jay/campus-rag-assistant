"""Tests for the helpdesk router and supporting services.

The router exposes two independent agent tasks:

- ``/summarize`` returns a narrative ``ConversationSummary``.
- ``/draft-ticket`` returns a structured ``TicketDraft`` for the modal.

Both share the same redact + trim pipeline; we exercise that path on
``/draft-ticket`` (it is the structured endpoint and gives a stable
``response.json()`` shape to assert against the LLM call).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from backend.app.core.config_manager import settings
from backend.app.core.metrics import (
    HELPDESK_AGENT_DECISION_TOTAL,
    HELPDESK_AGENT_ERROR_TOTAL,
    HELPDESK_AGENT_FUNNEL_TOTAL,
    HELPDESK_AGENT_TOOL_LATENCY_SECONDS,
)
from backend.app.schemas.helpdesk import ConversationTurn
from backend.app.services.helpdesk import github as github_module
from backend.app.services.helpdesk_graph import runner as runner_module
from backend.app.services.helpdesk_graph.runner import resume_session, start_session


@pytest.fixture()
def enable_helpdesk(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'HELPDESK_ENABLED', True)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_ENABLED', True)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_KILL_SWITCH', False)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_TOOL_GITHUB_SEARCH', True)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_LLM_SUPERVISOR', False)
    monkeypatch.setattr(settings, 'RAG_FORCE_MOCK', True)
    monkeypatch.setattr(settings, 'LLM_PROVIDER', 'mock')
    monkeypatch.setattr(settings, 'WEB_SEARCH_PROVIDER', 'mock')
    monkeypatch.setattr(settings, 'TAVILY_API_KEY', None)
    monkeypatch.setattr(settings, 'GITHUB_TOKEN', _SecretLike('demo-token'))
    monkeypatch.setattr(settings, 'GITHUB_REPO', 'demo-org/demo-repo')
    monkeypatch.setattr(settings, 'GITHUB_DEFAULT_LABELS', 'it-helpdesk,demo')
    monkeypatch.setattr(settings, 'HELPDESK_DEDUP_WINDOW_SECONDS', 300)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_USE_LANGGRAPH_CHECKPOINT', True)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_CHECKPOINT_BACKEND', 'memory')
    monkeypatch.setattr(
        settings,
        'HELPDESK_AGENT_CHECKPOINT_PATH',
        str(tmp_path / 'helpdesk_agent.sqlite'),
    )
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_CHECKPOINT_TTL_SECONDS', 86400)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_MAX_TURNS', 8)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_MAX_QUESTIONS', 2)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_CLARIFY_CONFIDENCE_FLOOR', 0.75)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_MAX_TOOL_RETRIES', 2)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_MAX_TOKENS_PER_SESSION', 20000)
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_DEADLINE_SECONDS', 60.0)
    # Reset the in-process dedup cache for test isolation.
    github_module._dedup_cache._store.clear()
    runner_module._confirm_idempotency_cache._store.clear()


def _counter_value(counter, **labels) -> float:
    return counter.labels(**labels)._value.get()


def _reset_postgres_checkpoint_schema(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS checkpoint_writes'))
        conn.execute(text('DROP TABLE IF EXISTS checkpoint_blobs'))
        conn.execute(text('DROP TABLE IF EXISTS checkpoints'))
        conn.execute(text('DROP TABLE IF EXISTS checkpoint_migrations'))
        conn.execute(text('CREATE TABLE checkpoint_migrations (v INTEGER PRIMARY KEY)'))
        conn.execute(
            text(
                """
                CREATE TABLE checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    type TEXT,
                    checkpoint JSONB NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}',
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE checkpoint_blobs (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    channel TEXT NOT NULL,
                    version TEXT NOT NULL,
                    type TEXT NOT NULL,
                    blob BYTEA,
                    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE checkpoint_writes (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    type TEXT,
                    blob BYTEA NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                )
                """
            )
        )
        conn.execute(text('INSERT INTO checkpoint_migrations (v) VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8)'))


class _SecretLike:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


@pytest.fixture()
def disable_helpdesk(monkeypatch):
    """Force the feature flag off even if the local ``.env`` enables it."""
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


def test_agent_start_requires_auth(client: TestClient, enable_helpdesk):
    response = client.post('/api/helpdesk/agent/start', json={'conversation': []})
    assert response.status_code == 401


def test_agent_resume_requires_auth(client: TestClient, enable_helpdesk):
    response = client.post('/api/helpdesk/agent/resume', json={'session_id': 'missing', 'reply': 'Team'})
    assert response.status_code == 401


def test_agent_abort_requires_auth(client: TestClient, enable_helpdesk):
    response = client.post('/api/helpdesk/agent/abort', json={'session_id': 'missing'})
    assert response.status_code == 401


def test_agent_confirm_requires_auth(client: TestClient, enable_helpdesk):
    response = client.post(
        '/api/helpdesk/agent/confirm',
        json={
            'session_id': 'missing',
            'draft': {
                'title': 'x',
                'description': 'x',
                'severity': 'low',
                'category': 'other',
                'steps_to_reproduce': None,
                'impact': 'Single user',
            },
        },
    )
    assert response.status_code == 401


def test_agent_start_returns_404_when_agent_disabled(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
    monkeypatch,
):
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_ENABLED', False)
    response = client.post(
        '/api/helpdesk/agent/start',
        json={'conversation': []},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 404


def _start_agent_for_oracle_issue(client: TestClient, token: str) -> dict:
    """Fresh agent invocation (no prior assistant turn).

    Exercises the full propose-solution path.
    """
    payload = {
        'conversation': [
            {
                'role': 'user',
                'content': 'Oracle Financials 403 error on budget reports',
            },
        ]
    }
    start = client.post(
        '/api/helpdesk/agent/start',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert start.status_code == 200, start.text
    body = start.json()
    assert body['kind'] == 'info'
    assert body['session_id']
    assert body['message'].lstrip().startswith('###')
    return body


def _answer_impact(
    client: TestClient,
    token: str,
    first_turn: dict,
    *,
    chat_session_id: int | None = None,
) -> dict:
    if first_turn['kind'] in {'info', 'draft_ready'}:
        return first_turn
    pending_question_id = first_turn['debug_trace'][0]['message']
    payload: dict = {
        'session_id': first_turn['session_id'],
        'choice': 'My team',
        'pending_question_id': pending_question_id,
    }
    if chat_session_id is not None:
        payload['chat_session_id'] = chat_session_id
    resume = client.post(
        '/api/helpdesk/agent/resume',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resume.status_code == 200, resume.text
    return resume.json()


def test_agent_start_stream_returns_status_and_final_turn(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    response = client.post(
        '/api/helpdesk/agent/start/stream',
        json={
            'conversation': [
                {
                    'role': 'user',
                    'content': 'Oracle Financials 403 error on budget reports',
                }
            ]
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )

    assert response.status_code == 200, response.text
    assert '"type": "step"' in response.text
    assert '"node": "supervisor"' in response.text
    assert '"type": "done"' in response.text
    assert '"kind": "info"' in response.text


def test_agent_resume_stream_returns_status_and_final_turn(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    first = _start_agent_for_oracle_issue(client, test_user_token)
    response = client.post(
        '/api/helpdesk/agent/resume/stream',
        json={
            'session_id': first['session_id'],
            'choice': 'Yes, that solved it',
            'pending_question_id': first['debug_trace'][-1]['message'],
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )

    assert response.status_code == 200, response.text
    assert '"type": "step"' in response.text
    assert '"node": "supervisor"' in response.text
    assert '"type": "done"' in response.text
    assert '"kind": "resolved"' in response.text


def test_agent_metrics_record_funnel_and_errors(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    started_before = _counter_value(HELPDESK_AGENT_FUNNEL_TOTAL, stage='started', outcome='api')
    error_before = _counter_value(HELPDESK_AGENT_ERROR_TOTAL, operation='resume', reason='http_404')

    _start_agent_for_oracle_issue(client, test_user_token)
    missing = client.post(
        '/api/helpdesk/agent/resume',
        json={'session_id': 'missing-session', 'reply': 'Team'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )

    assert missing.status_code == 404
    assert _counter_value(HELPDESK_AGENT_FUNNEL_TOTAL, stage='started', outcome='api') == started_before + 1
    assert _counter_value(HELPDESK_AGENT_ERROR_TOTAL, operation='resume', reason='http_404') == error_before + 1


def test_agent_stream_records_decision_and_tool_latency_metrics(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    decision_before = _counter_value(HELPDESK_AGENT_DECISION_TOTAL, next_action='search_duplicates')

    response = client.post(
        '/api/helpdesk/agent/start/stream',
        json={
            'conversation': [
                {
                    'role': 'user',
                    'content': 'Oracle Financials 403 error on budget reports',
                }
            ]
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )

    assert response.status_code == 200, response.text
    assert _counter_value(HELPDESK_AGENT_DECISION_TOTAL, next_action='search_duplicates') >= decision_before + 1
    samples = HELPDESK_AGENT_TOOL_LATENCY_SECONDS.labels(tool='retry_kb')._sum.get()
    assert samples >= 0


@pytest.mark.asyncio()
async def test_agent_postgres_checkpointer_round_trips_pause_resume(
    engine,
    enable_helpdesk,
    monkeypatch,
):
    _reset_postgres_checkpoint_schema(engine)
    monkeypatch.setattr(settings, 'DATABASE_URL', engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_CHECKPOINT_BACKEND', 'postgres')

    first = await start_session(
        [ConversationTurn(role='user', content='Oracle Financials 403 error on budget reports')],
        user_id='postgres-checkpoint-user',
    )
    pending_question_id = first.debug_trace[-1].message

    resumed = await resume_session(
        first.session_id,
        user_id='postgres-checkpoint-user',
        choice='Yes, that solved it',
        pending_question_id=pending_question_id,
    )

    assert first.kind == 'info'
    assert resumed.kind == 'resolved'
    with engine.connect() as conn:
        checkpoint_count = conn.execute(
            text('SELECT count(*) FROM checkpoints WHERE thread_id = :thread_id'),
            {'thread_id': first.session_id},
        ).scalar_one()
    assert checkpoint_count > 0


def test_agent_always_attempts_solution_even_after_out_of_scope_ask(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    """Agent must still try to answer even after an out-of-scope ASK refusal.

    A prior ASK answer such as "I can only answer questions covered by the
    knowledge base" is not a substantive answer — the agent should still
    run ``retry_kb`` (and ``web_search`` if needed) before falling back to
    a ticket draft. Regression test for the over-aggressive
    ``skip_propose_solution`` short-circuit.
    """
    payload = {
        'conversation': [
            {
                'role': 'user',
                'content': 'Oracle Financials 403 error on budget reports',
            },
            {
                'role': 'assistant',
                'content': 'I can only answer questions covered by the knowledge base.',
            },
        ]
    }
    start = client.post(
        '/api/helpdesk/agent/start',
        json=payload,
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert start.status_code == 200, start.text
    first = start.json()
    body = _answer_impact(client, test_user_token, first)

    actions = [step['action'] for step in body['debug_trace']]
    assert 'skip_propose_solution' not in actions
    # In the mock provider the agent reaches the propose-solution step
    # (or falls through to draft if KB retry yields nothing), but it
    # must never have short-circuited on a prior assistant turn.
    assert body['kind'] in {'info', 'draft_ready'}


def test_agent_resume_proposes_solution_after_impact_answer(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    first = _start_agent_for_oracle_issue(client, test_user_token)
    body = _answer_impact(client, test_user_token, first)

    assert body['kind'] == 'info'
    assert body['session_id'] == first['session_id']
    assert body['draft'] is None
    assert body['choices'] == [
        'Yes, that solved it',
        "No, doesn't apply",
        "Tried it, didn't work",
    ]
    # The solution message renders with a markdown title and a source link
    # (chat-prose formatted), so we just assert both shape pieces are present.
    assert body['message'].lstrip().startswith('###')
    assert 'View source' in body['message'] or 'KB' in body['message']
    assert [step['action'] for step in body['debug_trace']] == [
        'retry_kb',
        'propose_solution',
    ]
    assert body['sources']
    assert len(body['sources']) >= 1
    assert body['source_kind'] == 'kb'
    assert body['document_contents']


def test_agent_requests_web_consent_when_kb_empty_and_live_provider(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
    monkeypatch,
):
    async def _no_documents(*args, **kwargs):
        return []

    monkeypatch.setattr(settings, 'WEB_SEARCH_PROVIDER', 'tavily')
    monkeypatch.setattr(settings, 'TAVILY_API_KEY', _SecretLike('test-tavily-key'))
    with patch('backend.app.services.helpdesk_graph.runner.tools.retry_kb', _no_documents):
        response = client.post(
            '/api/helpdesk/agent/start',
            json={
                'conversation': [
                    {
                        'role': 'user',
                        'content': 'Oracle Financials 403 error on budget reports',
                    },
                ],
            },
            headers={'Authorization': f'Bearer {test_user_token}'},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'question'
    assert body['input'] == 'radio'
    assert 'public web' in body['message'].lower()
    assert body['choices'] == ['Search the web', 'Skip and draft a ticket']
    assert 'web_search' not in [step['action'] for step in body.get('debug_trace', [])]


def test_agent_web_consent_accept_runs_web_search(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
    monkeypatch,
):
    from langchain.schema import Document

    async def _no_kb(*args, **kwargs):
        return []

    async def _web_docs(*args, **kwargs):
        return [
            Document(
                page_content='Clear browser cache and retry Oracle login.',
                metadata={
                    'source_metadata': {
                        'kb_url': 'https://example.com/oracle-fix',
                        'kb_number': 'WEB-1',
                        'short_description': 'Oracle login fix',
                        'kb_category': '',
                        'project': '',
                        'ingestion_date': '',
                    },
                    'score': 0.9,
                },
            ),
        ]

    monkeypatch.setattr(settings, 'WEB_SEARCH_PROVIDER', 'tavily')
    monkeypatch.setattr(settings, 'TAVILY_API_KEY', _SecretLike('test-tavily-key'))
    with (
        patch('backend.app.services.helpdesk_graph.runner.tools.retry_kb', _no_kb),
        patch('backend.app.services.helpdesk_graph.runner.tools.web_search', _web_docs),
    ):
        start = client.post(
            '/api/helpdesk/agent/start',
            json={
                'conversation': [
                    {
                        'role': 'user',
                        'content': 'Oracle Financials 403 error on budget reports',
                    },
                ],
            },
            headers={'Authorization': f'Bearer {test_user_token}'},
        )
        assert start.status_code == 200, start.text
        first = start.json()
        pending_question_id = first['debug_trace'][-1]['message']
        resume = client.post(
            '/api/helpdesk/agent/resume',
            json={
                'session_id': first['session_id'],
                'choice': 'Search the web',
                'pending_question_id': pending_question_id,
            },
            headers={'Authorization': f'Bearer {test_user_token}'},
        )

    assert resume.status_code == 200, resume.text
    body = resume.json()
    assert body['kind'] == 'info'
    assert body['source_kind'] == 'web'
    assert body['disclaimer']
    assert body['sources']
    assert any(step['action'] == 'web_search' for step in body['debug_trace'])


def test_agent_web_consent_decline_drafts_ticket(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
    monkeypatch,
):
    async def _no_documents(*args, **kwargs):
        return []

    monkeypatch.setattr(settings, 'WEB_SEARCH_PROVIDER', 'tavily')
    monkeypatch.setattr(settings, 'TAVILY_API_KEY', _SecretLike('test-tavily-key'))
    with patch('backend.app.services.helpdesk_graph.runner.tools.retry_kb', _no_documents):
        start = client.post(
            '/api/helpdesk/agent/start',
            json={
                'conversation': [
                    {
                        'role': 'user',
                        'content': 'Oracle Financials 403 error on budget reports',
                    },
                ],
            },
            headers={'Authorization': f'Bearer {test_user_token}'},
        )
        assert start.status_code == 200, start.text
        first = start.json()
        pending_question_id = first['debug_trace'][-1]['message']
        resume = client.post(
            '/api/helpdesk/agent/resume',
            json={
                'session_id': first['session_id'],
                'choice': 'Skip and draft a ticket',
                'pending_question_id': pending_question_id,
            },
            headers={'Authorization': f'Bearer {test_user_token}'},
        )

    assert resume.status_code == 200, resume.text
    body = resume.json()
    assert body['kind'] == 'draft_ready'
    assert body['draft']['title']
    assert not any(step['action'] == 'web_search' for step in body['debug_trace'])


def test_mock_web_search_skips_consent_prompt(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
    monkeypatch,
):
    async def _no_kb(*args, **kwargs):
        return []

    monkeypatch.setattr(settings, 'WEB_SEARCH_PROVIDER', 'mock')
    monkeypatch.setattr(settings, 'TAVILY_API_KEY', None)
    with patch('backend.app.services.helpdesk_graph.runner.tools.retry_kb', _no_kb):
        response = client.post(
            '/api/helpdesk/agent/start',
            json={
                'conversation': [
                    {
                        'role': 'user',
                        'content': 'Oracle Financials 403 error on budget reports',
                    },
                ],
            },
            headers={'Authorization': f'Bearer {test_user_token}'},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'info'
    assert 'web_search_consent' not in [step['action'] for step in body.get('debug_trace', [])]
    assert any(step['action'] == 'web_search' for step in body['debug_trace'])


def test_agent_asks_clarification_after_help_attempt_when_impact_ambiguous(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    async def _no_documents(*args, **kwargs):
        return []

    with (
        patch('backend.app.services.helpdesk_graph.runner.tools.retry_kb', _no_documents),
        patch('backend.app.services.helpdesk_graph.runner.tools.web_search', _no_documents),
    ):
        response = client.post(
            '/api/helpdesk/agent/start',
            json={'conversation': [{'role': 'user', 'content': 'Canvas assignment upload is broken'}]},
            headers={'Authorization': f'Bearer {test_user_token}'},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'question'
    assert body['input'] == 'radio'
    assert 'campus' in body['message'].lower()
    assert body['choices'] == ['Only me', 'My team', 'Campus-wide', 'Not sure']


def test_agent_budget_exhaustion_returns_ticket_draft(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
    monkeypatch,
):
    monkeypatch.setattr(settings, 'HELPDESK_AGENT_MAX_TURNS', 1)
    proposal = _start_agent_for_oracle_issue(client, test_user_token)
    pending_question_id = proposal['debug_trace'][-1]['message']

    response = client.post(
        '/api/helpdesk/agent/resume',
        json={
            'session_id': proposal['session_id'],
            'choice': "Tried it, didn't work",
            'pending_question_id': pending_question_id,
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body['kind'] == 'draft_ready'
    assert body['draft']['title']
    assert any(step['action'] == 'budget_exhausted' for step in body['debug_trace'])


def test_agent_solution_acceptance_resolves_session(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    first = _start_agent_for_oracle_issue(client, test_user_token)
    proposal = _answer_impact(client, test_user_token, first)
    pending_question_id = proposal['debug_trace'][-1]['message']

    response = client.post(
        '/api/helpdesk/agent/resume',
        json={
            'session_id': first['session_id'],
            'choice': 'Yes, that solved it',
            'pending_question_id': pending_question_id,
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'resolved'
    assert body['draft'] is None
    assert body['kind'] in {'resolved', 'aborted'}


def test_agent_solution_rejection_returns_ticket_draft(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    first = _start_agent_for_oracle_issue(client, test_user_token)
    proposal = _answer_impact(client, test_user_token, first)
    pending_question_id = proposal['debug_trace'][-1]['message']

    response = client.post(
        '/api/helpdesk/agent/resume',
        json={
            'session_id': first['session_id'],
            'choice': "Tried it, didn't work",
            'pending_question_id': pending_question_id,
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'draft_ready'
    assert body['draft']['title']
    assert [step['action'] for step in body['debug_trace']] == [
        'solution_feedback',
        'classify_ticket',
        'write_draft',
    ]
    assert body['draft']['severity'] == 'high'
    assert body['draft']['category'] == 'access'
    assert body['draft']['impact'] == 'Single user'


def test_agent_resume_rejects_stale_question_id(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    start = client.post(
        '/api/helpdesk/agent/start',
        json={
            'conversation': [
                {
                    'role': 'user',
                    'content': 'Oracle Financials 403 error on budget reports',
                }
            ]
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert start.status_code == 200, start.text
    response = client.post(
        '/api/helpdesk/agent/resume',
        json={
            'session_id': start.json()['session_id'],
            'choice': 'My team',
            'pending_question_id': 'stale',
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 409


def _draft_ready_agent(client: TestClient, token: str) -> dict:
    first = _start_agent_for_oracle_issue(client, token)
    proposal = _answer_impact(client, token, first)
    response = client.post(
        '/api/helpdesk/agent/resume',
        json={
            'session_id': first['session_id'],
            'choice': "Tried it, didn't work",
            'pending_question_id': proposal['debug_trace'][-1]['message'],
        },
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'draft_ready'
    return body


def test_agent_confirm_files_reviewed_draft(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    draft_turn = _draft_ready_agent(client, test_user_token)
    filed = {'count': 0}

    async def _fake_create_github_issue(draft, *, user_id):
        from backend.app.schemas.helpdesk import CreateIssueResponse

        filed['count'] += 1
        assert draft.title == 'Reviewed Oracle Financials 403'
        assert user_id is not None
        return CreateIssueResponse(
            issue_url='https://github.com/demo-org/demo-repo/issues/77',
            issue_number=77,
            deduplicated=False,
        )

    reviewed = {**draft_turn['draft'], 'title': 'Reviewed Oracle Financials 403'}
    with patch(
        'backend.app.services.helpdesk_graph.runner.create_github_issue',
        _fake_create_github_issue,
    ):
        response = client.post(
            '/api/helpdesk/agent/confirm',
            json={'session_id': draft_turn['session_id'], 'draft': reviewed},
            headers={'Authorization': f'Bearer {test_user_token}'},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert filed['count'] == 1
    assert body['kind'] == 'filed'
    assert body['linked_issue_url'].endswith('/77')
    assert '#77' in body['message'] or '/issues/77' in body['message'] or 'filed' in body['message'].lower()
    assert body['debug_trace'][0]['action'] == 'file_ticket'

    resume = client.post(
        '/api/helpdesk/agent/resume',
        json={'session_id': draft_turn['session_id'], 'choice': 'My team'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert resume.status_code == 409


def test_agent_confirm_idempotency_key_reuses_prior_turn(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    draft_turn = _draft_ready_agent(client, test_user_token)
    filed = {'count': 0}

    async def _fake_create_github_issue(draft, *, user_id):
        from backend.app.schemas.helpdesk import CreateIssueResponse

        filed['count'] += 1
        return CreateIssueResponse(
            issue_url='https://github.com/demo-org/demo-repo/issues/88',
            issue_number=88,
            deduplicated=False,
        )

    headers = {
        'Authorization': f'Bearer {test_user_token}',
        'Idempotency-Key': 'confirm-double-click',
    }
    payload = {'session_id': draft_turn['session_id'], 'draft': draft_turn['draft']}
    with patch(
        'backend.app.services.helpdesk_graph.runner.create_github_issue',
        _fake_create_github_issue,
    ):
        first = client.post('/api/helpdesk/agent/confirm', json=payload, headers=headers)
        second = client.post('/api/helpdesk/agent/confirm', json=payload, headers=headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert filed['count'] == 1
    assert second.json() == first.json()


def test_agent_confirm_rejects_session_not_waiting_for_confirmation(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    first = _start_agent_for_oracle_issue(client, test_user_token)
    draft = {
        'title': 'Cannot access Oracle Financials',
        'description': 'A 403 error blocks budget reports.',
        'severity': 'high',
        'category': 'access',
        'steps_to_reproduce': None,
        'impact': 'Team',
    }
    response = client.post(
        '/api/helpdesk/agent/confirm',
        json={'session_id': first['session_id'], 'draft': draft},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 409


def test_agent_abort_cancels_active_session(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    first = _start_agent_for_oracle_issue(client, test_user_token)

    response = client.post(
        '/api/helpdesk/agent/abort',
        json={'session_id': first['session_id']},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'aborted'
    assert body['draft'] is None
    assert body['kind'] in {'resolved', 'aborted'}
    assert body['debug_trace'][0]['action'] == 'abort'

    resume = client.post(
        '/api/helpdesk/agent/resume',
        json={
            'session_id': first['session_id'],
            'choice': 'My team',
            'pending_question_id': first['debug_trace'][0]['message'],
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert resume.status_code == 409


def test_agent_abort_returns_404_for_missing_session(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    response = client.post(
        '/api/helpdesk/agent/abort',
        json={'session_id': 'missing'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 404


def test_agent_start_links_existing_mock_duplicate(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    payload = {
        'conversation': [
            {
                'role': 'user',
                'content': 'known duplicate Oracle Financials access issue',
            },
        ]
    }
    response = client.post(
        '/api/helpdesk/agent/start',
        json=payload,
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'linked'
    assert body['linked_issue_url'].endswith('/42')
    assert body['draft'] is None


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
    body = response.json()
    # Recap is a plain narrative wrapped in {summary: {summary: str}} —
    # explicitly NOT shaped like a ticket draft.
    assert 'summary' in body
    summary_obj = body['summary']
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
    body = response.json()
    draft = body['draft']
    assert draft['title']
    assert draft['severity'] in {'low', 'medium', 'high', 'critical'}
    assert draft['category'] in {
        'network',
        'access',
        'application',
        'hardware',
        'account',
        'other',
    }
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
        patch(
            'backend.app.services.helpdesk.agent.get_llm_provider',
            return_value=_FakeProvider(),
        ),
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
    """The recap endpoint must also redact before reaching the LLM."""
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
        patch(
            'backend.app.services.helpdesk.agent.get_llm_provider',
            return_value=_FakeProvider(),
        ),
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


def test_create_issue_calls_github_and_dedups(client: TestClient, test_user_token: str, enable_helpdesk):
    calls = {'count': 0}

    def _handler(request: httpx.Request) -> httpx.Response:
        calls['count'] += 1
        assert request.headers['Authorization'].startswith('token ')
        body = json.loads(request.content.decode('utf-8'))
        assert 'Severity' in body['body']
        return httpx.Response(
            201,
            json={
                'html_url': 'https://github.com/demo-org/demo-repo/issues/1',
                'number': 1,
            },
        )

    draft = {
        'title': 'Cannot access Oracle Financials',
        'description': 'A 403 error blocks budget report retrieval.',
        'severity': 'high',
        'category': 'access',
        'steps_to_reproduce': None,
        'impact': 'Team',
    }

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
            json={'draft': draft},
            headers={'Authorization': f'Bearer {test_user_token}'},
        )
        second = client.post(
            '/api/helpdesk/create-issue',
            json={'draft': draft},
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

    draft = {
        'title': 'GitHub denies us',
        'description': 'Token must be wrong.',
        'severity': 'low',
        'category': 'other',
        'steps_to_reproduce': None,
        'impact': 'Single user',
    }

    with patch(
        'backend.app.api.helpdesk.create_github_issue',
        lambda d, *, user_id: _patched_create(d, user_id=user_id, transport=transport),
    ):
        response = client.post(
            '/api/helpdesk/create-issue',
            json={'draft': draft},
            headers={'Authorization': f'Bearer {test_user_token}'},
        )
    assert response.status_code == 502, response.text


# --- Option A: durable agent summary persistence ---------------------------
#
# Terminal agent turns (filed / linked / resolved / aborted) write a single
# row to ``chat_messages`` for the user's chat session, so the agent's
# outcome survives a page refresh without dual-writing every intermediate
# turn. The optimistic in-memory bubble is then reconciled with the
# server-issued row id via ``AgentTurn.chat_message_id``.


def _create_chat_session(client: TestClient, token: str, title: str = 'Helpdesk test') -> int:
    res = client.post(
        '/api/chat/sessions',
        json={'title': title},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert res.status_code == 200, res.text
    return int(res.json()['id'])


def _session_assistant_messages(client: TestClient, token: str, session_id: int) -> list[dict]:
    res = client.get(
        f'/api/chat/sessions/{session_id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert res.status_code == 200, res.text
    return [m for m in res.json()['messages'] if m['role'] == 'assistant']


def test_agent_abort_persists_summary_to_chat_session(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    """Aborting an agent session writes one assistant row recapping the outcome."""
    chat_session_id = _create_chat_session(client, test_user_token)
    first = _start_agent_for_oracle_issue(client, test_user_token)

    response = client.post(
        '/api/helpdesk/agent/abort',
        json={'session_id': first['session_id'], 'chat_session_id': chat_session_id},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'aborted'
    assert isinstance(body['chat_message_id'], int)

    assistant_msgs = _session_assistant_messages(client, test_user_token, chat_session_id)
    assert len(assistant_msgs) == 1
    persisted = assistant_msgs[0]
    assert persisted['id'] == body['chat_message_id']
    assert persisted['metadata']['agent_summary']['kind'] == 'aborted'
    assert persisted['metadata']['agent_summary']['agent_session_id'] == first['session_id']
    # Trace is persisted so the reloaded chat row can render the same
    # activity timeline as the live in-memory bubble.
    trace = persisted['metadata']['agent_summary'].get('trace')
    assert isinstance(trace, list), 'trace should be a list'
    assert trace, 'trace should be populated on terminal turns'
    assert all('action' in step and 'outcome' in step for step in trace)


def test_agent_confirm_persists_summary_with_issue_link(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    """Filing a ticket persists one row with the GitHub issue URL inline."""
    chat_session_id = _create_chat_session(client, test_user_token)
    draft_turn = _draft_ready_agent(client, test_user_token)

    async def _fake_create_github_issue(draft, *, user_id):
        from backend.app.schemas.helpdesk import CreateIssueResponse

        return CreateIssueResponse(
            issue_url='https://github.com/demo-org/demo-repo/issues/101',
            issue_number=101,
            deduplicated=False,
        )

    with patch(
        'backend.app.services.helpdesk_graph.runner.create_github_issue',
        _fake_create_github_issue,
    ):
        response = client.post(
            '/api/helpdesk/agent/confirm',
            json={
                'session_id': draft_turn['session_id'],
                'draft': draft_turn['draft'],
                'chat_session_id': chat_session_id,
            },
            headers={'Authorization': f'Bearer {test_user_token}'},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body['kind'] == 'filed'
    assert isinstance(body['chat_message_id'], int)

    assistant_msgs = _session_assistant_messages(client, test_user_token, chat_session_id)
    assert len(assistant_msgs) == 1
    persisted = assistant_msgs[0]
    assert persisted['id'] == body['chat_message_id']
    assert 'github.com/demo-org/demo-repo/issues/101' in persisted['content']
    summary_meta = persisted['metadata']['agent_summary']
    assert summary_meta['kind'] == 'filed'
    assert summary_meta['linked_issue_url'].endswith('/101')
    trace = summary_meta.get('trace')
    assert isinstance(trace, list), 'trace should be a list'
    assert trace, 'trace should be populated on terminal turns'
    file_steps = [step for step in trace if step.get('action') == 'file_ticket']
    assert file_steps, 'expected file_ticket step in persisted trace'


def test_agent_terminal_without_chat_session_id_skips_persistence(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    """Back-compat: no ``chat_session_id`` means no chat row is written."""
    chat_session_id = _create_chat_session(client, test_user_token)
    first = _start_agent_for_oracle_issue(client, test_user_token)

    response = client.post(
        '/api/helpdesk/agent/abort',
        json={'session_id': first['session_id']},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    assert response.json()['chat_message_id'] is None

    assistant_msgs = _session_assistant_messages(client, test_user_token, chat_session_id)
    assert assistant_msgs == []


def test_agent_terminal_with_foreign_chat_session_skips_persistence(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    """Bogus ``chat_session_id`` is ignored — never raises, never writes."""
    first = _start_agent_for_oracle_issue(client, test_user_token)
    response = client.post(
        '/api/helpdesk/agent/abort',
        json={'session_id': first['session_id'], 'chat_session_id': 999999},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200, response.text
    assert response.json()['chat_message_id'] is None


def test_agent_start_upserts_question_when_chat_session_id_provided(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    """First agent turn persists immediately so refresh mid-turn is safe."""
    chat_session_id = _create_chat_session(client, test_user_token)
    start = client.post(
        '/api/helpdesk/agent/start',
        json={
            'conversation': [
                {
                    'role': 'user',
                    'content': 'Oracle Financials 403 error on budget reports',
                },
            ],
            'chat_session_id': chat_session_id,
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert start.status_code == 200, start.text
    body = start.json()
    assert body['kind'] == 'info'
    assert isinstance(body['chat_message_id'], int)

    assistant_msgs = _session_assistant_messages(client, test_user_token, chat_session_id)
    assert len(assistant_msgs) == 1
    persisted = assistant_msgs[0]
    assert persisted['id'] == body['chat_message_id']
    summary = persisted['metadata']['agent_summary']
    assert summary['kind'] == 'info'
    assert summary['agent_session_id'] == body['session_id']
    trace = summary.get('trace')
    assert isinstance(trace, list)
    assert trace
    assert summary.get('sources')
    assert summary.get('document_contents')
    assert summary.get('source_kind') == 'kb'


def test_agent_journey_upserts_same_chat_message_row(
    client: TestClient,
    test_user_token: str,
    enable_helpdesk,
):
    """Each subsequent turn updates the same row — no holes on refresh."""
    chat_session_id = _create_chat_session(client, test_user_token)
    start = client.post(
        '/api/helpdesk/agent/start',
        json={
            'conversation': [
                {
                    'role': 'user',
                    'content': 'Oracle Financials 403 error on budget reports',
                },
            ],
            'chat_session_id': chat_session_id,
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert start.status_code == 200, start.text
    first = start.json()
    first_row_id = first['chat_message_id']
    assert isinstance(first_row_id, int)

    proposal = _answer_impact(client, test_user_token, first, chat_session_id=chat_session_id)
    assert proposal['chat_message_id'] == first_row_id
    assert proposal['kind'] == 'info'

    assistant_msgs = _session_assistant_messages(client, test_user_token, chat_session_id)
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]['id'] == first_row_id
    assert assistant_msgs[0]['metadata']['agent_summary']['kind'] == 'info'
    trace = assistant_msgs[0]['metadata']['agent_summary'].get('trace')
    assert isinstance(trace, list)
    assert len(trace) >= len(first['debug_trace'])

    pending_question_id = proposal['debug_trace'][-1]['message']
    resolved = client.post(
        '/api/helpdesk/agent/resume',
        json={
            'session_id': first['session_id'],
            'choice': 'Yes, that solved it',
            'pending_question_id': pending_question_id,
            'chat_session_id': chat_session_id,
        },
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert resolved.status_code == 200, resolved.text
    resolved_body = resolved.json()
    assert resolved_body['chat_message_id'] == first_row_id
    assert resolved_body['kind'] == 'resolved'

    assistant_msgs = _session_assistant_messages(client, test_user_token, chat_session_id)
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]['id'] == first_row_id
    assert assistant_msgs[0]['metadata']['agent_summary']['kind'] == 'resolved'
