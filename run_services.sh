#!/bin/bash
set -e

# Activate virtual environment
source /var/app/venv/*/bin/activate

WORKERS="${API_WORKERS:-${UVICORN_WORKERS:-2}}"
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
UVICORN_ARGS=(backend.app.main:app --host "$HOST" --port "$PORT")

# Start FastAPI (multi-worker by default for concurrent auth + chat)
if [ "${WORKERS}" = "1" ]; then
  uvicorn "${UVICORN_ARGS[@]}" &
else
  uvicorn "${UVICORN_ARGS[@]}" --workers "${WORKERS}" &
fi

# Start Streamlit
streamlit run frontend-streamlit/app/main.py --server.port 8501 --server.address 0.0.0.0 &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
