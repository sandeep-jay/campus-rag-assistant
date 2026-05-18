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

from unittest.mock import ANY, MagicMock, patch

import pytest

from backend.app.services.rag import RAGService

"""Consolidated tests for the RAG service module."""


@pytest.fixture()
def rag_mocks():
    """Patch RAG providers and chain; return mocks tuple for assertions."""
    mock_llm = MagicMock()
    mock_retriever_instance = MagicMock()
    mock_bedrock_instance = MagicMock()
    mock_bedrock_instance.get_llm.return_value = mock_llm
    mock_bedrock_instance.client = MagicMock()

    mock_llm_provider = MagicMock()
    mock_llm_provider.is_mock = False
    mock_llm_provider.name = 'aws'
    mock_llm_provider.get_llm.return_value = mock_llm
    mock_llm_provider._bedrock = mock_bedrock_instance

    mock_ret_provider = MagicMock()
    mock_ret_provider.is_mock = False
    mock_ret_provider.name = 'aws'
    mock_ret_provider.get_retriever.return_value = mock_retriever_instance

    patchers = [
        patch('backend.app.services.rag.get_llm_provider', return_value=mock_llm_provider),
        patch('backend.app.services.rag.get_retriever_provider', return_value=mock_ret_provider),
        patch('backend.app.services.rag.ConversationalRetrievalChain'),
        patch('backend.app.services.rag.settings'),
        patch('backend.app.services.aws_client.settings'),
    ]
    mocks = [p.start() for p in patchers]

    mocks[3].AWS_REGION = 'us-east-1'
    mocks[3].BEDROCK_KNOWLEDGE_BASE_ID = 'test-kb-id'
    mocks[3].BEDROCK_MODEL_ID = 'anthropic.claude-v2'
    mocks[3].LANGCHAIN_API_KEY = None
    mocks[3].RAG_FORCE_MOCK = False

    mocks[4].AWS_REGION = 'us-east-1'
    mocks[4].AWS_ROLE_ARN = None

    mock_chain_instance = MagicMock()
    mock_chain_instance.invoke.return_value = {
        'answer': 'Test answer',
        'source_documents': [],
    }
    mocks[2].from_llm.return_value = mock_chain_instance

    # [0]=llm provider patch, [1]=retriever provider, [2]=chain, [3]=rag settings, [4]=aws settings
    yield (*mocks, mock_llm_provider, mock_ret_provider, mock_bedrock_instance, mock_llm, mock_retriever_instance)

    for p in patchers:
        p.stop()


# Basic Initialization Tests
def test_initialize_rag_service_with_bedrock_service(rag_mocks):
    """Test initialization of RAGService via provider registry."""
    service = RAGService()

    assert not service.is_mock
    assert service.llm_provider is rag_mocks[5]
    assert service.retriever_provider is rag_mocks[6]
    assert isinstance(service.bedrock_service, MagicMock)
    assert service.llm == rag_mocks[8]


def test_initialize_with_provided_client(rag_mocks):
    """Test initialization of RAGService with injected Bedrock service."""
    bedrock = rag_mocks[7]
    with patch('backend.app.services.rag.AwsLlmProvider.create_or_mock', return_value=rag_mocks[5]), patch(
        'backend.app.services.rag.AwsRetrieverProvider.create_or_mock',
        return_value=rag_mocks[6],
    ):
        service = RAGService(bedrock_service=bedrock)
    assert not service.is_mock
    assert service.bedrock_service == bedrock


def test_rag_service_initialization(rag_mocks):
    """Test that RAG service initializes correctly via providers."""
    rag_service = RAGService()

    assert not rag_service.is_mock
    assert rag_service.llm_provider is rag_mocks[5]
    assert rag_service.retriever_provider is rag_mocks[6]
    assert rag_service.llm == rag_mocks[8]
    assert rag_service.retriever == rag_mocks[9]


# Processing Query Tests
def test_process_query(rag_mocks):
    """Test process_query method."""
    # Setup mock responses
    mock_chain_instance = rag_mocks[2].from_llm.return_value

    service = RAGService()
    response = service.process_query('Test query')

    assert response['message'] == 'Test answer'
    mock_chain_instance.invoke.assert_called_once()


def test_process_query_with_source_documents(rag_mocks):
    """Test that RAG service processes queries with source documents correctly."""
    # Create mock documents with metadata
    doc1 = MagicMock()
    doc1.metadata = {
        'source': 'source1',
        'kb_url': 'url1',
        'kb_number': 'KB-123',
        'kb_category': 'category1',
        'short_description': 'desc1',
        'project': 'project1',
        'ingestion_date': '2023-01-01',
    }
    doc1.page_content = 'content1'

    doc2 = MagicMock()
    doc2.metadata = {
        'source': 'source2',
        'kb_url': 'url2',
        'kb_number': 'KB-456',
        'kb_category': 'category2',
        'short_description': 'desc2',
        'project': 'project2',
        'ingestion_date': '2023-01-02',
    }
    doc2.page_content = 'content2'

    # Mock chain response
    mock_chain_instance = rag_mocks[2].from_llm.return_value
    mock_chain_instance.invoke.return_value = {
        'answer': 'Test answer',
        'source_documents': [doc1, doc2],
    }

    rag_service = RAGService()
    response = rag_service.process_query('What is the meaning of life?')

    # Check the chain was invoked with the correct parameters
    mock_chain_instance.invoke.assert_called_once()
    call_args = mock_chain_instance.invoke.call_args[0][0]
    assert call_args['question'] == 'What is the meaning of life?'

    # Check the response is correct with KB references
    assert 'Test answer' in response['message']

    # Check for KB references in any order (they might be in a different order)
    assert 'References:' in response['message']
    assert 'KB-KB-123' in response['message']
    assert 'KB-KB-456' in response['message']


def test_rag_service_with_chat_history(rag_mocks):
    """Test that RAG service processes queries with chat history correctly."""
    rag_service = RAGService()

    # Test with chat history
    chat_history = [
        'What is the meaning of life?',
        '42',
        'Why is the sky blue?',
        'Because of Rayleigh scattering',
    ]

    response = rag_service.process_query('What is the universe?', chat_history)

    # Check the chain was invoked with the correct parameters
    mock_chain_instance = rag_mocks[2].from_llm.return_value
    mock_chain_instance.invoke.assert_called_once()
    call_args = mock_chain_instance.invoke.call_args[0][0]
    assert call_args['question'] == 'What is the universe?'
    # Chat history is now stored in the ConversationBufferMemory
    # and not passed directly

    # Check the response is correct
    assert response['message'] == 'Test answer'
    assert response['metadata']['sources'] == []


# Mock Mode Tests
def test_mock_mode(rag_mocks):
    """Test that RAG service works in mock mode."""
    rag_mocks[5].is_mock = True
    rag_mocks[6].is_mock = True

    # Mock the few_shot_examples.json file
    with patch('json.load') as mock_json_load:
        # Mock for loading few_shot_examples.json
        mock_examples = [
            {
                'input': 'What are the steps to create an assignment in Gradescope?',
                'output': [
                    '1. Create a bCourses assignment to add a new item to the gradebook.',
                    "2. Set submission type as 'External Tool', then click 'Find' and select 'Gradescope'. Set a point value, then Save.",
                    '3. The page will re-load with Gradescope embedded where you can create your Gradescope assignment.',
                    '4. Link your Gradescope assignment to the bCourses assignment/gradebook.',
                    '5. When you have completed grading in Gradescope, you can sync your scores to the gradebook.',
                ],
            }
        ]
        mock_json_load.return_value = mock_examples
        # Create a patch for open() that never gets called but prevents errors
        with patch('builtins.open'):
            rag_service = RAGService()
            # Check it's in mock mode
            assert rag_service.is_mock
            # Test process_query in mock mode (with our mocked similar example)
            query = 'What is the meaning of life?'
            response = rag_service.process_query(query)
            # Accept either the standard mock response or the similar example response
            assert any(
                [
                    'Mock response to: What is the meaning of life?' in response['message'],
                    'This is a mock response based on a similar question:' in response['message'],
                ]
            )
            assert response['metadata']['sources'][0]['kb_number'] == 'KB-123'


def test_fallback_to_mock_implementation(rag_mocks):
    """Test fallback to mock implementation when providers fail."""
    rag_mocks[5].is_mock = True
    service = RAGService()
    assert service.is_mock
    assert not hasattr(service, 'bedrock_service')


# Integration with Bedrock Tests
def test_rag_and_bedrock_service_compatibility(rag_mocks):
    """Test that injected Bedrock service works with RAGService."""
    bedrock = rag_mocks[7]
    with patch('backend.app.services.rag.AwsLlmProvider.create_or_mock', return_value=rag_mocks[5]), patch(
        'backend.app.services.rag.AwsRetrieverProvider.create_or_mock',
        return_value=rag_mocks[6],
    ):
        service = RAGService(bedrock_service=bedrock)
    assert not service.is_mock
    assert service.bedrock_service == bedrock

    response = service.process_query('Test query')
    assert response['message'] == 'Test answer'
    rag_mocks[2].from_llm.return_value.invoke.assert_called_once()
