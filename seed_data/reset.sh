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

DELETE FROM openemr_postcalendar_events WHERE CAST(pc_pid AS UNSIGNED) BETWEEN 100 AND 150;
DELETE FROM patient_data WHERE pid BETWEEN 100 AND 150;
DELETE FROM openemr_postcalendar_categories
  WHERE pc_catname IN ('zoom-telehealth','new-patient-zoom','new-patient-in-person','phone-consult','in-person');
DELETE FROM users WHERE id IN (10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,30,31,32,33,34,35,36);
DELETE FROM users_secure WHERE id IN (10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,30,31,32,33,34,35,36);
DELETE FROM gacl_aro WHERE id BETWEEN 12 AND 36;
DELETE FROM groups WHERE user IN ('moconnor','erodriguez','amiller','mthompson','blee','amartin','bwilliams','hsong',
                                  'jonathan.nelson','priya.patel','michael.chen','marcus.eriksson','yuki.tanaka','ethan.garcia',
                                  'lucas.johnson','dave.anderson','joe.smith','lisa.patel','hiroshi.tanaka','david.thompson',
                                  'sarah.martinez','ken.watanabe','maria.rodriguez','emma.wilson','cheryl.lewis');
DELETE FROM facility WHERE id IN (1, 2, 4, 5);
DELETE FROM patient_access_onsite WHERE pid BETWEEN 100 AND 150;
DELETE FROM openemr_postcalendar_categories WHERE pc_catname IN ('Telehealth Zoom', 'New Patient Zoom');
DELETE FROM openemr_postcalendar_categories WHERE pc_catname LIKE 'Zoom %';

-- Sprint 12 master data
DELETE FROM addresses WHERE foreign_id BETWEEN 200 AND 207;
DELETE FROM insurance_companies WHERE id BETWEEN 200 AND 207;

-- Sprint 12 clinical data (must run before patient_data delete; FK_CHECKS=0
-- means order is for clarity rather than constraint enforcement, but the
-- lists_medication / procedure_* chains still go child-first so the
-- intermediate state is sane if anyone runs the block partially.)
DELETE FROM lists_medication WHERE list_id IN (SELECT id FROM lists WHERE pid BETWEEN 100 AND 150);
DELETE FROM lists           WHERE pid        BETWEEN 100 AND 150;
DELETE FROM prescriptions   WHERE patient_id BETWEEN 100 AND 150;
DELETE FROM form_vitals     WHERE pid        BETWEEN 100 AND 150;
DELETE FROM history_data    WHERE pid        BETWEEN 100 AND 150;
DELETE FROM immunizations   WHERE patient_id BETWEEN 100 AND 150;
DELETE FROM insurance_data  WHERE pid        BETWEEN 100 AND 150;

-- procedure_* chain (labs from S12-11)
DELETE FROM procedure_result      WHERE procedure_report_id IN (SELECT procedure_report_id FROM procedure_report WHERE procedure_order_id IN (SELECT procedure_order_id FROM procedure_order WHERE patient_id BETWEEN 100 AND 150));
DELETE FROM procedure_report      WHERE procedure_order_id  IN (SELECT procedure_order_id FROM procedure_order WHERE patient_id BETWEEN 100 AND 150);
DELETE FROM procedure_order_code  WHERE procedure_order_id  IN (SELECT procedure_order_id FROM procedure_order WHERE patient_id BETWEEN 100 AND 150);
DELETE FROM procedure_order       WHERE patient_id BETWEEN 100 AND 150;

DELETE FROM forms WHERE pid BETWEEN 100 AND 150;
DELETE FROM form_encounter WHERE pid BETWEEN 100 AND 150;
DELETE FROM form_soap WHERE pid BETWEEN 100 AND 150;
DELETE FROM form_clinical_notes WHERE pid BETWEEN 100 AND 150;

UPDATE sequences SET id = COALESCE((SELECT MAX(encounter) FROM form_encounter), 1);

UPDATE globals SET gl_value = '1' WHERE gl_name = 'use_email_for_portal_username';
UPDATE facility SET inactive = 0, name = 'Your Clinic Name Here' WHERE id = 3;
UPDATE users SET facility_id = 3 WHERE id = 1;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'Reset complete.' AS status;
SELECT COUNT(*) AS remaining_appointments FROM openemr_postcalendar_events WHERE CAST(pc_pid AS UNSIGNED) BETWEEN 100 AND 150;
SELECT COUNT(*) AS remaining_patients FROM patient_data WHERE pid BETWEEN 100 AND 150;
SELECT COUNT(*) AS remaining_providers FROM users WHERE id IN (10,11,12,13,20,21,30,31);
SELECT COUNT(*) AS remaining_encounters FROM form_encounter WHERE pid BETWEEN 100 AND 150;
SELECT COUNT(*) AS remaining_lists FROM lists WHERE pid BETWEEN 100 AND 150;
SELECT COUNT(*) AS remaining_prescriptions FROM prescriptions WHERE patient_id BETWEEN 100 AND 150;
SELECT COUNT(*) AS remaining_vitals FROM form_vitals WHERE pid BETWEEN 100 AND 150;
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