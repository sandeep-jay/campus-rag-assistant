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

from app.core.config_manager import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title='RTL Services Support Chatbot API',
    description='API for the RTL Services Support Chatbot with RAG capabilities.',
    version='0.1.0',
)

# Configure CORS
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

# TODO: Include routers

@app.get('/')
async def root() -> dict:
    return {'message': 'Welcome to RTL Services Support Chatbot API'}


@app.get('/api/health')
async def health_check() -> dict:
    # Simple health check endpoint.
    return {'status': 'ok', 'message': 'API is healthy'}
