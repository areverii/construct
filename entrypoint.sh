#!/bin/sh
set -e

# Default to API mode if no arguments are given
if [ "$#" -eq 0 ]; then
    echo "Starting API mode..."
    exec poetry run python -m construct.main run-api
else
    echo "Running command: $@"
    exec "$@"
fi