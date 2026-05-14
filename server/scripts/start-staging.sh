#!/bin/bash
#
# start-staging.sh — staging equivalent of start.sh (S7-10).
#
# Identical to start.sh except:
#   1. Layers in docker-compose.staging.yml (S7-09) which extends the
#      OpenEMR healthcheck start_period to 15 minutes for slower Proxmox
#      hardware.
#   2. Runs `alembic upgrade head` at the end so migrations are applied as
#      part of deploy (dev users run alembic manually after editing
#      migrations; staging has no live mount so it needs to be automatic).
#
# `git pull` and `docker compose build --no-cache` are intentionally NOT in
# this script — they are deploy steps, not "start the stack" steps. Run
# them before this script when doing a full code refresh. Keeping them
# separate means start-staging.sh is safe to re-run if you just want to
# restart the stack.

set -e

echo "Starting Zoomly staging stack..."
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d

echo "Waiting for OpenEMR to be healthy (up to ~15 min on Proxmox)..."
until docker exec openemr curl -sf http://localhost:80/ > /dev/null 2>&1; do
    echo "  OpenEMR not ready yet, waiting..."
    sleep 5
done

echo "Fixing Zoomly file permissions..."
docker exec openemr chmod 755 /var/www/localhost/htdocs/openemr/library/zoomly
docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/library/zoomly/ZoomBridge.php

docker exec openemr chmod 755 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener
docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/openemr.bootstrap.php
docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/Bootstrap.php
docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/AppointmentListener.php
docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/DialogCloseListener.php

echo "Waiting for module init to complete..."
docker wait zoomly-module-init

echo "Running database migrations..."
docker exec zoom-bridge uv run alembic upgrade head

echo "Staging stack ready."
