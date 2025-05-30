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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from backend.app.api import auth, chat
from backend.app.core.config_manager import settings
from backend.app.core.logger import initialize_logger, logger
from backend.app.db.database import Base, engine

# Create database tables
logger.info('Initializing database tables')
Base.metadata.create_all(bind=engine)
logger.info('Database tables initialized successfully')

# Define HTTP Bearer security scheme for Swagger UI
security_scheme = HTTPBearer(auto_error=True)

app = FastAPI(
    title='BCourses Chatbot API',
    description='API for the BCourses Chatbot with RAG capabilities. To use authenticated endpoints:\n\n'
    '1. First get a token using the `/api/auth/token` endpoint with your username/password\n\n'
    "2. Click the 'Authorize' button and enter your token (without 'Bearer ' prefix)\n\n"
    '3. All API calls will now use your authorization token',
    version='1.0.0',
    docs_url='/api/docs',  # Swagger UI will be available at /api/docs
    redoc_url='/api/redoc',  # Redoc will be available at /api/redoc
    openapi_url='/api/openapi.json',
)

# Initialize enhanced logger with FastAPI app
initialize_logger(app)
logger.info('Enhanced logging system initialized with FastAPI app')

# Configure CORS
logger.info('Configuring CORS middleware')
app.add_middleware(
    CORSMiddleware,
    # For production, specify exactly your frontend URL
    # For local development, include localhost URLs
    allow_origins=[
        settings.FRONTEND_URL,  # Main frontend URL from settings
        'http://localhost:8501',  # Default Streamlit port
        'https://localhost:8501',
    ],
    allow_credentials=True,  # Important for cookies
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include routers
logger.info('Including API routers')
app.include_router(auth.router, prefix='/api/auth', tags=['auth'])
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
    """Simple health check endpoint."""
    logger.debug('Health check endpoint accessed')
    return {'status': 'ok', 'message': 'API is healthy'}
