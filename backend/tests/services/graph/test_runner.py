"""LangGraph RAG runner tests (mocked providers)."""

from unittest.mock import MagicMock, patch

import pytest
from langchain.schema import Document

from backend.app.services.graph.runner import run_rag_graph
from backend.app.services.rag import RAGService


@pytest.fixture()
def graph_rag_mocks():
    mock_llm = MagicMock()
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [
        Document(page_content="KB doc one", metadata={"source": "kb-1", "kb_url": "https://kb/1"}),
    ]
    mock_llm.invoke.side_effect = [
        "standalone question",
        "Answer from knowledge base.",
    ]

    mock_llm_provider = MagicMock()
    mock_llm_provider.is_mock = False
    mock_llm_provider.name = "aws"
    mock_llm_provider.get_llm.return_value = mock_llm

    mock_ret_provider = MagicMock()
    mock_ret_provider.is_mock = False
    mock_ret_provider.name = "aws"
    mock_ret_provider.get_retriever.return_value = mock_retriever

    patchers = [
        patch("backend.app.services.rag.get_llm_provider", return_value=mock_llm_provider),
        patch("backend.app.services.rag.get_retriever_provider", return_value=mock_ret_provider),
        patch("backend.app.services.rag.settings") as mock_settings,
    ]
    started = [p.start() for p in patchers]
    mock_settings.RAG_FORCE_MOCK = False
    mock_settings.RAG_ENGINE = "langgraph"
    mock_settings.WEB_RESEARCH_ENABLED = False
    mock_settings.LANGCHAIN_API_KEY = None

    yield mock_llm, mock_retriever

    for p in patchers:
        p.stop()


def test_run_rag_graph_kb_path(graph_rag_mocks):
    from backend.app.services import rag as rag_mod

    rag_mod._rag_service_instance = None
    service = RAGService()
    result = run_rag_graph(
        service,
        "How do I reset my password?",
        chat_history=[],
        research_mode="kb",
    )
    assert result["message"]
    assert result["metadata"].get("source_kind") == "kb"
    assert "sources" in result["metadata"]


@patch("backend.app.services.graph.nodes.settings")
def test_run_rag_graph_web_path(mock_node_settings, graph_rag_mocks):
    mock_node_settings.WEB_RESEARCH_ENABLED = True
    from backend.app.services import rag as rag_mod

    rag_mod._rag_service_instance = None
    service = RAGService()
    result = run_rag_graph(
        service,
        "FERPA updates",
        chat_history=[],
        research_mode="web",
    )
    assert result["metadata"].get("source_kind") == "web"
    assert result["metadata"].get("disclaimer")
