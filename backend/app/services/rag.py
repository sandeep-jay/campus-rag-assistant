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
import threading
import time
from pathlib import Path
from typing import Any

from botocore.exceptions import NoCredentialsError, NoRegionError, ProfileNotFound
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from langchain.schema import AIMessage, HumanMessage
from langchain_aws import AmazonKnowledgeBasesRetriever

from backend.app.core.config_manager import settings
from backend.app.services.bedrock import BedrockService
from backend.app.utils.simple_tracer import trace_rag

# Configure logging
logger = logging.getLogger(__name__)

# Directory where template files are stored
TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'

# Singleton instance with thread safety
_rag_service_instance = None
_instance_lock = threading.Lock()


class RAGService:
    """Enhanced RAG service using Bedrock and external templates"""

    def __init__(self, bedrock_service=None, bedrock_client=None):
        self.is_mock = False

        try:
            # First determine if we should use mock mode
            if not settings.BEDROCK_KNOWLEDGE_BASE_ID:
                logger.warning('No BEDROCK_KNOWLEDGE_BASE_ID provided in settings - using mock implementation')
                self.is_mock = True
                return

            # Use provided Bedrock service or client, or create a new service
            if bedrock_service:
                self.bedrock_service = bedrock_service
                logger.info('Using provided BedrockService')
            elif bedrock_client:
                self.bedrock_service = BedrockService(bedrock_client=bedrock_client)
                logger.info('Created BedrockService with provided client')
            else:
                self.bedrock_service = BedrockService()
                logger.info('Created new BedrockService')

            # Store the bedrock client for compatibility with existing code
            self.bedrock_client = self.bedrock_service.client

            # Set up the retriever
            self.retriever = self._initialize_retriever()
            if not self.retriever:
                logger.warning('Failed to initialize retriever - using mock implementation')
                self.is_mock = True
                return

            # Initialize the LLM
            self.llm = self.bedrock_service.get_llm()
            logger.info(f'Initialized BedrockLLM with model {settings.BEDROCK_MODEL_ID}')

            # Create prompt templates
            self.qa_prompt, self.condense_question_prompt = self._create_prompt_templates()
            logger.info('Created prompt templates')

            # No eager chain initialization - we'll create it per request

        except (ProfileNotFound, NoCredentialsError, NoRegionError) as e:
            logger.exception(f'AWS configuration error: {e!s}')
            logger.warning('Falling back to mock implementation')
            self.is_mock = True
        except Exception as e:
            logger.exception(f'Failed to initialize RAG service: {e!s}')
            logger.warning('Falling back to mock implementation')
            self.is_mock = True

    def _initialize_retriever(self):
        """Initialize the knowledge base retriever with improved configuration"""
        try:
            # Get the agent client from the Bedrock service
            agent_client = self.bedrock_service.get_agent_client()

            # Create the retriever with enhanced configuration
            retriever = AmazonKnowledgeBasesRetriever(
                knowledge_base_id=settings.BEDROCK_KNOWLEDGE_BASE_ID,
                retrieval_config={
                    'vectorSearchConfiguration': {
                        'numberOfResults': settings.RETRIEVER_NUMBER_OF_RESULTS,
                        'overrideSearchType': settings.RETRIEVER_SEARCH_TYPE,
                    }
                },
                region_name=settings.AWS_REGION,
                client=agent_client,
            )
            logger.info('Successfully initialized AmazonKnowledgeBasesRetriever')
            return retriever
        except Exception as e:
            logger.exception(f'Failed to initialize knowledge base retriever: {e!s}')
            return None

    def _load_templates(self):
        """Load prompt templates and few-shot examples from the templates directory"""
        templates = {}
        try:
            # Load prefix template
            with open(TEMPLATES_DIR / 'prompt_prefix.txt', 'r') as f:
                templates['prefix'] = f.read()
            # Load suffix template
            with open(TEMPLATES_DIR / 'prompt_suffix.txt', 'r') as f:
                templates['suffix'] = f.read()
            # Load few-shot examples
            with open(TEMPLATES_DIR / 'few_shot_examples.json', 'r') as f:
                templates['few_shot_examples'] = json.load(f)
            logger.info('Successfully loaded templates and few-shot examples')
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

    def _create_prompt_templates(self):
        # Create the prompt templates for the RAG QA system
        # Load templates
        templates = self._load_templates()
        # Create the regular QA prompt
        if templates.get('few_shot_examples'):
            # Create few-shot prompt if examples are available
            example_template = """
            Input: {input}
            Output: {output}
            """
            example_prompt = PromptTemplate(input_variables=['input', 'output'], template=example_template)
            qa_prompt = FewShotPromptTemplate(
                examples=templates['few_shot_examples'],
                example_prompt=example_prompt,
                prefix=templates.get('prefix', ''),
                suffix=templates.get('suffix', ''),
                input_variables=['context', 'chat_history', 'question'],
            )
        else:
            # Create simple prompt if no examples are available
            qa_prompt = PromptTemplate(
                input_variables=['context', 'chat_history', 'question'], template=templates.get('prefix', '') + templates.get('suffix', '')
            )
        # Create the condense question prompt for follow-up questions
        condense_question_prompt = PromptTemplate.from_template("""
        Given the following conversation and a follow up question, rephrase the follow up question
        to be a standalone question, in its original language. Always respond in English unless the user explicitly asks for a different language.

        Chat History:
        {chat_history}

        Follow Up Input: {question}
        Standalone Question:""")
        return qa_prompt, condense_question_prompt

    def _process_query_intent(self, query: str):
        # Process and improve the original query to better match KB content
        if self.is_mock:
            return query
        try:
            # Simple intent-checking prompt
            intent_prompt = """
            Examine this question: {0}

            If it's about educational technology tools, rewrite it to be more specific
            while maintaining the original intent.
            If it's not about educational technology, return it unchanged.

            Rewritten question:
            """
            # Use the LLM to improve the query
            response = self.llm.invoke(intent_prompt.format(query))
            improved_query = response.strip()
            if improved_query and improved_query != query:
                logger.info(f"Improved query: '{query}' -> '{improved_query}'")
                return improved_query
            return query
        except Exception as e:
            logger.warning(f'Query intent processing failed: {e!s}')
            return query

    def _enhance_response(self, response, metadata_list):
        # Enhance the response with proper formatting and citations
        # Check if KB references are already in the response
        kb_refs = [f"KB-{meta.get('kb_number')}" for meta in metadata_list if meta.get('kb_number') and meta.get('kb_number') != 'N/A']
        has_refs = any(ref in response for ref in kb_refs)
        # Add references if not already present
        if kb_refs and not has_refs:
            # Add up to 3 most relevant KB references
            refs = list(set(kb_refs))[:3]
            response += f"\n\nReferences: {', '.join(refs)}"
        # Format lists consistently
        if '1.' in response and '\n1.' not in response:
            response = response.replace('1.', '\n1.')
        return response

    def _create_mock_response(self, query: str):
        # Create an improved mock response using few-shot examples if available
        try:
            # Try to load examples for better mock responses
            with open(TEMPLATES_DIR / 'few_shot_examples.json', 'r') as file:
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
    ) -> dict[str, Any]:
        # Process a user query through the RAG pipeline with conversation memory.
        if not chat_history:
            chat_history = []

        logger.info(f"Processing query: '{query}'")
        start_time = time.time()

        if self.is_mock:
            mock_response = self._create_mock_response(query)
            logger.info(f'Mock response generated in {time.time() - start_time:.2f}s')
            return mock_response

        try:
            # Format chat history for LangChain
            memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True, output_key='answer')
            # Process pairs of messages as human/AI interactions
            # This assumes chat_history is a flat list of alternating human/AI messages
            for i in range(0, len(chat_history), 2):
                if i < len(chat_history):
                    human_msg = chat_history[i]
                    memory.chat_memory.add_message(HumanMessage(content=human_msg))
                    # Add AI response if available
                    if i + 1 < len(chat_history):
                        ai_msg = chat_history[i + 1]
                        memory.chat_memory.add_message(AIMessage(content=ai_msg))

            """
            # Process query intent if enabled
            # Commented out for now - uncomment to enable
            # improved_query = self._process_query_intent(query)
            """
            improved_query = query  # Use original query for now
            # Initialize the conversational chain for each request
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.retriever,
                return_source_documents=True,
                memory=memory,
                combine_docs_chain_kwargs={'prompt': self.qa_prompt},
                condense_question_prompt=self.condense_question_prompt,
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

            # Format metadata from source documents
            metadata_list = []
            document_contents = []
            for doc in source_documents:
                # Get source_metadata if it exists, otherwise use the whole metadata
                source_meta = doc.metadata.get('source_metadata', {})

                # Map the metadata fields correctly
                doc_metadata = {
                    'source': source_meta.get('source', doc.metadata.get('source', 'unknown')),
                    'kb_url': source_meta.get('kb_url', doc.metadata.get('kb_url', '#')),
                    'kb_number': source_meta.get('kb_number', doc.metadata.get('kb_number', 'N/A')),
                    'kb_category': source_meta.get('kb_category', doc.metadata.get('kb_category', '')),
                    'short_description': source_meta.get('short_description', doc.metadata.get('short_description', '')),
                    'project': source_meta.get('project', doc.metadata.get('project', '')),
                    'ingestion_date': source_meta.get('ingestion_date', doc.metadata.get('ingestion_date', '')),
                    'score': doc.metadata.get('score', None),  # Extract score if available
                }
                metadata_list.append(doc_metadata)

                # Extract document content
                document_contents.append(
                    {'content': doc.page_content, 'metadata': doc_metadata},
                )

                logger.debug(f'Document metadata: {doc_metadata}')
                logger.debug(f'Original metadata: {doc.metadata}')

            # Enhance the response with proper formatting and citations
            enhanced_answer = self._enhance_response(response['answer'], metadata_list)
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
                    return {
                        'message': f'{answer}\n\n(Note: This response was generated without access to the knowledge base.)',
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
