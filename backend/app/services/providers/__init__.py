"""RAG LLM and retriever provider registries (config-driven)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.core.config_manager import settings

from .llm.aws import AwsLlmProvider
from .llm.azure import AzureLlmProvider
from .llm.mock import MockLlmProvider
from .retriever.aws import AwsRetrieverProvider
from .retriever.azure import AzureRetrieverProvider
from .retriever.mock import MockRetrieverProvider

if TYPE_CHECKING:
    from collections.abc import Callable

    from .base import BaseLlmProvider, BaseRetrieverProvider

_LLM_REGISTRY: dict[str, Callable[[], BaseLlmProvider]] = {}
_RET_REGISTRY: dict[str, Callable[[], BaseRetrieverProvider]] = {}


def register_llm(name: str, factory: Callable[[], BaseLlmProvider]) -> None:
    _LLM_REGISTRY[name.strip().lower()] = factory


def register_retriever(name: str, factory: Callable[[], BaseRetrieverProvider]) -> None:
    _RET_REGISTRY[name.strip().lower()] = factory


def _resolve_name(side_default: str, side_var: str) -> str:
    if getattr(settings, 'RAG_FORCE_MOCK', False):
        return 'mock'
    shortcut = getattr(settings, 'RAG_PROVIDER', None)
    if shortcut is not None and str(shortcut).strip():
        return str(shortcut).strip().lower()
    val = getattr(settings, side_var, None) or side_default
    return str(val).strip().lower()


def get_llm_provider() -> BaseLlmProvider:
    name = _resolve_name('mock', 'LLM_PROVIDER')
    factory = _LLM_REGISTRY.get(name)
    if factory is None:
        return MockLlmProvider()
    return factory()


def get_retriever_provider() -> BaseRetrieverProvider:
    name = _resolve_name('mock', 'RETRIEVER_PROVIDER')
    factory = _RET_REGISTRY.get(name)
    if factory is None:
        return MockRetrieverProvider()
    return factory()


register_llm('aws', lambda: AwsLlmProvider.create_or_mock(MockLlmProvider))
register_llm('azure', lambda: AzureLlmProvider.create_or_mock(MockLlmProvider))
register_llm('mock', MockLlmProvider)

register_retriever('aws', lambda: AwsRetrieverProvider.create_or_mock(MockRetrieverProvider))
register_retriever('azure', lambda: AzureRetrieverProvider.create_or_mock(MockRetrieverProvider))
register_retriever('mock', MockRetrieverProvider)
