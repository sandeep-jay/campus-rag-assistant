"""RAG graph nodes (condense, retrieve, web search, generate, format)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain.prompts import PromptTemplate
from langchain.schema import Document

from backend.app.core.config_manager import settings
from backend.app.services.graph.state import RagState
from backend.app.services.tools.web_search import web_search_documents

if TYPE_CHECKING:
    from backend.app.services.rag import RAGService

logger = logging.getLogger(__name__)

CONDENSE_TEMPLATE = """
Rephrase the follow-up question into a standalone question in English.

Chat History:
{chat_history}

Follow Up Input: {question}

Standalone Question (one line only, no labels):"""


def _format_chat_history_for_condense(chat_history: list) -> str:
    if not chat_history:
        return ''
    lines: list[str] = []
    for human, ai in chat_history:
        if human:
            lines.append(f'Human: {human}')
        if ai:
            lines.append(f'Assistant: {ai}')
    return '\n'.join(lines)


def _has_prior_turns(chat_history: list) -> bool:
    return any((human or '').strip() or (ai or '').strip() for human, ai in chat_history)


def make_condense_node(rag_service: RAGService, tenant_config=None):
    def condense_question(state: RagState) -> dict[str, Any]:
        question = state['question']
        chat_history = state.get('chat_history') or []
        if not _has_prior_turns(chat_history):
            return {'standalone_question': question}
        condense_prompt = PromptTemplate.from_template(CONDENSE_TEMPLATE)
        history_text = _format_chat_history_for_condense(chat_history)
        prompt = condense_prompt.format(chat_history=history_text, question=question)
        llm = rag_service.llm
        response = llm.invoke(prompt)
        standalone = rag_service._extract_answer_text(response) or question
        return {'standalone_question': standalone.strip()}

    condense_question.__name__ = 'rag_condense'
    return condense_question


def make_retrieve_node(rag_service: RAGService):
    def retrieve(state: RagState) -> dict[str, Any]:
        standalone = state.get('standalone_question') or state['question']
        retriever = rag_service.retriever
        if hasattr(retriever, 'invoke'):
            documents = retriever.invoke(standalone)
        elif hasattr(retriever, 'get_relevant_documents'):
            documents = retriever.get_relevant_documents(standalone)
        else:
            documents = []
        if documents and not isinstance(documents[0], Document):
            documents = [Document(page_content=getattr(d, 'page_content', str(d)), metadata=getattr(d, 'metadata', {})) for d in documents]
        logger.info('Graph retrieve: %s documents for %r', len(documents), standalone[:80])
        return {'documents': documents}

    retrieve.__name__ = 'rag_retrieve'
    return retrieve


def make_web_search_node(rag_service: RAGService):
    def web_search(state: RagState) -> dict[str, Any]:
        standalone = state.get('standalone_question') or state['question']
        documents = web_search_documents(standalone)
        logger.info('Graph web_search: %s documents', len(documents))
        return {'documents': documents}

    web_search.__name__ = 'rag_web_search'
    return web_search


def make_generate_node(rag_service: RAGService, tenant_config=None):
    def generate_answer(state: RagState) -> dict[str, Any]:
        standalone = state.get('standalone_question') or state['question']
        documents = state.get('documents') or []
        qa_prompt, _ = rag_service._create_prompt_templates(tenant_config)
        context = '\n\n'.join(doc.page_content for doc in documents)
        if not context.strip():
            context = '(No context retrieved.)'
        prompt_text = qa_prompt.format(context=context, question=standalone)
        response = rag_service.llm.invoke(prompt_text)
        answer = rag_service._extract_answer_text(response)
        return {'answer': answer}

    generate_answer.__name__ = 'rag_generate'
    return generate_answer


def make_format_node(rag_service: RAGService):
    def format_response(state: RagState) -> dict[str, Any]:
        documents = state.get('documents') or []
        answer = state.get('answer') or ''
        research_mode = state.get('research_mode') or 'kb'
        metadata_list, document_contents = rag_service._format_source_documents(documents)
        message = rag_service._normalize_answer_formatting(answer, metadata_list)
        metadata: dict[str, Any] = {
            'sources': metadata_list,
            'document_contents': document_contents,
            'source_kind': research_mode,
        }
        if research_mode == 'web':
            metadata['disclaimer'] = 'This answer used public web search results. ' 'Verify information against official institutional sources.'
        else:
            metadata['disclaimer'] = None
        return {'message': message, 'metadata': metadata}

    format_response.__name__ = 'rag_format'
    return format_response


def route_research_mode(state: RagState) -> str:
    mode = (state.get('research_mode') or 'kb').lower()
    if mode == 'web' and getattr(settings, 'WEB_RESEARCH_ENABLED', False):
        return 'web_search'
    return 'retrieve'
