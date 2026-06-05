#!/bin/bash
#
# start-prod.sh — production stack startup.
#
# Production differences vs dev/staging:
#   1. No --profile non-prod flag → DbGate is not started (its compose service
#      is gated by that profile, and ENABLE_DBGATE must also be unset/false so
#      the Flask reverse-proxy blueprint is never registered).
#   2. Explicit `-f docker-compose.yml` only → no patches overlay, no
#      docker-compose.override.yml (which is gitignored and dev-only), no
#      staging overlay. The image is always authoritative.
#   3. OpenEMR image must be built from openemr/Dockerfile (patches + branding
#      baked in). `docker compose up` will trigger the build the first time if
#      the image is missing locally; in steady-state deploys, `docker compose
#      build openemr` should be run before this script as part of the deploy.
#   4. `alembic upgrade head` runs at the end (same as staging — no live code
#      mount means deploys need explicit migration application).
#
# `git pull` and `docker compose build --no-cache` are intentionally NOT in
# this script — they are deploy steps, not "start the stack" steps. Run them
# before this script when doing a full code refresh. Keeping them separate
# means start-prod.sh is safe to re-run if you just want to restart the stack.

set -e

echo "Starting Zoomly production stack..."
docker compose -f docker-compose.yml up -d

echo "Waiting for OpenEMR to be healthy..."
until docker exec openemr curl -sf http://localhost:80/ > /dev/null 2>&1; do
    echo "  OpenEMR not ready yet, waiting..."
    sleep 5
done

echo "Waiting for module init to complete..."
docker wait zoomly-module-init

echo "Running database migrations..."
docker exec zoom-bridge uv run alembic upgrade head

echo "Production stack ready."
