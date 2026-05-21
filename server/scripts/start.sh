#!/bin/bash

set -e

echo "Starting Zoomly stack..."
docker compose up -d

echo "Waiting for OpenEMR to be healthy..."
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

docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/library/patient_tracker.inc.php
docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/interface/patient_tracker/patient_tracker.php

echo "Waiting for module init to complete..."
docker wait zoomly-module-init

echo "Stack ready."