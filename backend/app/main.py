"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from starlette.middleware.sessions import SessionMiddleware

from backend.app.api import auth, chat, oauth_routes
from backend.app.core.config_manager import settings
from backend.app.core.logger import initialize_logger, logger
from backend.app.core.metrics import metrics_middleware, metrics_response, refresh_db_pool_metrics
from backend.app.core.request_context import RequestContextMiddleware
from backend.app.db.database import Base, engine

# Configure logging before other subsystems emit logs.
initialize_logger()

_env = (getattr(settings, 'APP_ENV', None) or settings.ENVIRONMENT or '').lower()
if _env in ('development', 'test', 'testing'):
    logger.info('Creating database tables via metadata.create_all (dev/test only)')
    Base.metadata.create_all(bind=engine)
else:
    logger.info(
        'Skipping metadata.create_all in %s; run alembic upgrade head before serving traffic',
        _env or 'production',
    )

security_scheme = HTTPBearer(auto_error=True)

_openapi = '/api/openapi.json' if settings.ENABLE_OPENAPI_DOCS else None
_docs = '/api/docs' if settings.ENABLE_OPENAPI_DOCS else None
_redoc = '/api/redoc' if settings.ENABLE_OPENAPI_DOCS else None

app = FastAPI(
    title='BCourses Chatbot API',
    description='API for the BCourses Chatbot with RAG capabilities.',
    version='1.0.0',
    docs_url=_docs,
    redoc_url=_redoc,
    openapi_url=_openapi,
)

initialize_logger(app)
logger.info('Enhanced logging system initialized with FastAPI app')

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

logger.info('Configuring CORS middleware')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        'http://localhost:8501',
        'https://localhost:8501',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['X-Request-ID'],
)

app.middleware('http')(metrics_middleware)
app.add_middleware(RequestContextMiddleware)

logger.info('Including API routers')
app.include_router(auth.router, prefix='/api/auth', tags=['auth'])
app.include_router(oauth_routes.router, prefix='/api/auth/oauth', tags=['auth'])
app.include_router(chat.router, prefix='/api/chat', tags=['chat'])
logger.info('API setup complete')


@app.get('/')
async def root_base():
    return {'message': 'OK'}


@app.get('/api/')
async def root() -> dict:
    logger.debug('Root endpoint accessed')
    return {'message': 'Welcome to BCourses Chatbot API'}


@app.get('/api/health')
async def health_check() -> dict:
    logger.debug('Health check endpoint accessed')
    return {'status': 'ok', 'message': 'API is healthy'}


@app.get('/api/metrics')
async def metrics():
    return metrics_response()


@app.get('/api/metrics/db-pool')
async def metrics_db_pool() -> dict:
    return refresh_db_pool_metrics(engine)
