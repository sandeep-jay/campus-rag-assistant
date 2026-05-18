"""Tests for Bedrock model ID / inference profile resolution."""

from backend.app.services.bedrock_model_id import resolve_bedrock_model_id


def test_resolve_claude_35_haiku_us_west():
    raw = 'anthropic.claude-3-5-haiku-20241022-v1:0'
    assert resolve_bedrock_model_id(raw, 'us-west-2') == 'us.anthropic.claude-3-5-haiku-20241022-v1:0'


def test_resolve_leaves_profile_id_unchanged():
    profile = 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
    assert resolve_bedrock_model_id(profile, 'us-west-2') == profile


def test_resolve_legacy_claude_unchanged():
    assert resolve_bedrock_model_id('anthropic.claude-3-sonnet-20240229-v1:0', 'us-east-1') == ('anthropic.claude-3-sonnet-20240229-v1:0')
