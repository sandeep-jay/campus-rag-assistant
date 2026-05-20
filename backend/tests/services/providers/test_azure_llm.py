"""Azure LLM provider wiring tests."""

from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from backend.app.services.providers.llm.azure import AzureLlmProvider


def test_azure_llm_get_llm_wiring():
    fake_llm = MagicMock()
    with (
        patch('backend.app.services.providers.llm.azure.settings') as s,
        patch(
            'backend.app.services.providers.llm.azure.AzureChatOpenAI',
            return_value=fake_llm,
        ) as ctor,
    ):
        s.AZURE_OPENAI_ENDPOINT = 'https://x.openai.azure.com/'
        s.AZURE_OPENAI_API_KEY = SecretStr('k')
        s.AZURE_OPENAI_DEPLOYMENT = 'gpt-4o'
        s.AZURE_OPENAI_API_VERSION = '2024-02-01'
        s.TEMPERATURE = 0.2
        s.MAX_TOKENS = 123
        p = AzureLlmProvider()
        out = p.get_llm()
        assert out is fake_llm
        ctor.assert_called_once()
        kwargs = ctor.call_args.kwargs
        assert kwargs['azure_deployment'] == 'gpt-4o'
        assert kwargs['api_version'] == '2024-02-01'
        assert kwargs['temperature'] == 0.2
        assert kwargs['max_tokens'] == 123
