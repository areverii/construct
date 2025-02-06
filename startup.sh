#!/usr/bin/env bash

set -e

# remove old containers
docker compose down --remove-orphans || true

# build images without cache
docker compose build --no-cache

# start containers in the background
docker compose up -d

echo "containers started. run 'docker compose logs -f' or visit http://localhost:8000"