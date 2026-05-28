"""Phase 5 retrieval helpers: multi-query expansion, fusion, metadata filters."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Any

from langchain.prompts import PromptTemplate
from langchain.schema import Document

from backend.app.core.config_manager import settings

if TYPE_CHECKING:
    from backend.app.services.rag import RAGService

logger = logging.getLogger(__name__)

MULTI_QUERY_TEMPLATE = """You help improve search over a campus EdTech knowledge base (Canvas LMS, Kaltura, Gradescope, Ally, etc.).

Given the user question, write {count} short alternative search queries for the same information need.
One query per line. No numbering or bullets.

Question: {question}

Alternative queries:"""


def is_multi_query_enabled() -> bool:
    return bool(getattr(settings, 'MULTI_QUERY_ENABLED', False))


def multi_query_variant_count() -> int:
    """Number of extra queries to generate (standalone is always included)."""
    return max(0, int(getattr(settings, 'MULTI_QUERY_COUNT', 2) or 2))


def is_metadata_filter_enabled() -> bool:
    return bool(getattr(settings, 'METADATA_FILTER_ENABLED', False))


def is_post_metadata_filter_enabled() -> bool:
    return bool(getattr(settings, 'METADATA_FILTER_CLIENT_ENABLED', False))


def _doc_dedupe_key(doc: Document) -> str:
    text = (doc.page_content or '').strip()
    if len(text) > 200:
        text = text[:200]
    return 'content:' + hashlib.sha256(text.encode()).hexdigest()[:16]


def _int_setting(name: str, default: int) -> int:
    raw = getattr(settings, name, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _rrf_k() -> int:
    return _int_setting('RERANK_RRF_K', 60)


def fuse_documents(*doc_lists: list[Document]) -> list[Document]:
    """Merge lists with reciprocal rank fusion (dedupe by content)."""
    scores: dict[str, float] = {}
    doc_by_key: dict[str, Document] = {}
    k = _rrf_k()
    for docs in doc_lists:
        for rank, doc in enumerate(docs):
            key = _doc_dedupe_key(doc)
            doc_by_key[key] = doc
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    ordered_keys = sorted(scores.keys(), key=lambda key: scores[key], reverse=True)
    return [doc_by_key[key] for key in ordered_keys]


def _parse_query_lines(text: str, limit: int) -> list[str]:
    lines: list[str] = []
    for raw in (text or '').splitlines():
        line = raw.strip().lstrip('0123456789.-) ').strip()
        if line and len(line) > 8:
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def expand_search_queries(rag_service: RAGService, standalone_question: str) -> list[str]:
    """Return [standalone, ...variants] for multi-query retrieval."""
    base = (standalone_question or '').strip()
    if not base:
        return []
    if not is_multi_query_enabled():
        return [base]

    extra = multi_query_variant_count()
    if extra == 0:
        return [base]

    prompt = PromptTemplate.from_template(MULTI_QUERY_TEMPLATE).format(
        count=extra,
        question=base,
    )
    try:
        response = rag_service.llm.invoke(prompt)
        text = rag_service._extract_answer_text(response)  # noqa: SLF001
        variants = _parse_query_lines(text, extra)
    except Exception as exc:
        logger.warning('Multi-query expansion failed: %s', exc)
        variants = []

    queries = [base]
    for v in variants:
        if v.lower() != base.lower() and v not in queries:
            queries.append(v)
    logger.info('Multi-query: %s search queries', len(queries))
    return queries


def invoke_retriever(retriever: Any, query: str) -> list[Document]:
    if hasattr(retriever, 'invoke'):
        documents = retriever.invoke(query)
    elif hasattr(retriever, 'get_relevant_documents'):
        documents = retriever.get_relevant_documents(query)
    else:
        documents = []
    if not documents:
        return []
    if not isinstance(documents[0], Document):
        return [
            Document(
                page_content=getattr(d, 'page_content', str(d)),
                metadata=getattr(d, 'metadata', {}) or {},
            )
            for d in documents
        ]
    return list(documents)


def retrieve_with_queries(retriever: Any, queries: list[str]) -> list[Document]:
    lists: list[list[Document]] = []
    for q in queries:
        lists.append(invoke_retriever(retriever, q))
    fused = fuse_documents(*lists)
    logger.info(
        'Retrieved %s unique documents from %s queries',
        len(fused),
        len(queries),
    )
    return fused


def _load_json_setting(name: str) -> dict[str, Any] | None:
    raw = getattr(settings, name, None)
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(str(raw).strip())
    except json.JSONDecodeError:
        logger.warning('Invalid JSON in %s', name)
        return None


def build_bedrock_vector_filter() -> dict[str, Any] | None:
    """Optional Bedrock KB vectorSearchConfiguration.filter from METADATA_FILTER_JSON."""
    if not is_metadata_filter_enabled():
        return None
    spec = _load_json_setting('METADATA_FILTER_JSON')
    return spec if spec else None


def apply_client_metadata_filter(documents: list[Document]) -> list[Document]:
    """Post-filter documents by source_metadata key matches (METADATA_FILTER_CLIENT_JSON)."""
    if not is_post_metadata_filter_enabled():
        return documents
    rules = _load_json_setting('METADATA_FILTER_CLIENT_JSON')
    if not rules:
        return documents

    def matches(doc: Document) -> bool:
        meta = doc.metadata or {}
        nested = meta.get('source_metadata') if isinstance(meta.get('source_metadata'), dict) else {}
        combined = {**meta, **nested}
        for key, expected in rules.items():
            actual = combined.get(key)
            if actual is None:
                return False
            if isinstance(expected, str):
                if str(actual).lower() != expected.lower():
                    return False
            elif actual != expected:
                return False
        return True

    filtered = [d for d in documents if matches(d)]
    if filtered:
        logger.info('Client metadata filter: %s -> %s docs', len(documents), len(filtered))
        return filtered
    logger.info('Client metadata filter removed all docs; keeping originals')
    return documents
