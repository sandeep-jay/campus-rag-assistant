"""Build and compile the RAG LangGraph."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from backend.app.services.graph.nodes import (
    make_condense_node,
    make_format_node,
    make_generate_node,
    make_multi_query_node,
    make_rerank_node,
    make_retrieve_node,
    make_web_search_node,
    route_research_mode,
)
from backend.app.services.graph.state import RagState

if TYPE_CHECKING:
    from backend.app.services.rag import RAGService


def build_rag_graph(rag_service: RAGService, tenant_config=None):
    graph = StateGraph(RagState)
    graph.add_node('condense', make_condense_node(rag_service, tenant_config))
    graph.add_node('multi_query', make_multi_query_node(rag_service))
    graph.add_node('retrieve', make_retrieve_node(rag_service))
    graph.add_node('rerank', make_rerank_node())
    graph.add_node('web_search', make_web_search_node(rag_service))
    graph.add_node('generate', make_generate_node(rag_service, tenant_config))
    graph.add_node('format', make_format_node(rag_service, tenant_config))

    graph.add_edge(START, 'condense')
    graph.add_conditional_edges('condense', route_research_mode, {'multi_query': 'multi_query', 'web_search': 'web_search'})
    graph.add_edge('multi_query', 'retrieve')
    graph.add_edge('retrieve', 'rerank')
    graph.add_edge('rerank', 'generate')
    graph.add_edge('web_search', 'generate')
    graph.add_edge('generate', 'format')
    graph.add_edge('format', END)
    return graph.compile()
