"""Mock retriever provider."""

from backend.app.services.providers.base import BaseRetrieverProvider


class MockRetrieverProvider(BaseRetrieverProvider):
    name = 'mock'
    is_mock = True

    def get_retriever(self):
        raise NotImplementedError('MockRetrieverProvider does not expose a retriever')
