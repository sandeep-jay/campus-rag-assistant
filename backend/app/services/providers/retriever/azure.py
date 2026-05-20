"""Azure AI Search hybrid retriever provider."""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from langchain.schema import Document
from langchain.schema.retriever import BaseRetriever
from langchain_openai import AzureOpenAIEmbeddings
from pydantic import Field, PrivateAttr

from backend.app.core.config_manager import settings
from backend.app.services.providers.base import BaseRetrieverProvider
from backend.app.services.rerank import retrieval_candidate_count


class AzureHybridRetriever(BaseRetriever):
    top_k: int = Field(default=4)
    _search_client: SearchClient = PrivateAttr()
    _embeddings: AzureOpenAIEmbeddings = PrivateAttr()
    _vector_field: str = PrivateAttr(default='text_vector')

    def __init__(
        self,
        search_client: SearchClient,
        embeddings: AzureOpenAIEmbeddings,
        top_k: int = 4,
        vector_field: str = 'text_vector',
        **kwargs,
    ) -> None:
        super().__init__(top_k=top_k, **kwargs)
        object.__setattr__(self, '_search_client', search_client)
        object.__setattr__(self, '_embeddings', embeddings)
        object.__setattr__(self, '_vector_field', vector_field)

    def _get_relevant_documents(self, query: str, **_kwargs) -> list[Document]:
        vector = self._embeddings.embed_query(query)
        results = self._search_client.search(
            search_text=query,
            vector_queries=[
                VectorizedQuery(
                    vector=vector,
                    k_nearest_neighbors=self.top_k,
                    fields=self._vector_field,
                )
            ],
            select=['chunk_id', 'text', 'kb_number', 'kb_url', 'kb_category', 'short_description'],
            top=self.top_k,
        )
        docs: list[Document] = []
        for r in results:
            score = r.get('@search.score', None)
            docs.append(
                Document(
                    page_content=r.get('text', '') or '',
                    metadata={
                        'kb_url': r.get('kb_url', ''),
                        'kb_number': r.get('kb_number', ''),
                        'kb_category': r.get('kb_category', ''),
                        'short_description': r.get('short_description', ''),
                        'chunk_id': r.get('chunk_id', ''),
                        'score': score,
                    },
                )
            )
        return docs


class AzureRetrieverProvider(BaseRetrieverProvider):
    name = 'azure'

    def __init__(self) -> None:
        self._validate_config()
        svc = settings.AZURE_SEARCH_SERVICE_NAME
        endpoint = f'https://{svc}.search.windows.net'
        self._search_client = SearchClient(
            endpoint=endpoint,
            index_name=settings.AZURE_SEARCH_INDEX,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY.get_secret_value() if settings.AZURE_SEARCH_KEY else ''),
        )
        self._embeddings = AzureOpenAIEmbeddings(
            azure_deployment=getattr(settings, 'AZURE_EMBEDDING_DEPLOYMENT', 'text-embedding-ada-002'),
            azure_endpoint=str(settings.AZURE_OPENAI_ENDPOINT).rstrip('/'),
            api_key=(settings.AZURE_OPENAI_API_KEY.get_secret_value() if settings.AZURE_OPENAI_API_KEY else None),
            api_version=getattr(settings, 'AZURE_OPENAI_API_VERSION', '2024-02-01'),
        )
        self._vector_field = getattr(settings, 'AZURE_SEARCH_VECTOR_FIELD', 'text_vector')
        self._top_k = retrieval_candidate_count()

    def _validate_config(self) -> None:
        keys = [
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_API_VERSION',
            'AZURE_EMBEDDING_DEPLOYMENT',
            'AZURE_SEARCH_SERVICE_NAME',
            'AZURE_SEARCH_KEY',
            'AZURE_SEARCH_INDEX',
        ]
        missing = [k for k in keys if not getattr(settings, k, None)]
        if missing:
            raise ValueError(f'Azure retriever missing config: {missing}')

    def get_retriever(self):
        return AzureHybridRetriever(
            search_client=self._search_client,
            embeddings=self._embeddings,
            top_k=self._top_k,
            vector_field=self._vector_field,
        )
