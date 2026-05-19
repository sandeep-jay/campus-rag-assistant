"""Tests for log redaction helpers."""

from backend.app.core.log_redaction import jwt_subject_for_log, query_log_preview


def test_query_log_preview_hashes_and_truncates() -> None:
    long_q = 'x' * 200
    summary = query_log_preview(long_q)
    assert 'len=200' in summary
    assert 'sha256=' in summary
    assert '…' in summary
    assert long_q not in summary


def test_query_log_preview_empty() -> None:
    assert query_log_preview('') == 'len=0'


def test_jwt_subject_for_log() -> None:
    assert jwt_subject_for_log({'sub': 'alice'}) == 'alice'
    assert jwt_subject_for_log({}) == '<no-sub>'
    assert jwt_subject_for_log(None) == '<invalid>'
