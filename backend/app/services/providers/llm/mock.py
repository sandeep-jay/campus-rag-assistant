"""Mock LLM provider (RAGService uses full mock path when either side is mock)."""

from backend.app.services.providers.base import BaseLlmProvider


class MockLlmProvider(BaseLlmProvider):
    name = 'mock'
    is_mock = True

    def get_llm(self):
        raise NotImplementedError('MockLlmProvider does not expose an LLM')
