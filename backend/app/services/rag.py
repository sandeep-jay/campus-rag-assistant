"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

from botocore.exceptions import NoCredentialsError, NoRegionError, ProfileNotFound
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import AIMessage, HumanMessage

from backend.app.core.config_manager import settings
from backend.app.core.log_redaction import query_log_preview
from backend.app.services.graph.runner import run_rag_graph
from backend.app.services.providers import get_llm_provider, get_retriever_provider
from backend.app.services.providers.llm.aws import AwsLlmProvider
from backend.app.services.providers.llm.mock import MockLlmProvider
from backend.app.services.providers.retriever.aws import AwsRetrieverProvider
from backend.app.services.providers.retriever.mock import MockRetrieverProvider
from backend.app.services.tenant_rag_config import TenantRagConfig
from backend.app.utils.simple_tracer import trace_rag

# Configure logging
logger = logging.getLogger(__name__)


def _stream_artificial_delay() -> None:
    """Optional demo delay between streamed tokens (STREAM_ARTIFICIAL_DELAY_MS)."""
    delay_ms = int(getattr(settings, 'STREAM_ARTIFICIAL_DELAY_MS', 0) or 0)
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)


# Directory where template files are stored
TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'

# Singleton instance with thread safety
_rag_service_instance = None
_instance_lock = threading.Lock()


def _token_from_chat_stream_chunk(chunk: Any) -> str:
    """Extract text from LangChain/Bedrock on_chat_model_stream chunks."""
    if chunk is None:
        return ''
    content = getattr(chunk, 'content', None)
    if content is None:
        raw = str(chunk).strip()
        return '' if raw in ('', "content=''") else raw
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get('text') or block.get('content') or '')
            else:
                parts.append(getattr(block, 'text', None) or str(block))
        return ''.join(parts)
    return str(content)


class RAGService:
    """RAG service with config-driven LLM and retriever providers."""

    def __init__(self, bedrock_service=None, bedrock_client=None):
        self.is_mock = False
        self.llm_provider = None
        self.retriever_provider = None

        try:
            if bedrock_service is not None or bedrock_client is not None:
                self.llm_provider = AwsLlmProvider.create_or_mock(
                    MockLlmProvider,
                    bedrock_service=bedrock_service,
                    bedrock_client=bedrock_client,
                )
                self.retriever_provider = AwsRetrieverProvider.create_or_mock(
                    MockRetrieverProvider,
                    bedrock_service=bedrock_service,
                    bedrock_client=bedrock_client,
                )
            else:
                self.llm_provider = get_llm_provider()
                self.retriever_provider = get_retriever_provider()

            if getattr(settings, 'RAG_FORCE_MOCK', False) or self.llm_provider.is_mock or self.retriever_provider.is_mock:
                logger.warning(
                    'RAG running in mock mode (provider=%s/%s)',
                    self.llm_provider.name,
                    self.retriever_provider.name,
                )
                self.is_mock = True
                return

            self.llm = self.llm_provider.get_llm()
            self.retriever = self.retriever_provider.get_retriever()
            logger.info(
                'Initialized RAG with llm=%s retriever=%s model=%s',
                self.llm_provider.name,
                self.retriever_provider.name,
                settings.BEDROCK_MODEL_ID,
            )

            _bedrock = getattr(self.llm_provider, '_bedrock', None)
            if _bedrock is not None:
                self.bedrock_service = _bedrock
                self.bedrock_client = self.bedrock_service.client
            elif bedrock_service is not None:
                self.bedrock_service = bedrock_service

            self.qa_prompt, self.condense_question_prompt = self._create_prompt_templates(
                TenantRagConfig.from_settings(),
            )
            logger.info('Created prompt templates')

        except (ProfileNotFound, NoCredentialsError, NoRegionError) as e:
            logger.exception(f'AWS configuration error: {e!s}')
            logger.warning('Falling back to mock implementation')
            self.is_mock = True
        except Exception as e:
            logger.exception(f'Failed to initialize RAG service: {e!s}')
            logger.warning('Falling back to mock implementation')
            self.is_mock = True

    def _load_templates(self, tenant_config: TenantRagConfig | None = None):
        """Load prompt templates; hydrate placeholders from tenant or env defaults."""
        config = tenant_config or TenantRagConfig.from_settings()
        templates = {}
        try:
            with open(TEMPLATES_DIR / 'prompt_prefix.txt', 'r', encoding='utf-8') as f:
                templates['prefix'] = config.hydrate_text(f.read())
            suffix_path = TEMPLATES_DIR / 'prompt_suffix.txt'
            if suffix_path.is_file():
                with open(suffix_path, 'r', encoding='utf-8') as f:
                    templates['suffix'] = config.hydrate_text(f.read())
            else:
                templates['suffix'] = ''
            if config.few_shot_examples:
                templates['few_shot_examples'] = config.few_shot_examples
            else:
                with open(TEMPLATES_DIR / 'few_shot_examples.json', 'r', encoding='utf-8') as f:
                    templates['few_shot_examples'] = json.load(f)
            logger.info('Successfully loaded templates for assistant=%s', config.assistant_name)
        except Exception as e:
            logger.exception(f'Failed to load templates: {e!s}')
            # Provide default templates as fallback
            templates['prefix'] = """
            Human:
            You are a helpful and informative conversational assistant specialized in
            providing information from a knowledge base. Always respond in English unless the user asks for a different language.
            Use the following context to answer the user's question.
            If you cannot find the answer within the provided context, politely inform
            the user that you do not have the information and suggest alternative resources
            if available.
            When providing answers, always include the most relevant 'kb_url' and 'kb_number' metadata
            references for the answers provided.
            Provide concise and accurate answers. If a question is ambiguous, ask for clarification.
            Respond based ONLY on the following context:
            {context}

            Chat History:
            {chat_history}

            Question: {question}

            Assistant:
            """
            templates['suffix'] = 'Assistant: (Answer strictly based on the provided context, with kb_url and kb_number.)'
            templates['few_shot_examples'] = []
        return templates

    def _create_prompt_templates(self, tenant_config: TenantRagConfig | None = None):
        # Load templates — use a single QA prompt (few-shot examples removed from combine chain
        # because they caused format leakage and garbled answers with ConversationalRetrievalChain).
        templates = self._load_templates(tenant_config)
        prefix = templates.get('prefix', '')
        suffix = templates.get('suffix', '')
        qa_prompt = PromptTemplate(
            input_variables=['context', 'question'],
            template=prefix + suffix,
        )
        condense_question_prompt = PromptTemplate.from_template("""
Rephrase the follow-up question into a standalone question in English.

Chat History:
{chat_history}

Follow Up Input: {question}

Standalone Question (one line only, no labels):""")
        return qa_prompt, condense_question_prompt

    def _process_query_intent(self, query: str):
        # Process and improve the original query to better match KB content
        if self.is_mock:
            return query
        try:
            # Simple intent-checking prompt
            intent_prompt = """
            Examine this question: {0}

            If it's about the supported topic areas, rewrite it to be more specific
            while maintaining the original intent.
            If it's not about educational technology, return it unchanged.

            Rewritten question:
            """
            # Use the LLM to improve the query
            response = self.llm.invoke(intent_prompt.format(query))
            improved_query = response.strip()
            if improved_query and improved_query != query:
                logger.info('Improved query: %s -> %s', query_log_preview(query), query_log_preview(improved_query))
                logger.debug('Improved query full: %r -> %r', query, improved_query)
                return improved_query
            return query
        except Exception as e:
            logger.warning(f'Query intent processing failed: {e!s}')
            return query

    def _extract_answer_text(self, answer: Any) -> str:
        """Normalize LangChain/Bedrock answer objects to plain text."""
        if answer is None:
            return ''
        if isinstance(answer, str):
            return answer.strip()
        content = getattr(answer, 'content', None)
        if isinstance(content, str):
            return content.strip()
        if content is not None:
            return str(content).strip()
        return str(answer).strip()

    def _build_memory(self, chat_history: list):
        memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True, output_key='answer')
        for i in range(0, len(chat_history), 2):
            if i < len(chat_history):
                human_msg = chat_history[i]
                memory.chat_memory.add_message(HumanMessage(content=human_msg))
                if i + 1 < len(chat_history):
                    ai_msg = chat_history[i + 1]
                    memory.chat_memory.add_message(AIMessage(content=ai_msg))
        return memory

    def _format_source_documents(self, source_documents: list) -> tuple[list, list]:
        metadata_list = []
        document_contents = []
        for doc in source_documents:
            source_meta = doc.metadata.get('source_metadata', {})
            doc_metadata = {
                'source': source_meta.get('source', doc.metadata.get('source', 'unknown')),
                'kb_url': source_meta.get('kb_url', doc.metadata.get('kb_url', '#')),
                'kb_number': source_meta.get('kb_number', doc.metadata.get('kb_number', 'N/A')),
                'kb_category': source_meta.get('kb_category', doc.metadata.get('kb_category', '')),
                'short_description': source_meta.get('short_description', doc.metadata.get('short_description', '')),
                'project': source_meta.get('project', doc.metadata.get('project', '')),
                'ingestion_date': source_meta.get('ingestion_date', doc.metadata.get('ingestion_date', '')),
                'score': doc.metadata.get('score', None),
            }
            metadata_list.append(doc_metadata)
            document_contents.append({'content': doc.page_content, 'metadata': doc_metadata})
        return metadata_list, document_contents

    def _strip_condensed_question_leakage(self, text: str) -> str:
        """Remove standalone reformulated question leaked before out-of-scope or answers."""
        if not text:
            return text
        stripped = text.strip()
        max_q_words = 35

        # "Question?— Answer" / "Question? - Answer" (common RAG chain leak)
        m = re.match(r'^(.+\?)\s*[\u2014\u2013\-]+\s*(.+)$', stripped, re.DOTALL)
        if m and len(m.group(1).split()) <= max_q_words:
            return m.group(2).strip()

        # "Question? Answer continues" when answer starts with a capital letter
        m = re.match(r'^(.+\?)\s+([A-Z][\s\S]+)$', stripped)
        if m and len(m.group(1).split()) <= max_q_words:
            return m.group(2).strip()

        oos_markers = (
            'I can only answer questions',
            'I can only help with',
            'Please ask a question related to',
        )
        for marker in oos_markers:
            idx = stripped.find(marker)
            if idx <= 0:
                continue
            prefix = stripped[:idx].strip()
            if prefix.endswith('?') and len(prefix.split()) <= max_q_words:
                return stripped[idx:].strip()

        parts = re.split(r'(?<=[.!?])\s+', stripped, maxsplit=1)
        if len(parts) == 2 and parts[0].strip().endswith('?') and len(parts[0].split()) <= max_q_words:
            return parts[1].strip()
        return stripped

    def _sanitize_answer_text(self, text: str) -> str:
        """Remove prompt leakage, inline citations, and broken lines from model output."""
        if not text:
            return text
        text = self._extract_answer_text(text)
        text = self._strip_condensed_question_leakage(text)
        if text.startswith("content='") and 'additional_kwargs=' in text:
            m = re.match(r"content='(.*)' additional_kwargs=", text, re.DOTALL)
            if m:
                text = m.group(1).encode().decode('unicode_escape')

        drop_patterns = (
            r'^\s*Human\b',
            r'^\s*Assistant\b',
            r'^\s*Question\s*:',
            r'^\s*Standalone Question',
            r'^\s*Input\s*:',
            r'^\s*Output\s*:',
            r'^\s*Human the\s*:',
            r'^\s*kb_url\s*:',
            r'^\s*kb_number\s*:',
            r'^\s*References\s*:',
            r'^\s*\*\*References',
            r'^\s*\[URL:',
            r'^\s*\*\*Article\s*:\*\*\s*KB',
            r'^\s*Article\s*:\s*KB',
        )
        cleaned: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                cleaned.append('')
                continue
            if any(re.search(pat, stripped, re.IGNORECASE) for pat in drop_patterns):
                continue
            if re.match(r"^\[.*'.*'.*\]\s*$", stripped):
                continue
            if re.match(r"^\['", stripped) or re.match(r"^\[\s*'", stripped):
                continue
            cleaned.append(line.rstrip())
        text = '\n'.join(cleaned)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _promote_bold_headings(self, text: str) -> str:
        """Convert standalone **Title** lines to ## Title (generic Markdown fix)."""
        out: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            m = re.match(r'^\*\*(.+)\*\*\s*$', stripped)
            if m:
                inner = m.group(1).strip()
                if inner.endswith(':'):
                    out.append(line)
                else:
                    out.append(f'## {inner}')
            else:
                out.append(line)
        return '\n'.join(out)

    def _enhance_response(self, response: str, _metadata_list: list) -> str:
        """Sources are shown in the UI; do not append duplicate reference footers."""
        return response

    def _normalize_answer_formatting(self, text: str, metadata_list: list | None = None) -> str:
        """Convert model plain-text output into readable markdown."""
        if not text:
            return text
        metadata_list = metadata_list or []
        text = self._sanitize_answer_text(text)

        text = re.sub(r'(?<!\n)(\d+)\.\s+', r'\n\1. ', text)
        text = self._promote_bold_headings(text.lstrip())
        text = re.sub(r'\n{3,}', '\n\n', text)
        return self._enhance_response(text.strip(), metadata_list)

    def _chunk_for_stream(self, text: str, size: int = 16):
        for i in range(0, len(text), size):
            yield text[i : i + size]

    def stream_query(
        self,
        query: str,
        chat_history: list | None = None,
        tenant_config: TenantRagConfig | None = None,
    ):
        """Yield SSE payload dicts: token events then a final done metadata event."""
        if chat_history is None:
            chat_history = []

        if self.is_mock:
            mock = self._create_mock_response(query, tenant_config)
            message = self._normalize_answer_formatting(
                mock['message'],
                mock['metadata'].get('sources', []),
            )
            for chunk in self._chunk_for_stream(message, size=12):
                yield {'type': 'token', 'token': chunk}
                _stream_artificial_delay()
            yield {'type': 'done', 'metadata': mock['metadata']}
            return

        try:
            yield {'type': 'status', 'message': 'Searching the knowledge base…'}
            memory = self._build_memory(chat_history)
            streaming_llm = self.llm_provider.get_streaming_llm()
            if streaming_llm is None:
                streaming_llm = self.llm_provider.get_llm()
            qa_prompt, condense_question_prompt = self._create_prompt_templates(tenant_config)
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=streaming_llm,
                retriever=self.retriever,
                return_source_documents=True,
                memory=memory,
                combine_docs_chain_kwargs={'prompt': qa_prompt},
                condense_question_prompt=condense_question_prompt,
            )
            last_answer = ''
            source_documents: list = []
            for chunk in qa_chain.stream({'question': query}):
                if chunk.get('source_documents'):
                    source_documents = chunk['source_documents']
                if 'answer' not in chunk or chunk['answer'] is None:
                    continue
                current = self._extract_answer_text(chunk['answer'])
                delta = current[len(last_answer) :]
                last_answer = current
                if delta:
                    for piece in self._chunk_for_stream(delta, size=12):
                        yield {'type': 'token', 'token': piece}
                        _stream_artificial_delay()

            metadata_list, document_contents = self._format_source_documents(source_documents)
            logger.info('Retrieved %s documents from knowledge base', len(source_documents))
            yield {
                'type': 'done',
                'metadata': {
                    'sources': metadata_list,
                    'document_contents': document_contents,
                },
            }
        except Exception as e:
            logger.exception('Stream query failed, using buffered fallback: %s', e)
            result = self.process_query(query, chat_history, tenant_config)
            for chunk in self._chunk_for_stream(result['message'], size=12):
                yield {'type': 'token', 'token': chunk}
                _stream_artificial_delay()
            yield {'type': 'done', 'metadata': result['metadata']}

    def _use_langgraph_engine(self) -> bool:
        engine = (getattr(settings, 'RAG_ENGINE', None) or 'chain').strip().lower()
        return engine == 'langgraph'

    async def stream_query_async(
        self,
        query: str,
        chat_history: list | None = None,
        tenant_config: TenantRagConfig | None = None,
    ):
        """Async token stream via LangChain astream_events (true Bedrock streaming)."""
        if chat_history is None:
            chat_history = []

        if self.is_mock:
            mock = self._create_mock_response(query, tenant_config)
            message = self._normalize_answer_formatting(
                mock['message'],
                mock['metadata'].get('sources', []),
            )
            for chunk in self._chunk_for_stream(message, size=12):
                yield {'type': 'token', 'token': chunk}
                _stream_artificial_delay()
            yield {'type': 'done', 'metadata': mock['metadata']}
            return

        try:
            yield {'type': 'status', 'message': 'Searching the knowledge base…'}
            memory = self._build_memory(chat_history)
            streaming_llm = self.llm_provider.get_streaming_llm()
            if streaming_llm is None:
                streaming_llm = self.llm_provider.get_llm()
            qa_prompt, condense_question_prompt = self._create_prompt_templates(tenant_config)
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=streaming_llm,
                retriever=self.retriever,
                return_source_documents=True,
                memory=memory,
                combine_docs_chain_kwargs={'prompt': qa_prompt},
                condense_question_prompt=condense_question_prompt,
            )
            source_documents: list = []
            async for event in qa_chain.astream_events({'question': query}, version='v2'):
                kind = event.get('event')
                if kind == 'on_retriever_end':
                    output = event.get('data', {}).get('output')
                    if output is not None:
                        if isinstance(output, list):
                            source_documents = output
                        elif hasattr(output, 'documents'):
                            source_documents = list(output.documents)
                elif kind == 'on_chat_model_stream':
                    token = _token_from_chat_stream_chunk(event.get('data', {}).get('chunk'))
                    if token:
                        yield {'type': 'token', 'token': token}
                elif kind == 'on_chain_end' and not source_documents:
                    output = event.get('data', {}).get('output')
                    if isinstance(output, dict) and output.get('source_documents'):
                        source_documents = output['source_documents']

            metadata_list, document_contents = self._format_source_documents(source_documents)
            logger.info('Retrieved %s documents from knowledge base', len(source_documents))
            yield {
                'type': 'done',
                'metadata': {
                    'sources': metadata_list,
                    'document_contents': document_contents,
                },
            }
        except Exception as e:
            logger.exception('Async stream query failed, using buffered fallback: %s', e)
            result = self.process_query(query, chat_history, tenant_config)
            for chunk in self._chunk_for_stream(result['message'], size=12):
                yield {'type': 'token', 'token': chunk}
                _stream_artificial_delay()
            yield {'type': 'done', 'metadata': result['metadata']}

    def _create_mock_response(self, query: str, tenant_config: TenantRagConfig | None = None):
        # Create an improved mock response using few-shot examples if available
        try:
            # Try to load examples for better mock responses
            config = tenant_config or TenantRagConfig.from_settings()
            if config.few_shot_examples:
                mock_examples = config.few_shot_examples
            else:
                with open(TEMPLATES_DIR / 'few_shot_examples.json', 'r', encoding='utf-8') as file:
                    mock_examples = json.load(file)
            # Find most relevant example based on simple keyword matching
            query_words = set(query.lower().split())
            best_match = None
            best_score = 0
            for example in mock_examples:
                example_words = set(example['input'].lower().split())
                overlap = len(query_words.intersection(example_words))
                if overlap > best_score:
                    best_score = overlap
                    best_match = example
            if best_match and best_score > 0:
                # Use the matched example for a more relevant mock response
                mock_response = 'This is a mock response based on a similar question:\n\n'
                if isinstance(best_match['output'], list):
                    mock_response += '\n'.join(best_match['output'])
                else:
                    mock_response += best_match['output']
            else:
                mock_response = (
                    f'Mock response to: {query}\n\n'
                    f'This is a placeholder response since the RAG service is running in mock mode. '
                    f'Please configure AWS Bedrock for full functionality.'
                )
        except Exception as e:
            logger.warning(f'Error creating enhanced mock response: {e!s}')
            mock_response = (
                f'Mock response to: {query}\n\n'
                f'This is a placeholder response since the RAG service is running in mock mode. '
                f'Please configure AWS Bedrock for full functionality.'
            )
        # Enhanced mock metadata
        mock_metadata = [
            {
                'source': 'mock-document',
                'kb_url': 'https://example.com/kb/123',
                'kb_number': 'KB-123',
                'kb_category': 'Educational Technology',
                'short_description': 'Mock KB article for development',
                'project': 'Chatbot',
                'ingestion_date': '2023-07-01',
            },
        ]

        mock_document_contents = [
            {
                'content': 'This is mock content for testing purposes.',
                'metadata': mock_metadata[0],
            },
        ]

        return {
            'message': mock_response,
            'metadata': {
                'sources': mock_metadata,
                'document_contents': mock_document_contents,
            },
        }

    @trace_rag
    def process_query(
        self,
        query: str,
        chat_history: list | None = None,
        tenant_config: TenantRagConfig | None = None,
        research_mode: str = 'kb',
    ) -> dict[str, Any]:
        # Process a user query through the RAG pipeline with conversation memory.
        if not chat_history:
            chat_history = []

        logger.info('Processing query: %s', query_log_preview(query))
        logger.debug('Processing query full: %r', query)
        start_time = time.time()

        if self.is_mock:
            mock_response = self._create_mock_response(query, tenant_config)
            logger.info(f'Mock response generated in {time.time() - start_time:.2f}s')
            return mock_response

        try:
            if self._use_langgraph_engine():
                logger.info('Processing query via LangGraph (research_mode=%s)', research_mode)
                return run_rag_graph(
                    self,
                    query,
                    chat_history=chat_history,
                    tenant_config=tenant_config,
                    research_mode=research_mode,
                )

            memory = self._build_memory(chat_history)
            improved_query = query
            # Initialize the conversational chain for each request
            qa_prompt, condense_question_prompt = self._create_prompt_templates(tenant_config)
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.retriever,
                return_source_documents=True,
                memory=memory,
                combine_docs_chain_kwargs={'prompt': qa_prompt},
                condense_question_prompt=condense_question_prompt,
            )
            # Use the conversational retrieval chain to get a response
            response = qa_chain.invoke(
                {'question': improved_query},
            )

            # Format the response
            source_documents = response.get('source_documents', [])
            logger.info(
                f'Retrieved {len(source_documents)} documents from knowledge base',
            )

            metadata_list, document_contents = self._format_source_documents(source_documents)
            answer_text = self._extract_answer_text(response.get('answer'))
            enhanced_answer = self._normalize_answer_formatting(answer_text, metadata_list)
            # Log performance
            processing_time = time.time() - start_time
            logger.info(f'Query processed in {processing_time:.2f}s with {len(source_documents)} docs')

            return {
                'message': enhanced_answer,
                'metadata': {
                    'sources': metadata_list,
                    'document_contents': document_contents,
                },
            }
        except Exception as e:
            logger.exception(f'Error in RAG processing: {e!s}')
            # If RAG fails, try a fallback to direct LLM call
            try:
                if not self.is_mock and hasattr(self, 'llm'):
                    fallback_prompt = f"""I'm an AI assistant for educational technology.
                    I'm having trouble accessing my knowledge base right now, but I'll try to help with: {query}"""
                    answer = self.llm.invoke(fallback_prompt)
                    answer_text = self._extract_answer_text(answer)
                    return {
                        'message': self._normalize_answer_formatting(
                            f'{answer_text}\n\n(Note: This response was generated without access to the knowledge base.)',
                            [],
                        ),
                        'metadata': {'sources': [], 'document_contents': []},
                    }
            except Exception as fallback_error:
                logger.warning(f'Fallback response also failed: {fallback_error}')
            raise RuntimeError(f'Unexpected error in RAG service: {e!s}')


def get_rag_service():
    # Get or create the RAG service singleton instance.
    global _rag_service_instance
    if _rag_service_instance is None:
        with _instance_lock:
            if _rag_service_instance is None:
                _rag_service_instance = RAGService()
    return _rag_service_instance
