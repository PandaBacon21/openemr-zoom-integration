# Custom Zoomly OpenEMR image.
#
# Bakes every patch under openemr/patches/ and every branding asset under
# openemr/branding/ into the OpenEMR 8.0.0 base, with apache:apache ownership
# and 644 file perms, so that:
#   - The dozen+ patch bind mounts in docker-compose.yml are unnecessary
#   - The `branding` init container is unnecessary
#   - The post-up chmod block in start-*.sh is unnecessary
#
# Build context is the repo root so this Dockerfile can reach both openemr/patches/
# and openemr/branding/. Build from the repo root with:
#   docker compose build openemr


FROM openemr/openemr:8.0.0

# Two destinations don't exist in the stock image — create them with apache
# ownership so the parent dirs match upstream perms before files land in them.
RUN mkdir -p /var/www/localhost/htdocs/openemr/library/zoomly \
             /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener \
 && chown apache:apache /var/www/localhost/htdocs/openemr/library/zoomly \
                        /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener \
 && chmod 755 /var/www/localhost/htdocs/openemr/library/zoomly \
              /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener

# ─── OAuth2 / SMART patches ──────────────────────────────────────────────────
# AuthorizationController / OAuth2AuthorizationListener: fix DELETE 403 from
# registration_access_token column mismatch + OAuth2 dispatch routing.
# RsaSha384Signer: multi-client JWT kid lookup fix (S7-08).
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/AuthorizationController.php \
     /var/www/localhost/htdocs/openemr/src/RestControllers/AuthorizationController.php
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/OAuth2AuthorizationListener.php \
     /var/www/localhost/htdocs/openemr/src/RestControllers/Subscriber/OAuth2AuthorizationListener.php
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/RsaSha384Signer.php \
     /var/www/localhost/htdocs/openemr/src/Common/Auth/OpenIDConnect/JWT/RsaSha384Signer.php

# ─── Zoom Appointment Listener module ────────────────────────────────────────
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/zoom_appointment_listener/AppointmentListener.php \
     openemr/patches/zoom_appointment_listener/Bootstrap.php \
     openemr/patches/zoom_appointment_listener/DialogCloseListener.php \
     openemr/patches/zoom_appointment_listener/openemr.bootstrap.php \
     /var/www/localhost/htdocs/openemr/interface/modules/custom_modules/zoom_appointment_listener/

# ─── Calendar patches (Start Zoom Meeting button + day/week/month templates) ─
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/add_edit_event.php \
     /var/www/localhost/htdocs/openemr/interface/main/calendar/add_edit_event.php
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/post_calendar/ajax_template.html \
     /var/www/localhost/htdocs/openemr/interface/main/calendar/modules/PostCalendar/pntemplates/default/views/day/ajax_template.html
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/post_calendar/week/ajax_template.html \
     /var/www/localhost/htdocs/openemr/interface/main/calendar/modules/PostCalendar/pntemplates/default/views/week/ajax_template.html
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/post_calendar/month/ajax_template.html \
     /var/www/localhost/htdocs/openemr/interface/main/calendar/modules/PostCalendar/pntemplates/default/views/month/ajax_template.html

# ─── Patient Flow Board patches (Telehealth column + Zoom button) ────────────
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/patient_tracker.inc.php \
     /var/www/localhost/htdocs/openemr/library/patient_tracker.inc.php
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/patient_tracker.php \
     /var/www/localhost/htdocs/openemr/interface/patient_tracker/patient_tracker.php

# ─── Encounter clinical note fetcher (Retrieve / Complete Zoom Note) ─────────
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/clinical_note_fetcher/forms.php \
     /var/www/localhost/htdocs/openemr/interface/patient_file/encounter/forms.php
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/clinical_note_fetcher/fetch_zoom_note.php \
     /var/www/localhost/htdocs/openemr/interface/patient_file/encounter/fetch_zoom_note.php
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/clinical_note_fetcher/complete_zoom_note.php \
     /var/www/localhost/htdocs/openemr/interface/patient_file/encounter/complete_zoom_note.php

# ─── Shared HMAC signing helper for PHP → Flask calls ────────────────────────
COPY --chown=apache:apache --chmod=644 \
     openemr/patches/library/zoomly/ZoomBridge.php \
     /var/www/localhost/htdocs/openemr/library/zoomly/ZoomBridge.php

# ─── Branding assets ─────────────────────────────────────────────────────────
# Replaces the `branding` init container. Lands every file under
# public/images/logos/ that the container used to write into the openemr_public
# volume. With openemr_public removed from docker-compose.yml, these are the
# authoritative branding source at runtime.
COPY --chown=apache:apache --chmod=644 \
     openemr/branding/core/login/primary/logo.png \
     /var/www/localhost/htdocs/openemr/public/images/logos/core/login/primary/logo.png
COPY --chown=apache:apache --chmod=644 \
     openemr/branding/core/menu/primary/logo.png \
     /var/www/localhost/htdocs/openemr/public/images/logos/core/menu/primary/logo.png
COPY --chown=apache:apache --chmod=644 \
     openemr/branding/core/favicon/favicon.ico \
     /var/www/localhost/htdocs/openemr/public/images/logos/core/favicon/favicon.ico
COPY --chown=apache:apache --chmod=644 \
     openemr/branding/core/login/primary/logo.png \
     /var/www/localhost/htdocs/openemr/public/images/logos/portal/login/primary/logo.png
COPY --chown=apache:apache --chmod=644 \
     openemr/branding/core/menu/primary/logo.png \
     /var/www/localhost/htdocs/openemr/public/images/logos/portal/menu/primary/logo.png
COPY --chown=apache:apache --chmod=644 \
     openemr/branding/Product_Meetings_Light_Badge-Solo.png \
     /var/www/localhost/htdocs/openemr/public/images/logos/Product_Meetings_Light_Badge-Solo.png
COPY --chown=apache:apache --chmod=644 \
     openemr/branding/Product_Meetings_Bloom_Badge-Solo.png \
     /var/www/localhost/htdocs/openemr/public/images/logos/Product_Meetings_Bloom_Badge-Solo.png
