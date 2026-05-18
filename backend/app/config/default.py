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

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class DefaultSettings(BaseSettings):
    """Default application settings."""

    # CORE SETTINGS
    PROJECT_NAME: str = 'EdTech RAG Assistant API'
    VERSION: str = '1.0.0'
    API_V1_STR: str = '/api'
    SECRET_KEY: str = 'supersecretkey'

    # DATABASE SETTINGS
    DATABASE_URL: str = 'postgresql://chatbot:chatbot@localhost:5432/chatbot'

    # JWT SETTINGS
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 4  # 4 hours

    # CORS SETTINGS
    BACKEND_CORS_ORIGINS: list[str] = ['*']
    FRONTEND_URL: str = 'http://localhost:8501'  # Default Streamlit port

    @field_validator('BACKEND_CORS_ORIGINS')
    def assemble_cors_origins(cls, v: list[str] | str) -> list[str] | str:
        """Validate CORS origins."""
        if isinstance(v, str) and not v.startswith('['):
            return [i.strip() for i in v.split(',')]
        elif isinstance(v, list):
            return v
        return ['*']

    # SQLALCHEMY
    SQLALCHEMY_DATABASE_URI: str | None = None

    @field_validator('SQLALCHEMY_DATABASE_URI', mode='before')
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> Any:
        if isinstance(v, str):
            return v
        return info.data.get('DATABASE_URL')

    # AWS settings
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = 'us-east-1'
    AWS_ROLE_ARN: str | None = None
    AWS_PROFILE_NAME: str | None = None  # Deprecated: Use instance profiles on EC2 instead
    BEDROCK_MODEL_ID: str = 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
    BEDROCK_KNOWLEDGE_BASE_ID: str | None = None
    BEDROCK_EMBEDDING_MODEL_ID: str = 'amazon.titan-embed-text-v1'

    # LangSmith settings
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = 'chatbot-poc'
    LANGCHAIN_ENDPOINT: str | None = None

    # Application settings
    ENVIRONMENT: str = 'development'
    APP_ENV: str | None = None

    # Logging settings
    LOG_TO_FILE: bool = True
    LOGGING_FORMAT: str = '[%(asctime)s] req=%(request_id)s - %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    LOGGING_LOCATION: str = 'fastapi.log'
    LOGGING_LEVEL: str = 'INFO'  # Default to INFO level
    LOGGING_PROPAGATION_LEVEL: str = 'INFO'

    # RAG and LLM tuning parameters
    MAX_TOKENS: int = 500  # Default for LLM max tokens
    TOP_K: int = 10  # Default for LLM top_k
    RETRIEVER_NUMBER_OF_RESULTS: int = 3  # Default number of docs to retrieve
    RETRIEVER_SEARCH_TYPE: str = 'HYBRID'  # Default search type for retriever
    TEMPERATURE: float = 0.1  # Default temperature for LLM

    # Provider selection (mock | aws | azure); RAG_FORCE_MOCK overrides all
    RAG_FORCE_MOCK: bool = False
    RAG_PROVIDER: str | None = None  # single shortcut for both LLM and retriever
    LLM_PROVIDER: str = 'mock'
    RETRIEVER_PROVIDER: str = 'mock'

    # Observability and platform
    LOG_JSON: bool = False
    ENABLE_DEV_API_ROUTES: bool = False
    ENABLE_OPENAPI_DOCS: bool = False

    # Rate limiting (Redis optional; fakeredis used when REDIS_URL unset)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_REGISTER_PER_MINUTE: int = 5
    RATE_LIMIT_CHAT_PER_MINUTE: int = 30
    REDIS_URL: str | None = None

    # Tenant / assistant branding (defaults when user has no tenant or tenant.rag_config)
    ASSISTANT_NAME: str = 'EdTech Support Assistant'
    SUPPORTED_TOPICS: str = (
        'your learning platform, course tools, integrations, and support documentation'
    )
    OUT_OF_SCOPE_MESSAGE: str = (
        'I can only answer questions covered by the knowledge base for '
        '{{supported_topics}}. Please ask a question related to those topics.'
    )

    # Performance / chat context
    CHAT_HISTORY_MAX_MESSAGES: int = 40  # Max messages passed to RAG (0 = unlimited)
    STREAM_ARTIFICIAL_DELAY_MS: int = 0  # Demo-only delay between streamed tokens; 0 = off
    SQLALCHEMY_POOL_SIZE: int = 5
    SQLALCHEMY_MAX_OVERFLOW: int = 10


    # Azure OpenAI (optional — for LLM_PROVIDER=azure)
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_DEPLOYMENT: str | None = None
    AZURE_OPENAI_API_VERSION: str = '2024-02-01'
    AZURE_EMBEDDING_DEPLOYMENT: str | None = None

    # Azure AI Search (optional — for RETRIEVER_PROVIDER=azure)
    AZURE_SEARCH_SERVICE_NAME: str | None = None
    AZURE_SEARCH_KEY: str | None = None
    AZURE_SEARCH_INDEX: str | None = None

    model_config = {
        'extra': 'allow',
    }
