"""Document reranking for RAG retrieval (FlashRank or lightweight keyword fallback)."""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from backend.app.core.config_manager import settings

logger = logging.getLogger(__name__)


def _int_setting(name: str, default: int) -> int:
    raw = getattr(settings, name, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


_TOKEN_RE = re.compile(r'[a-z0-9]+', re.IGNORECASE)
_RANKER = None


def is_rerank_enabled() -> bool:
    return bool(getattr(settings, 'RERANK_ENABLED', False))


def retrieval_candidate_count() -> int:
    """How many documents to fetch from the retriever before reranking."""
    if is_rerank_enabled():
        return int(getattr(settings, 'RERANK_CANDIDATE_K', 10) or 10)
    return int(getattr(settings, 'RETRIEVER_NUMBER_OF_RESULTS', 3) or 3)


def rerank_top_n() -> int:
    return int(getattr(settings, 'RERANK_TOP_N', 3) or 3)


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or '') if len(t) > 2}


def _keyword_score(query: str, doc) -> int:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0
    content = getattr(doc, 'page_content', str(doc))
    return len(q_tokens & _tokenize(content))


def prefilter_for_rerank(query: str, documents: list) -> list:
    """Trim fused candidates before expensive rerank (precision)."""
    max_docs = _int_setting('RERANK_PREFILTER_MAX', 12)
    if len(documents) <= max_docs:
        return documents
    ranked = sorted(documents, key=lambda d: _keyword_score(query, d), reverse=True)
    min_hits = _int_setting('RERANK_MIN_KEYWORD_OVERLAP', 1)
    if min_hits > 0:
        with_overlap = [d for d in ranked if _keyword_score(query, d) >= min_hits]
        if len(with_overlap) >= rerank_top_n():
            ranked = with_overlap
    trimmed = ranked[:max_docs]
    logger.info('Rerank prefilter: %s -> %s documents', len(documents), len(trimmed))
    return trimmed


def _rerank_keyword(query: str, documents: list, top_n: int) -> list:
    ranked = sorted(documents, key=lambda d: _keyword_score(query, d), reverse=True)
    return ranked[:top_n]


@lru_cache(maxsize=1)
def _get_flashrank_ranker():
    from flashrank import Ranker

    model_name = getattr(settings, 'RERANK_MODEL', None) or 'ms-marco-MiniLM-L-12-v2'
    logger.info('Loading FlashRank model: %s', model_name)
    return Ranker(model_name=model_name, cache_dir=None)


def _rerank_flashrank(query: str, documents: list, top_n: int) -> list:
    from flashrank import RerankRequest

    ranker = _get_flashrank_ranker()
    passages = [{'id': str(i), 'text': getattr(d, 'page_content', str(d))} for i, d in enumerate(documents)]
    results = ranker.rerank(RerankRequest(query=query, passages=passages))
    by_id = {int(r['id']): r.score for r in results}
    order = sorted(range(len(documents)), key=lambda i: by_id.get(i, 0.0), reverse=True)
    return [documents[i] for i in order[:top_n]]


def rerank_documents(query: str, documents: list, top_n: int | None = None) -> list:
    """Return top-N documents reordered by relevance to the query."""
    if not documents:
        return []
    if not is_rerank_enabled():
        limit = top_n or len(documents)
        return documents[:limit]

    limit = top_n or rerank_top_n()
    if len(documents) <= limit:
        return documents

    documents = prefilter_for_rerank(query, documents)
    if len(documents) <= limit:
        return documents

    backend = (getattr(settings, 'RERANK_BACKEND', None) or 'flashrank').strip().lower()
    try:
        if backend == 'flashrank':
            return _rerank_flashrank(query, documents, limit)
    except ImportError:
        logger.warning('flashrank not installed; falling back to keyword rerank')
    except Exception as exc:
        logger.warning('FlashRank rerank failed (%s); falling back to keyword rerank', exc)

    return _rerank_keyword(query, documents, limit)
