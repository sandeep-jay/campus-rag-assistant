"""OAuth handoff one-time code store."""

from backend.app.services.oauth_handoff import consume_handoff_code, create_handoff_code


def test_handoff_round_trip():
    code = create_handoff_code('jwt-token-abc')
    assert consume_handoff_code(code) == 'jwt-token-abc'
    assert consume_handoff_code(code) is None


def test_handoff_invalid_code():
    assert consume_handoff_code('not-a-valid-code') is None
