"""Tests for Phase 5 retrieval helpers."""

from unittest.mock import MagicMock, patch

from langchain.schema import Document

from backend.app.services.retrieval import (
    expand_search_queries,
    fuse_documents,
    retrieve_with_queries,
)


def test_fuse_documents_dedupes_by_content():
    a = Document(page_content='same text', metadata={'source': 'a'})
    b = Document(page_content='same text', metadata={'source': 'b'})
    c = Document(page_content='other', metadata={'source': 'c'})
    merged = fuse_documents([a, b], [c])
    assert len(merged) == 2


@patch('backend.app.services.retrieval.settings')
def test_expand_search_queries_disabled(mock_settings):
    mock_settings.MULTI_QUERY_ENABLED = False
    rag = MagicMock()
    assert expand_search_queries(rag, 'How do I use Kaltura?') == ['How do I use Kaltura?']


@patch('backend.app.services.retrieval.settings')
def test_expand_search_queries_with_llm(mock_settings):
    mock_settings.MULTI_QUERY_ENABLED = True
    mock_settings.MULTI_QUERY_COUNT = 2
    rag = MagicMock()
    rag.llm.invoke.return_value = 'Kaltura embed Canvas LMS\nRich Content Editor media'
    rag._extract_answer_text.return_value = 'Kaltura embed Canvas LMS\nRich Content Editor media'
    queries = expand_search_queries(rag, 'How do I embed Kaltura in Canvas LMS?')
    assert queries[0] == 'How do I embed Kaltura in Canvas LMS?'
    assert len(queries) >= 2


def test_retrieve_with_queries_merges():
    retriever = MagicMock()
    retriever.invoke.side_effect = [
        [Document(page_content='doc one')],
        [Document(page_content='doc two')],
    ]
    docs = retrieve_with_queries(retriever, ['q1', 'q2'])
    assert len(docs) == 2
    assert retriever.invoke.call_count == 2


def test_fuse_rrf_orders_higher_rank_first():
    a = Document(page_content='first', metadata={})
    b = Document(page_content='second', metadata={})
    fused = fuse_documents([a, b], [b])
    assert fused[0].page_content == 'second'
