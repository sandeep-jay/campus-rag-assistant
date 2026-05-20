"""Azure OpenAI chat LLM provider."""

from langchain_openai import AzureChatOpenAI

from backend.app.core.config_manager import settings
from backend.app.services.providers.base import BaseLlmProvider


class AzureLlmProvider(BaseLlmProvider):
    name = 'azure'

    def __init__(self) -> None:
        self._validate_config()

    def _validate_config(self) -> None:
        missing = []
        for key in (
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_DEPLOYMENT',
            'AZURE_OPENAI_API_VERSION',
        ):
            if not getattr(settings, key, None):
                missing.append(key)
        if missing:
            raise ValueError(f'Azure LLM missing config: {missing}')

    def _llm_kwargs(self, streaming: bool = False, callbacks: list | None = None) -> dict:  # noqa: FBT001
        kwargs = dict(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            azure_endpoint=str(settings.AZURE_OPENAI_ENDPOINT).rstrip('/'),
            api_key=(settings.AZURE_OPENAI_API_KEY.get_secret_value() if settings.AZURE_OPENAI_API_KEY else None),
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
        )
        if streaming:
            kwargs['streaming'] = True
        if callbacks:
            kwargs['callbacks'] = callbacks
        return kwargs

    def get_llm(self):
        return AzureChatOpenAI(**self._llm_kwargs())

    def get_streaming_llm(self, callbacks: list | None = None):
        return AzureChatOpenAI(**self._llm_kwargs(streaming=True, callbacks=callbacks))
