"""Provider base classes for decoupled LLM and retriever selection."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class _ProviderBase:
    """Shared provider metadata and safe fallback to mock."""

    name: str = 'base'
    is_mock: bool = False

    @classmethod
    def create_or_mock(cls, mock_cls: type[Any], **kwargs: Any) -> Any:
        try:
            return cls(**kwargs)
        except Exception as e:
            logger.warning('%s init failed (%s); falling back to %s', cls.__name__, e, mock_cls.__name__)
            return mock_cls()


class BaseLlmProvider(_ProviderBase, ABC):
    @abstractmethod
    def get_llm(self):
        """Return a LangChain-compatible chat/completion model."""

    def get_streaming_llm(self, _callbacks: list | None = None):
        """Return a streaming-enabled variant of the LLM with the given callbacks.

        Returns None if the provider does not support streaming — callers should
        fall back to fake-streaming the buffered process_query result.
        """


class BaseRetrieverProvider(_ProviderBase, ABC):
    @abstractmethod
    def get_retriever(self):
        """Return a LangChain BaseRetriever."""
