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
from pathlib import Path

from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from langchain.schema import AIMessage, HumanMessage
from langchain_aws import AmazonKnowledgeBasesRetriever, BedrockLLM

from backend.app.core.config_manager import settings
from backend.app.schemas.chat import ChatRequest, SourceDocument
from backend.app.services.aws_service import AWSService

logger = logging.getLogger(__name__)

# Directory where template files are stored
TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'

"""RAG Service module for handling LangChain and Bedrock interactions."""


def get_aws_session():
    # Get AWS session from the AWS service.
    return AWSService.get_session()


class RAGService:
    # Service for RAG operations using LangChain and Bedrock.

    def __init__(self, aws_session=None):
        # Initialize the RAG service with AWS session.
        try:
            # Try to get AWS session if not provided
            self.aws_session = aws_session or get_aws_session()
            self.mock_mode = False
            logger.info('RAG service initialized with AWS session')
        except Exception as e:
            logger.warning(f'Failed to initialize AWS session: {e}')
            self.aws_session = None
            self.mock_mode = True
            # Don't raise error, continue with mock mode

        # Only initialize these if not in mock mode
        if not self.mock_mode:
            self.retriever = self._initialize_retriever()
            self.llm = self._initialize_llm()
            self.few_shot_prompt, self.condense_question_prompt = self._create_prompt_templates()

    def _initialize_retriever(self):
        # Initialize the Amazon Knowledge Bases Retriever.
        try:
            return AmazonKnowledgeBasesRetriever(
                knowledge_base_id=settings.BEDROCK_KNOWLEDGE_BASE_ID,
                retrieval_config={'vectorSearchConfiguration': {'numberOfResults': 4}},
                region_name=settings.AWS_REGION,
                client=self.aws_session.client('bedrock-agent-runtime'),
            )
        except Exception as e:
            logger.error(f'Knowledge Base Retriever Error: {e}')
            raise ValueError(f'Failed to initialize retriever: {e}')

    def _initialize_llm(self):
        # Initialize the Bedrock LLM.
        try:
            model_kwargs = {
                'temperature': 0,
                'top_k': 10,
                'max_tokens': 750,
            }
            return BedrockLLM(
                model_id=settings.BEDROCK_MODEL_ID,
                model_kwargs=model_kwargs,
                region_name=settings.AWS_REGION,
                client=self.aws_session.client('bedrock-runtime'),
            )
        except Exception as e:
            logger.error(f'Bedrock LLM Initialization Error: {e}')
            raise ValueError(f'Failed to initialize LLM: {e}')

    def _create_prompt_templates(self):
        # Create prompt templates for the Conversational Retrieval Chain.
        try:
            with open(TEMPLATES_DIR / 'prompt_prefix.txt', 'r') as file:
                my_template_prefix = file.read()

            with open(TEMPLATES_DIR / 'prompt_suffix.txt', 'r') as file:
                my_template_suffix = file.read()

            # Load the few shot examples
            with open(TEMPLATES_DIR / 'few_shot_examples.json', 'r') as file:
                few_shot_examples = json.load(file)

            example_template = """
            Input: {input}
            Output: {output}
            """

            example_prompt = PromptTemplate(input_variables=['input', 'output'], template=example_template)

            few_shot_prompt = FewShotPromptTemplate(
                examples=few_shot_examples,
                example_prompt=example_prompt,
                prefix=my_template_prefix,
                suffix=my_template_suffix,
                input_variables=['context', 'chat_history', 'question'],
            )

            condense_question_prompt = PromptTemplate.from_template("""
            Given the following conversation and a follow up question, rephrase the follow up question
            to be a standalone question, in its original language.

            Chat History:
            {chat_history}

            Follow Up Input: {question}
            Standalone Question:""")

            return few_shot_prompt, condense_question_prompt
        except Exception as e:
            logger.error(f'Error creating prompt templates: {e}')
            raise ValueError(f'Failed to create prompt templates: {e}')

    def _process_query_intent(self, query: str):
        # Process and improve the original query by understanding its intent.
        intent_prompt = PromptTemplate.from_template("""
        As an AI assistant with knowledge of instructional technology, improve the
        following question to make it clearer and more specific.
        If the question is already well-formed, return it unchanged.
        If the question is unclear or poorly formed, rewrite it to be more precise
        while preserving its original intent.

        Original question: {query}

        Improved question:""")

        try:
            response = self.llm.invoke(intent_prompt.format(query=query))
            improved_query = response.strip()
            return improved_query if improved_query else query
        except Exception as e:
            logger.warning(f'Query intent processing failed: {e}')
            return query

    def process_chat_request(self, request: ChatRequest):
        # Process a chat request through the RAG pipeline.
        try:
            # If in mock mode, return a mock response
            if self.mock_mode:
                logger.info('Using mock response in RAG service')
                return {
                    'answer': 'This is a mock response as AWS credentials are not configured. '
                    'To use the real RAG service, please configure AWS credentials in the .env file.',
                    'source_documents': [],
                }

            # Create memory for chat history
            memory = ConversationBufferMemory(memory_key='chat_history', output_key='answer', return_messages=True)

            # Properly format and add chat history to memory
            for msg in request.chat_history:
                if 'role' in msg:
                    role = msg['role']
                    content = msg['content']
                elif 'type' in msg:
                    role = msg['type']
                    content = msg['content']
                else:
                    logger.warning(f'Unrecognized message format in chat history: {msg}')
                    continue

                # Add appropriate message type based on role
                if role.lower() in ['ai', 'assistant']:
                    memory.chat_memory.add_message(AIMessage(content=content))
                elif role.lower() in ['human', 'user']:
                    memory.chat_memory.add_message(HumanMessage(content=content))
                else:
                    logger.warning(f'Unknown role type in chat history: {role}')

            # Create conversational chain
            qa = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.retriever,
                return_source_documents=True,
                combine_docs_chain_kwargs={'prompt': self.few_shot_prompt},
                memory=memory,
                condense_question_prompt=self.condense_question_prompt,
            )

            # Process query intent
            """
            This is a temporary fix to improve the query intent. The process involved making an LLM call
            to deduce query inent and expand the query. But, currently, the LLM rewrites all queries to match
            what exists in the knowledge base. Also, additional LLM cll introduces latency for negligible gain.

            It is not a good solution for now and we should improve the prompt to make it more accurate.

            # improved_prompt = self._process_query_intent(request.message)
            # if improved_prompt != request.message:
            #     logger.info(f"Original query: '{request.message}' improved to: '{improved_prompt}'")

            # Get response from the chain
            # output = qa.invoke({'question': improved_prompt, 'chat_history': memory.load_memory_variables({})})
            """

            # Get response from the chain
            output = qa.invoke({'question': request.message, 'chat_history': memory.load_memory_variables({})})

            # Convert source documents to SourceDocument model
            source_docs = []
            if output.get('source_documents'):
                for doc in output['source_documents']:
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

                    source_docs.append(SourceDocument(content=doc.page_content, metadata=doc_metadata))

            return {'answer': output.get('answer', ''), 'source_documents': source_docs}

        except Exception as e:
            logger.error(f'Error processing chat request: {e}')
            raise ValueError(f'Failed to process chat request: {e}')


# Singleton instance
_rag_service_instance = None


def get_rag_service():
    # Get or create the RAG service singleton instance.
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
