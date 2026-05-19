"""Execute the compiled RAG graph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.app.services.graph.graph import build_rag_graph
from backend.app.services.tenant_rag_config import TenantRagConfig

if TYPE_CHECKING:
    from backend.app.services.rag import RAGService


def run_rag_graph(
    rag_service: RAGService,
    query: str,
    chat_history: list | None = None,
    tenant_config: TenantRagConfig | None = None,
    research_mode: str = 'kb',
) -> dict[str, Any]:
    if chat_history is None:
        chat_history = []
    mode = (research_mode or 'kb').lower()
    if mode not in ('kb', 'web'):
        mode = 'kb'

    graph = build_rag_graph(rag_service, tenant_config)
    initial_state = {
        'question': query,
        'chat_history': chat_history,
        'research_mode': mode,
    }
    final_state = graph.invoke(initial_state)
    return {
        'message': final_state.get('message', ''),
        'metadata': final_state.get('metadata', {'sources': [], 'document_contents': []}),
    }
