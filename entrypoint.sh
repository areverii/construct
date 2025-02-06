#!/bin/sh
set -e

# Default to running the FastAPI server
if [ "$#" -eq 0 ]; then
    echo "Starting FastAPI server..."
    exec poetry run uvicorn construct.api:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Running command: $@"
    exec "$@"
fi