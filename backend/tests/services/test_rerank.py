"""Tests for document reranking."""

from unittest.mock import patch

from langchain.schema import Document

from backend.app.services.rerank import rerank_documents


@patch('backend.app.services.rerank.settings')
def test_rerank_disabled_returns_slice(mock_settings):
    mock_settings.RERANK_ENABLED = False
    docs = [Document(page_content='a'), Document(page_content='b')]
    assert rerank_documents('q', docs, top_n=1) == docs[:1]


@patch('backend.app.services.rerank.settings')
def test_rerank_keyword_orders_by_overlap(mock_settings):
    mock_settings.RERANK_ENABLED = True
    mock_settings.RERANK_BACKEND = 'keyword'
    mock_settings.RERANK_TOP_N = 2
    mock_settings.RERANK_PREFILTER_MAX = 12
    mock_settings.RERANK_MIN_KEYWORD_OVERLAP = 0
    docs = [
        Document(page_content='unrelated content about cats'),
        Document(page_content='Canvas LMS Kaltura embed media Rich Content Editor'),
        Document(page_content='another random doc'),
    ]
    result = rerank_documents('How do I embed Kaltura in Canvas LMS?', docs)
    assert len(result) == 2
    assert 'Kaltura' in result[0].page_content


@patch('backend.app.services.rerank.settings')
def test_rerank_flashrank_fallback_to_keyword_on_import_error(mock_settings):
    mock_settings.RERANK_ENABLED = True
    mock_settings.RERANK_BACKEND = 'flashrank'
    mock_settings.RERANK_TOP_N = 1
    docs = [
        Document(page_content='noise'),
        Document(page_content='Gradescope assignment Canvas LMS gradebook'),
    ]

    with patch('backend.app.services.rerank._rerank_flashrank', side_effect=ImportError('no flashrank')):
        result = rerank_documents('Gradescope Canvas LMS assignment', docs)
    assert len(result) == 1
    assert 'Gradescope' in result[0].page_content
