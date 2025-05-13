# Chabot
RTL Chabot platform with RAG capabilities. Uses Fast API backend.

## Prerequisites

- Python 3.11+
- PostgreSQL 13+
- AWS account with Bedrock access

## Installation 
1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the environment file and update the values:
```bash
cp .env.example .env
```

4. Create the database:
```bash
createuser chatbot --no-createdb --no-superuser --no-createrole --pwprompt
createdb chatbot
```

## Development
### Running the Application

1. Start the backend server:
```bash
uvicorn backend.app.main:app --reload
```

2. In a new terminal, start the frontend:
```bash
cd frontend
streamlit run app/main.py
```

## Testing
### Run all tests using tox including linters
tox

### Code Quality

The project uses Ruff for code quality checks:
```bash

# Run them separately:
# Check linting
ruff check backend frontend

# Format code
ruff format backend frontend
```

