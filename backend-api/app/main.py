from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title='RTL Chatbot API',
    description='API for the RTL Chatbot with RAG capabilities.',
    version='0.1.0',
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# TODO: Include routers

@app.get('/')
async def root() -> dict:
    return {'message': 'Welcome to BCourses Chatbot API'}


@app.get('/api/health')
async def health_check() -> dict:
    # Simple health check endpoint.
    return {'status': 'ok', 'message': 'API is healthy'}
