"""Tests for assistant answer markdown normalization."""

from backend.app.services.rag import RAGService


def _fmt(text: str) -> str:
    rag = RAGService.__new__(RAGService)
    return rag._normalize_answer_formatting(text)


def test_sanitize_drops_prompt_leakage():
    raw = 'Answer here.\nHuman: follow-up\nkb_url: http://x'
    out = _fmt(raw)
    assert 'Human' not in out
    assert 'kb_url' not in out
    assert 'Answer here' in out


def test_promote_standalone_bold_to_heading():
    raw = 'Summary.\n\n**Group Management**\n- Create groups\n'
    out = _fmt(raw)
    assert '## Group Management' in out
    assert '- Create groups' in out


def test_keeps_bold_leadin_with_colon():
    raw = '**To create groups:**\n- Step one\n'
    out = _fmt(raw)
    assert '**To create groups:**' in out
    assert '## To create groups' not in out


def test_preserves_model_markdown_structure():
    raw = """Short intro.

## Discussion Tools

**Use discussions to:**
  - Post announcements
  - Reply to threads

1. Open Canvas LMS
2. Select Discussions
"""
    out = _fmt(raw)
    assert '## Discussion Tools' in out
    assert '1. Open Canvas LMS' in out
    assert '  - Post announcements' in out


def test_strip_condensed_question_before_em_dash():
    raw = 'How do I submit an assignment in the learning platform?' '— Students can submit assignments in Canvas LMS.'
    out = _fmt(raw)
    assert not out.startswith('How do I submit')
    assert 'Students can submit' in out
