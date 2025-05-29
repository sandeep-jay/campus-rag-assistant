#!/bin/bash
set -e

# Activate virtual environment
source /var/app/venv/*/bin/activate

# Start FastAPI
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit
streamlit run frontend/app/main.py --server.port 8501 --server.address 0.0.0.0 &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?