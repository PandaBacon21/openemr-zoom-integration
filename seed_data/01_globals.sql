-- =============================================================================
-- Zoomly Demo Seed Data
-- OpenEMR 8.0.0
--
-- Usage:
--   ./seed_data/seed.sh
--
-- To reset:
--   ./seed_data/reset.sh
--
-- Appointment categories in this seed (all Zoom-prefixed, telehealth-themed):
--   Zoom Behavioral Health, Zoom Chronic Care, Zoom MAT (Suboxone),
--   Zoom New Patient, Zoom Preventive
--
-- Every appointment row in this seed lives under one of the five categories
-- above. OpenEMR built-in categories (Office Visit, Established Patient,
-- New Patient, etc.) remain in the DB but are no longer referenced. Zoomly's
-- per-account AppointmentTypeFilter can opt in/out of the Zoom set as a
-- group, or by specialty (e.g. a behavioral-health-focused SE picks only
-- Zoom Behavioral Health + Zoom MAT + Zoom New Patient).
--
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- Widen pc_website to accommodate full Zoom start URLs with zak tokens
ALTER TABLE openemr_postcalendar_events MODIFY pc_website VARCHAR(1024);

-- Hide SQL debug modal pop up screen
UPDATE globals SET gl_value = '1' WHERE gl_name = 'sql_string_no_show_screen';

-- Disable provider availability check
UPDATE globals SET gl_value = '0' WHERE gl_name = 'schedule_limit';

-- Require facility selection on login so the calendar/provider lists scope to
-- the user's facility from the start (instead of showing all providers across
-- all facilities until the user picks one from the calendar dropdown).
UPDATE globals SET gl_value = '1' WHERE gl_name = 'login_into_facility';

