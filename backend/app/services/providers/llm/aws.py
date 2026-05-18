"""AWS Bedrock LLM provider."""

from backend.app.services.bedrock import BedrockService
from backend.app.services.providers.base import BaseLlmProvider


class AwsLlmProvider(BaseLlmProvider):
    name = 'aws'

    def __init__(self, bedrock_service: BedrockService | None = None, bedrock_client=None) -> None:
        if bedrock_service is not None:
            self._bedrock = bedrock_service
        elif bedrock_client is not None:
            self._bedrock = BedrockService(bedrock_client=bedrock_client)
        else:
            self._bedrock = BedrockService()

    def get_llm(self):
        return self._bedrock.get_llm()

    def get_streaming_llm(self, callbacks: list | None = None):
        return self._bedrock.get_streaming_llm(callbacks=callbacks)
