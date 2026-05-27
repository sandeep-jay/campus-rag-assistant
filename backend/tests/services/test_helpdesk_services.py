"""Service-level helpdesk tests (redaction, kb_resolved heuristic)."""

from __future__ import annotations

from langchain.schema import Document

from backend.app.services.graph.nodes import _compute_kb_resolved
from backend.app.services.helpdesk.redaction import redact_text


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


def test_compute_kb_resolved_returns_none_for_web_mode():
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
