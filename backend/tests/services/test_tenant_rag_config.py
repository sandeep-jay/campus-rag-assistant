"""Tests for tenant RAG configuration hydration."""

from backend.app.services.tenant_rag_config import TenantRagConfig


class _FakeTenant:
    def __init__(self, rag_config):
        self.rag_config = rag_config


def test_from_settings_hydrates_placeholders():
    config = TenantRagConfig(
        assistant_name='Test Bot',
        supported_topics='LMS and grading',
        out_of_scope_message='Only {{supported_topics}} please.',
    )
    text = config.hydrate_text('Hello {{assistant_name}}. Topics: {{supported_topics}}.')
    assert 'Test Bot' in text
    assert 'LMS and grading' in text
    assert '{{' not in text


def test_from_tenant_overrides_settings_fields():
    tenant = _FakeTenant(
        {
            'assistant_name': 'Campus Bot',
            'supported_topics': 'Canvas LMS',
            'out_of_scope_message': 'Ask about Canvas LMS only.',
        },
    )
    config = TenantRagConfig.from_tenant(tenant)
    assert config.assistant_name == 'Campus Bot'
    assert config.supported_topics == 'Canvas LMS'


def test_from_tenant_few_shot_examples():
    tenant = _FakeTenant({'few_shot_examples': [{'input': 'q', 'output': ['a']}]})
    config = TenantRagConfig.from_tenant(tenant)
    assert len(config.few_shot_examples) == 1
