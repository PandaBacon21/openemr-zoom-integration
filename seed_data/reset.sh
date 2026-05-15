#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env for DB credentials
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

DB_ROOT_PASS=${MYSQL_ROOT_PASSWORD:-change-me-db-root}
DB_CONTAINER=${MARIADB_CONTAINER:-mariadb-emr}
DB_NAME=${OPENEMR_DB_NAME:-openemr}

echo "Clearing demo data from $DB_CONTAINER..."

docker exec -i "$DB_CONTAINER" mariadb -u root -p"$DB_ROOT_PASS" "$DB_NAME" <<EOF
SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM openemr_postcalendar_events WHERE pc_aid IN ('10','11','12','13');
DELETE FROM patient_data WHERE pid BETWEEN 100 AND 129;
DELETE FROM openemr_postcalendar_categories
  WHERE pc_catname IN ('zoom-telehealth','new-patient-zoom','new-patient-in-person','phone-consult','in-person');
DELETE FROM users WHERE id IN (10,11,12,13,20,21,30,31);
DELETE FROM users_secure WHERE id IN (10,11,12,13,20,21,30,31);
DELETE FROM gacl_aro WHERE id BETWEEN 12 AND 19;
DELETE FROM groups WHERE user IN ('moconnor','erodriguez','amiller','mthompson','blee','amartin','bwilliams','hsong');
DELETE FROM facility WHERE id = 1;
DELETE FROM patient_access_onsite WHERE pid BETWEEN 100 AND 129;
DELETE FROM openemr_postcalendar_categories WHERE pc_catname IN ('Telehealth Zoom', 'New Patient Zoom');
DELETE FROM openemr_postcalendar_categories WHERE pc_catname LIKE 'Zoom %';

-- Sprint 12 master data
DELETE FROM addresses WHERE foreign_id BETWEEN 200 AND 207;
DELETE FROM insurance_companies WHERE id BETWEEN 200 AND 207;

DELETE FROM forms WHERE pid BETWEEN 100 AND 129;
DELETE FROM form_encounter WHERE pid BETWEEN 100 AND 129;
DELETE FROM form_soap WHERE pid BETWEEN 100 AND 129;
DELETE FROM form_clinical_notes WHERE pid BETWEEN 100 AND 129;

UPDATE sequences SET id = COALESCE((SELECT MAX(encounter) FROM form_encounter), 1);

UPDATE globals SET gl_value = '1' WHERE gl_name = 'use_email_for_portal_username';
UPDATE facility SET inactive = 0, name = 'Your Clinic Name Here' WHERE id = 3;
UPDATE users SET facility_id = 3 WHERE id = 1;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'Reset complete.' AS status;
SELECT COUNT(*) AS remaining_appointments FROM openemr_postcalendar_events WHERE pc_aid IN ('10','11','12','13');
SELECT COUNT(*) AS remaining_patients FROM patient_data WHERE pid BETWEEN 100 AND 129;
SELECT COUNT(*) AS remaining_providers FROM users WHERE id IN (10,11,12,13,20,21,30,31);
SELECT COUNT(*) AS remaining_encounters FROM form_encounter WHERE pid BETWEEN 100 AND 129;
EOF


docker exec zoom-bridge uv run python -c "
import sys
sys.path.insert(0, '/app')
from app import create_app
from app.extensions import db
from app.models import MeetingRecord, MeetingPatient, AppointmentTypeFilter, ClinicalNoteRecord, AuditLog
app = create_app()
with app.app_context():
    ClinicalNoteRecord.query.delete()
    MeetingRecord.query.delete()
    MeetingPatient.query.delete()
    AppointmentTypeFilter.query.delete()
    AuditLog.query.delete()
    db.session.commit()
    print('Flask DB cleared.')
"

echo "Done."