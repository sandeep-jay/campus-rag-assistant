"""Deterministic tools for the helpdesk agent."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import httpx
from langchain.schema import Document

from backend.app.core.config_manager import settings
from backend.app.core.metrics import HELPDESK_AGENT_TOOL_TOTAL
from backend.app.services.helpdesk.github import create_github_issue
from backend.app.services.helpdesk_graph.state import GitHubIssue, HelpdeskState
from backend.app.services.helpdesk_graph.tracing import trace_agent_tool
from backend.app.services.retrieval import apply_client_metadata_filter, retrieve_with_queries
from backend.app.services.tools.web_search import web_search_documents

if TYPE_CHECKING:
    from backend.app.schemas.helpdesk import CreateIssueResponse, TicketDraft
    from backend.app.services.rag import RAGService

logger = logging.getLogger(__name__)


def _github_token_and_repo() -> tuple[str, str] | None:
    token_secret = settings.GITHUB_TOKEN
    repo = settings.GITHUB_REPO
    if not token_secret or not repo:
        return None
    return token_secret.get_secret_value(), repo


def _normalize_query(query: str) -> str:
    return ' '.join((query or '').split()).strip().lower()[:256]


def _cache_get(state: HelpdeskState | None, tool: str, query: str) -> list[Document] | None:
    if state is None:
        return None
    cache = state.setdefault('tool_cache', {})
    cached = cache.get(f'{tool}:{_normalize_query(query)}')
    if cached is None:
        return None
    return [Document(**doc) if isinstance(doc, dict) else doc for doc in cached]


def _cache_put(state: HelpdeskState | None, tool: str, query: str, documents: list[Document]) -> None:
    if state is None:
        return
    cache = state.setdefault('tool_cache', {})
    cache[f'{tool}:{_normalize_query(query)}'] = [doc.model_dump() for doc in documents]


def _truncate_documents(documents: list[Document]) -> list[Document]:
    max_chars = max(1, int(getattr(settings, 'HELPDESK_AGENT_TOOL_OUTPUT_MAX_CHARS', 4000) or 4000))
    truncated: list[Document] = []
    for doc in documents:
        content = (doc.page_content or '')[:max_chars]
        meta = dict(doc.metadata or {})
        if len(doc.page_content or '') > max_chars:
            meta['truncated'] = True
        truncated.append(Document(page_content=content, metadata=meta))
    return truncated


async def _run_with_timeout(func, *, timeout: float):
    return await asyncio.wait_for(asyncio.to_thread(func), timeout=timeout)


@trace_agent_tool('helpdesk_agent.retry_kb')
async def retry_kb(query: str, *, rag_service: RAGService, state: HelpdeskState | None = None) -> list[Document]:  # noqa: PLR0911
    """Run a retrieval-only KB retry without generating an answer."""
    tool = 'retry_kb'
    cleaned = _normalize_query(query)
    if not settings.HELPDESK_AGENT_TOOL_KB_RETRY:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='skipped', reason='disabled').inc()
        return []
    if not cleaned:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='skipped', reason='empty_query').inc()
        return []

    cached = _cache_get(state, tool, cleaned)
    if cached is not None:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='cached', reason='ok').inc()
        return cached

    if getattr(rag_service, 'is_mock', False):
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='mock', reason='provider_mock').inc()
        documents = [
            Document(
                page_content=f'Mock KB retry result for: {query}',
                metadata={'source': 'mock-kb', 'source_metadata': {'short_description': 'Mock KB retry result'}},
            )
        ]
        _cache_put(state, tool, cleaned, documents)
        return documents

    retriever = getattr(rag_service, 'retriever', None)
    if retriever is None:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='skipped', reason='missing_retriever').inc()
        return []

    timeout = float(getattr(settings, 'HELPDESK_AGENT_KB_RETRY_TIMEOUT_SECONDS', 12.0) or 12.0)

    def _retrieve() -> list[Document]:
        docs = retrieve_with_queries(retriever, [cleaned])
        docs = apply_client_metadata_filter(docs)
        return _truncate_documents(docs)

    try:
        documents = await _run_with_timeout(_retrieve, timeout=timeout)
    except TimeoutError:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='timeout', reason='timeout').inc()
        logger.warning('Helpdesk KB retry timed out')
        return []
    except Exception as exc:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='error', reason=exc.__class__.__name__).inc()
        logger.warning('Helpdesk KB retry failed: %s', exc)
        return []

    HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='success', reason='ok').inc()
    _cache_put(state, tool, cleaned, documents)
    return documents


@trace_agent_tool('helpdesk_agent.web_search')
async def web_search(query: str, *, state: HelpdeskState | None = None) -> list[Document]:
    """Run the configured web-search provider with timeout and in-session cache."""
    tool = 'web_search'
    cleaned = _normalize_query(query)
    if not settings.HELPDESK_AGENT_TOOL_WEB_SEARCH:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='skipped', reason='disabled').inc()
        return []
    if not cleaned:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='skipped', reason='empty_query').inc()
        return []

    cached = _cache_get(state, tool, cleaned)
    if cached is not None:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='cached', reason='ok').inc()
        return cached

    timeout = float(getattr(settings, 'HELPDESK_AGENT_WEB_SEARCH_TIMEOUT_SECONDS', 10.0) or 10.0)
    try:
        documents = await _run_with_timeout(lambda: _truncate_documents(web_search_documents(cleaned)), timeout=timeout)
    except TimeoutError:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='timeout', reason='timeout').inc()
        logger.warning('Helpdesk web search timed out')
        return []
    except Exception as exc:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='error', reason=exc.__class__.__name__).inc()
        logger.warning('Helpdesk web search failed: %s', exc)
        return []

    HELPDESK_AGENT_TOOL_TOTAL.labels(tool=tool, outcome='success', reason='ok').inc()
    _cache_put(state, tool, cleaned, documents)
    return documents


@trace_agent_tool('helpdesk_agent.search_existing_issues')
async def search_existing_issues(
    query: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    limit: int = 3,
) -> list[GitHubIssue]:
    """Search the configured GitHub repo for likely duplicate issues.

    Failure is non-fatal: the supervisor can still draft a new ticket.
    """
    if not settings.HELPDESK_AGENT_TOOL_GITHUB_SEARCH:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool='search_existing_issues', outcome='skipped', reason='disabled').inc()
        return []

    config = _github_token_and_repo()
    if config is None:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool='search_existing_issues', outcome='skipped', reason='missing_config').inc()
        return []

    token, repo = config
    cleaned = ' '.join(query.split())[:256]
    if not cleaned:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool='search_existing_issues', outcome='skipped', reason='empty_query').inc()
        return []

    params = {'q': f'repo:{repo} is:issue {cleaned}', 'per_page': str(limit)}
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'campus-rag-assistant-helpdesk-agent',
    }
    timeout = float(getattr(settings, 'HELPDESK_AGENT_GITHUB_SEARCH_TIMEOUT_SECONDS', 8.0) or 8.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
            response = await client.get('https://api.github.com/search/issues', headers=headers, params=params)
    except httpx.HTTPError as exc:
        HELPDESK_AGENT_TOOL_TOTAL.labels(tool='search_existing_issues', outcome='error', reason=exc.__class__.__name__).inc()
        logger.warning('GitHub duplicate search failed: %s', exc)
        return []

    if response.status_code >= 400:
        HELPDESK_AGENT_TOOL_TOTAL.labels(
            tool='search_existing_issues',
            outcome='error',
            reason=f'http_{response.status_code}',
        ).inc()
        logger.warning('GitHub duplicate search rejected: status=%s', response.status_code)
        return []

    data: dict[str, Any] = response.json()
    issues: list[GitHubIssue] = []
    for item in data.get('items', [])[:limit]:
        issues.append(
            GitHubIssue(
                number=int(item.get('number') or 0),
                title=str(item.get('title') or 'Untitled issue'),
                state=str(item.get('state') or 'open'),
                url=str(item.get('html_url') or ''),
                body=item.get('body'),
            )
        )

    HELPDESK_AGENT_TOOL_TOTAL.labels(tool='search_existing_issues', outcome='success', reason='ok').inc()
    return issues


@trace_agent_tool('helpdesk_agent.file_ticket')
async def file_ticket(draft: TicketDraft, *, user_id: int | str) -> CreateIssueResponse:
    """HITL-gated issue creation wrapper for future `/agent/confirm`."""
    HELPDESK_AGENT_TOOL_TOTAL.labels(tool='file_ticket', outcome='started', reason='hitl_confirmed').inc()
    return await create_github_issue(draft, user_id=user_id)
