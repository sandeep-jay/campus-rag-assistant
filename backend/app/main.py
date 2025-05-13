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

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langsmith import Client

from backend.app.api import api_router
from backend.app.core.config_manager import settings
from backend.app.core.logger import initialize_logger, logger
from backend.app.db.database import Base, engine

# Create database tables
logger.info('Initializing database tables')
Base.metadata.create_all(bind=engine)
logger.info('Database tables initialized successfully')

# Initialize LangSmith client if API key is available
if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
    # LangSmith library seems to expect that these environment variables are explicity set
    os.environ['LANGCHAIN_TRACING_V2'] = 'true'
    os.environ['LANGCHAIN_API_KEY'] = settings.LANGCHAIN_API_KEY
    os.environ['LANGCHAIN_PROJECT'] = settings.LANGCHAIN_PROJECT

    client = Client()
    logger.info('LangSmith client initialized successfully')
    logger.info(f'LangSmith project: {settings.LANGCHAIN_PROJECT}')
else:
    logger.warning('LangSmith tracing is disabled. Please check LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY settings.')

app = FastAPI(
    title='RTL Services Support Chatbot API',
    description='API for the RTL Services Support Chatbot with RAG capabilities.',
    version='0.1.0',
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
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include API routers
logger.info('TODO: Including API routers')
app.include_router(api_router, prefix='/api')


@app.get('/')
async def root():
    logger.debug('Root endpoint accessed')
    return {'message': 'Welcome to RTL Services Support Chatbot API'}


@app.get('/api/health')
async def health_check():
    """Simple health check endpoint."""
    logger.debug('Health check endpoint accessed')
    return {'status': 'ok', 'message': 'API is healthy'}
