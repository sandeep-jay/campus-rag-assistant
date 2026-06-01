"""Service-level helpdesk tests (redaction, kb_resolved heuristic)."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from langchain.schema import Document

from backend.app.services.graph.nodes import _compute_kb_resolved
from backend.app.services.helpdesk.redaction import redact_text
from backend.app.services.helpdesk_graph import tools
from backend.app.services.helpdesk_graph.nodes import classify_ticket_facts


class _SecretLike:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


def test_redact_text_handles_emails_tokens_secrets():
    out = redact_text('reach me at alice@example.com bearer abc123def4567 password=hunter2 AKIAAAAAAAAAAAAAAAAA')
    assert 'alice@example.com' not in out
    assert 'hunter2' not in out
    assert 'AKIAAAAAAAAAAAAAAAAA' not in out
    assert 'bearer abc123def4567' not in out
    assert '[REDACTED]' in out


def test_redact_text_is_idempotent_for_clean_text():
    clean = 'How do I submit an assignment?'
    assert redact_text(clean) == clean


def test_redact_text_redacts_jwt_like_token():
    sample = 'token eyJabcdefghij.eyJhbGciOiJIUzI1NiJ9.abcdefghijklmnopqrst here'
    out = redact_text(sample)
    assert 'eyJabcdefghij.eyJhbGciOiJIUzI1NiJ9.abcdefghijklmnopqrst' not in out
    assert '[REDACTED]' in out


def test_compute_kb_resolved_returns_false_for_web_mode():
    assert _compute_kb_resolved('answer', [Document(page_content='x', metadata={})], 'web', None) is None


def test_compute_kb_resolved_false_when_no_documents():
    assert _compute_kb_resolved('an answer', [], 'kb', None) is False


def test_compute_kb_resolved_false_when_answer_is_out_of_scope():
    docs = [Document(page_content='hi', metadata={})]
    oos = 'I can only answer questions covered by the knowledge base for your platform.'
    assert _compute_kb_resolved(oos, docs, 'kb', None) is False


def test_compute_kb_resolved_true_for_substantive_answer():
    docs = [Document(page_content='step 1', metadata={})]
    answer = 'You can submit your assignment from the course homepage.'
    assert _compute_kb_resolved(answer, docs, 'kb', None) is True


class _FakeRetriever:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, query: str):
        self.calls += 1
        return [Document(page_content=f'KB result for {query}', metadata={'source': 'kb'})]


class _FakeRagService:
    is_mock = False

    def __init__(self) -> None:
        self.retriever = _FakeRetriever()


@pytest.mark.asyncio()
async def test_retry_kb_uses_retriever_and_session_cache(monkeypatch):
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_KB_RETRY', True)
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_KB_RETRY_TIMEOUT_SECONDS', 1.0)
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_OUTPUT_MAX_CHARS', 4000)
    state = {'session_id': 's1', 'user_id': 'u1', 'tool_cache': {}}
    rag = _FakeRagService()

    first = await tools.retry_kb('Oracle budget reports 403', rag_service=rag, state=state)
    second = await tools.retry_kb('Oracle budget reports 403', rag_service=rag, state=state)

    assert [doc.page_content for doc in first] == ['KB result for oracle budget reports 403']
    assert [doc.page_content for doc in second] == ['KB result for oracle budget reports 403']
    assert rag.retriever.calls == 1
    assert 'retry_kb:oracle budget reports 403' in state['tool_cache']


@pytest.mark.asyncio()
async def test_retry_kb_respects_disabled_flag(monkeypatch):
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_KB_RETRY', False)
    state = {'session_id': 's1', 'user_id': 'u1', 'tool_cache': {}}

    docs = await tools.retry_kb('anything', rag_service=_FakeRagService(), state=state)

    assert docs == []
    assert state['tool_cache'] == {}


@pytest.mark.asyncio()
async def test_web_search_redacts_secret_before_provider_query(monkeypatch):
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_WEB_SEARCH', True)
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_WEB_SEARCH_TIMEOUT_SECONDS', 1.0)
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_OUTPUT_MAX_CHARS', 4000)
    captured: dict[str, str] = {}
    fake_aws_key = 'AKIA' + 'ABCDEFGHIJKLMNOP'

    def _fake_web_search(query: str):
        captured['query'] = query
        return [Document(page_content='safe web result', metadata={'source': 'web'})]

    with patch('backend.app.services.helpdesk_graph.tools.web_search_documents', _fake_web_search):
        await tools.web_search(
            f'Canvas login broken with key {fake_aws_key}',
            state={'session_id': 's1', 'user_id': 'u1', 'tool_cache': {}},
        )

    assert fake_aws_key not in captured['query']
    assert '[redacted]' in captured['query']


@pytest.mark.asyncio()
async def test_web_search_uses_helper_and_session_cache(monkeypatch):
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_WEB_SEARCH', True)
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_WEB_SEARCH_TIMEOUT_SECONDS', 1.0)
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_OUTPUT_MAX_CHARS', 4000)
    state = {'session_id': 's1', 'user_id': 'u1', 'tool_cache': {}}
    calls = {'count': 0}

    def _fake_web_search(query: str):
        calls['count'] += 1
        return [Document(page_content=f'Web result for {query}', metadata={'source': 'web'})]

    with patch('backend.app.services.helpdesk_graph.tools.web_search_documents', _fake_web_search):
        first = await tools.web_search('Oracle budget reports 403', state=state)
        second = await tools.web_search('Oracle budget reports 403', state=state)

    assert [doc.page_content for doc in first] == ['Web result for oracle budget reports 403']
    assert [doc.page_content for doc in second] == ['Web result for oracle budget reports 403']
    assert calls['count'] == 1
    assert 'web_search:oracle budget reports 403' in state['tool_cache']


@pytest.mark.asyncio()
async def test_web_search_truncates_tool_output(monkeypatch):
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_WEB_SEARCH', True)
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_WEB_SEARCH_TIMEOUT_SECONDS', 1.0)
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_OUTPUT_MAX_CHARS', 5)

    with patch(
        'backend.app.services.helpdesk_graph.tools.web_search_documents',
        lambda _query: [Document(page_content='0123456789', metadata={'source': 'web'})],
    ):
        docs = await tools.web_search('long output', state={'session_id': 's1', 'user_id': 'u1', 'tool_cache': {}})

    assert docs[0].page_content == '01234'
    assert docs[0].metadata['truncated'] is True


@pytest.mark.asyncio()
async def test_search_existing_issues_redacts_secret_from_github_query(monkeypatch):
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_TOOL_GITHUB_SEARCH', True)
    monkeypatch.setattr(tools.settings, 'GITHUB_TOKEN', _SecretLike('demo-token'))
    monkeypatch.setattr(tools.settings, 'GITHUB_REPO', 'demo-org/demo-repo')
    monkeypatch.setattr(tools.settings, 'HELPDESK_AGENT_GITHUB_SEARCH_TIMEOUT_SECONDS', 1.0)
    captured: dict[str, str] = {}
    fake_aws_key = 'AKIA' + 'ABCDEFGHIJKLMNOP'

    def _handler(request: httpx.Request) -> httpx.Response:
        captured['q'] = str(request.url.params.get('q'))
        return httpx.Response(200, json={'items': []})

    await tools.search_existing_issues(
        f'Canvas login broken with key {fake_aws_key}',
        transport=httpx.MockTransport(_handler),
    )

    assert fake_aws_key not in captured['q']
    assert '[REDACTED]' in captured['q']


def test_classify_ticket_facts_infers_access_high_team():
    state = {
        'session_id': 's1',
        'user_id': 'u1',
        'original_question': 'Oracle Financials 403 error blocks budget reports',
        'conversation': [],
        'facts': {'impact': 'My team'},
    }

    facts = classify_ticket_facts(state)

    assert facts == {'severity': 'high', 'category': 'access', 'impact': 'Team'}


def test_classify_ticket_facts_infers_network_outage():
    state = {
        'session_id': 's1',
        'user_id': 'u1',
        'original_question': 'Campus-wide wifi outage for all users',
        'conversation': [],
        'facts': {},
    }

    facts = classify_ticket_facts(state)

    assert facts == {'severity': 'critical', 'category': 'network', 'impact': 'Campus-wide'}
