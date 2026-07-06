#!/bin/bash
#
# start-dev.sh — dev stack startup (renamed from start.sh).
#
# Behavior:
#   - Default: docker-compose.yml + auto-loaded docker-compose.override.yml.
#     The override carries the Flask dev server (FLASK_DEBUG, debug command,
#     live ./server/app mount) AND the openemr/patches/ bind mounts that shadow
#     the baked OpenEMR image. Edit a .php in openemr/patches/, refresh the page, mod_php
#     picks it up — no image rebuild. Bind-mounted files inherit host
#     ownership so the chmod block runs to fix perms to apache:apache + 644.
#     --profile non-prod includes DbGate.
#
#   - --baked: explicit `-f docker-compose.yml` skips the override entirely,
#     so OpenEMR runs from the baked zoomly-openemr:local image with no patch
#     shadowing, and zoom-bridge runs gunicorn-gevent (not the Flask dev
#     server). Use this to simulate staging/prod locally and confirm the
#     baked image works before deploying. No chmod block — the image already
#     has correct ownership.
#
# On a fresh clone: copy docker-compose.override.yml.example to
# docker-compose.override.yml. Without that file, the default mode runs as
# if --baked were passed (no patch shadowing, gunicorn) — the stack still
# works, but you lose the fast-iteration loop.

set -e

if [[ "$1" == "--baked" ]]; then
    echo "Starting Zoomly dev stack (--baked: image-authoritative, no override)..."
    docker compose -f docker-compose.yml --profile non-prod up -d

    echo "Waiting for OpenEMR to be healthy..."
    until docker exec openemr curl -sf http://localhost:80/ > /dev/null 2>&1; do
        echo "  OpenEMR not ready yet, waiting..."
        sleep 5
    done
else
    echo "Starting Zoomly dev stack (override active — Flask dev server + patches bind mounts)..."
    docker compose --profile non-prod up -d

    echo "Waiting for OpenEMR to be healthy..."
    until docker exec openemr curl -sf http://localhost:80/ > /dev/null 2>&1; do
        echo "  OpenEMR not ready yet, waiting..."
        sleep 5
    done

    echo "Fixing patch file permissions (bind-mounted, rw only)..."
    # :ro-mounted patches (AuthorizationController, OAuth2AuthorizationListener,
    # RsaSha384Signer, post_calendar/week + month, patient_tracker.inc.php,
    # patient_tracker.php) reject chmod with "Read-only file system" — the host
    # files are 644 already, so apache can read them through the mount.
    docker exec openemr chmod 755 /var/www/localhost/htdocs/openemr/library/zoomly
    docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/library/zoomly/ZoomBridge.php

    docker exec openemr chmod 755 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener
    docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/openemr.bootstrap.php
    docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/Bootstrap.php
    docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/AppointmentListener.php
    docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/DialogCloseListener.php
fi

echo "Waiting for module init to complete..."
docker wait zoomly-module-init

echo "Running database migrations..."
docker exec zoom-bridge uv run alembic upgrade head

echo "Dev stack ready."
