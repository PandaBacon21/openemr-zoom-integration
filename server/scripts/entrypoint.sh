#!/bin/sh
set -e

echo "Running Alembic migrations..."
uv run alembic upgrade head

echo "Starting Flask..."
exec uv run run.py