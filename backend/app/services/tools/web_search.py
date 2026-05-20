"""Web search tool for opt-in research_mode=web."""

from __future__ import annotations

import logging

from langchain.schema import Document

from backend.app.core.config_manager import settings

logger = logging.getLogger(__name__)

WEB_DISCLAIMER_SOURCE = 'web-search'


def _mock_web_documents(query: str) -> list[Document]:
    return [
        Document(
            page_content=(f'Mock web snippet for: {query}. ' 'Configure WEB_SEARCH_PROVIDER=tavily and TAVILY_API_KEY for live results.'),
            metadata={
                'source': 'example.com',
                'source_metadata': {
                    'source': 'example.com',
                    'kb_url': 'https://example.com/search-result',
                    'kb_number': 'WEB-001',
                    'kb_category': 'Web',
                    'short_description': f'Mock result for {query[:60]}',
                    'project': 'web-research',
                    'ingestion_date': '',
                },
            },
        ),
    ]


def _tavily_documents(query: str) -> list[Document]:
    api_key_field = getattr(settings, 'TAVILY_API_KEY', None)
    if not api_key_field:
        logger.warning('TAVILY_API_KEY not set; falling back to mock web search')
        return _mock_web_documents(query)
    # TAVILY_API_KEY is typed as SecretStr in Settings; unwrap once.
    api_key = api_key_field.get_secret_value() if hasattr(api_key_field, 'get_secret_value') else str(api_key_field)
    try:
        from tavily import TavilyClient
    except ImportError as e:
        logger.warning('tavily package not installed: %s', e)
        return _mock_web_documents(query)

    max_results = int(getattr(settings, 'WEB_SEARCH_MAX_RESULTS', 5) or 5)
    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=max_results)
    results = response.get('results') or []
    documents: list[Document] = []
    for item in results[:max_results]:
        url = item.get('url') or '#'
        title = item.get('title') or url
        content = item.get('content') or ''
        documents.append(
            Document(
                page_content=content,
                metadata={
                    'source': url,
                    'source_metadata': {
                        'source': url,
                        'kb_url': url,
                        'kb_number': 'WEB',
                        'kb_category': 'Web',
                        'short_description': title,
                        'project': WEB_DISCLAIMER_SOURCE,
                        'ingestion_date': '',
                    },
                },
            ),
        )
    return documents or _mock_web_documents(query)


def web_search_documents(query: str) -> list[Document]:
    provider = (getattr(settings, 'WEB_SEARCH_PROVIDER', None) or 'mock').strip().lower()
    if provider == 'tavily':
        return _tavily_documents(query)
    return _mock_web_documents(query)
