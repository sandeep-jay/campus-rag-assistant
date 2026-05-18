"""Tenant-aware RAG prompt and behavior configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from backend.app.core.config_manager import settings

_PLACEHOLDER_ASSISTANT = '{{assistant_name}}'
_PLACEHOLDER_TOPICS = '{{supported_topics}}'
_PLACEHOLDER_OUT_OF_SCOPE = '{{out_of_scope_message}}'


@dataclass(frozen=True)
class TenantRagConfig:
    assistant_name: str
    supported_topics: str
    out_of_scope_message: str
    few_shot_examples: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_settings(cls) -> TenantRagConfig:
        return cls(
            assistant_name=getattr(settings, 'ASSISTANT_NAME', 'EdTech Support Assistant'),
            supported_topics=getattr(
                settings,
                'SUPPORTED_TOPICS',
                "your organization's learning platform, integrations, and support documentation",
            ),
            out_of_scope_message=getattr(
                settings,
                'OUT_OF_SCOPE_MESSAGE',
                (
                    'I can only answer questions covered by the knowledge base for '
                    '{{supported_topics}}. Please ask a question related to those topics.'
                ),
            ),
            few_shot_examples=[],
        )

    @classmethod
    def from_tenant(cls, tenant: Any, *, fallback: TenantRagConfig | None = None) -> TenantRagConfig:
        base = fallback or cls.from_settings()
        raw = getattr(tenant, 'rag_config', None) or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = {}
        if not isinstance(raw, dict):
            raw = {}

        few_shots = raw.get('few_shot_examples', base.few_shot_examples)
        if not isinstance(few_shots, list):
            few_shots = base.few_shot_examples

        return cls(
            assistant_name=str(raw.get('assistant_name') or base.assistant_name),
            supported_topics=str(raw.get('supported_topics') or base.supported_topics),
            out_of_scope_message=str(raw.get('out_of_scope_message') or base.out_of_scope_message),
            few_shot_examples=few_shots,
        )

    def hydrate_text(self, text: str) -> str:
        """Replace {{placeholders}} without touching LangChain {context}/{question} braces."""
        replacements = {
            _PLACEHOLDER_ASSISTANT: self.assistant_name,
            _PLACEHOLDER_TOPICS: self.supported_topics,
            _PLACEHOLDER_OUT_OF_SCOPE: self._hydrated_out_of_scope(),
        }
        for token, value in replacements.items():
            text = text.replace(token, value)
        return text

    def _hydrated_out_of_scope(self) -> str:
        msg = self.out_of_scope_message
        if _PLACEHOLDER_TOPICS in msg:
            msg = msg.replace(_PLACEHOLDER_TOPICS, self.supported_topics)
        return msg


def load_tenant_rag_config(tenant: Any | None) -> TenantRagConfig:
    if tenant is None:
        return TenantRagConfig.from_settings()
    return TenantRagConfig.from_tenant(tenant)
