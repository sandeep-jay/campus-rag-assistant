"""Azure hybrid retriever tests."""

from unittest.mock import MagicMock, patch

from backend.app.services.providers.retriever.azure import AzureHybridRetriever, AzureRetrieverProvider


def test_azure_hybrid_maps_score_and_metadata():
    emb = MagicMock()
    emb.embed_query.return_value = [0.1, 0.2]
    client = MagicMock()
    client.search.return_value = [
        {
            'text': 'hello',
            'kb_url': 'u',
            'kb_number': 'KB-1',
            'kb_category': 'c',
            'short_description': 'd',
            'chunk_id': '1',
            '@search.score': 0.99,
        }
    ]
    r = AzureHybridRetriever(
        search_client=client,
        embeddings=emb,
        top_k=3,
        vector_field='myvec',
    )
    docs = r.get_relevant_documents('q')
    assert len(docs) == 1
    assert docs[0].page_content == 'hello'
    assert docs[0].metadata['score'] == 0.99
    assert docs[0].metadata['kb_number'] == 'KB-1'
    client.search.assert_called_once()
    call_kw = client.search.call_args.kwargs
    assert call_kw['top'] == 3
    assert call_kw['vector_queries'][0].fields == 'myvec'


def test_azure_retriever_provider_get_retriever():
    with (
        patch('backend.app.services.providers.retriever.azure.settings') as s,
        patch(
            'backend.app.services.providers.retriever.azure.SearchClient',
        ) as sc,
        patch('backend.app.services.providers.retriever.azure.AzureOpenAIEmbeddings') as emb_ctor,
    ):
        s.AZURE_OPENAI_ENDPOINT = 'https://x.openai.azure.com/'
        s.AZURE_OPENAI_API_KEY = 'k'
        s.AZURE_OPENAI_API_VERSION = '2024-02-01'
        s.AZURE_EMBEDDING_DEPLOYMENT = 'ada'
        s.AZURE_SEARCH_SERVICE_NAME = 'svc'
        s.AZURE_SEARCH_KEY = 'sk'
        s.AZURE_SEARCH_INDEX = 'idx'
        s.AZURE_SEARCH_VECTOR_FIELD = 'vf'
        s.RETRIEVER_NUMBER_OF_RESULTS = 5
        p = AzureRetrieverProvider()
        ret = p.get_retriever()
        assert isinstance(ret, AzureHybridRetriever)
        sc.assert_called_once()
        emb_ctor.assert_called_once()
