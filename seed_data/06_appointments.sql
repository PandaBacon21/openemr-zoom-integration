-- =============================================================================
-- 06 — APPOINTMENTS (292 total: 112 original + 72 Sprint 12/13 + 108 panel-expansion)
--
-- Order in file:
--   a) Original 112 appointments across 14 days (DAY 1 ... DAY 14)
--   b) Persona-driven category pivot (UPDATEs + pc_title sync)
--   c) S12-20 drop Zoom Cardiology (absorbed into Zoom Chronic Care — kept
--      as a historical no-op now that seeded appointments are non-Zoom)
--   d) S12-29 pc_aid retarget UPDATE (point at each patient's new providerID)
--   e) 72 new appointments for PIDs 130-150 + Sarah Chen panel appointments
--   f) 108 panel-expansion appointments for PIDs 172-207
--
-- S13 update: every appointment seeded by this file uses an OpenEMR built-in
-- category (Office Visit / Established Patient / New Patient / Behavioral
-- Assessment / Preventive Care). Zoom-typed appointments are created only by
-- the Hydrate Demo Data flow (server/app/services/hydrate*), so the pre-seeded
-- calendar never carries Zoom slots without real Zoom meetings behind them.
-- The Zoom-prefixed categories themselves still exist in
-- openemr_postcalendar_categories so SEs can pick them ad-hoc.
-- =============================================================================

-- =============================================================================
-- APPOINTMENTS
--
-- 2 appointments per provider per day × 4 providers × 14 days = 112 total
--
-- Patient assignment strategy:
--   - Each patient's FIRST appointment with a provider = New Patient
--   - Subsequent appointments = Established Patient or Office Visit
--   - Mix in Preventive Care, Behavioral Assessment sparingly for realism
--
-- Provider → specialty → realistic appointment mix:
--   10 (OConnor, Internal Medicine):  Office Visit, Established, Preventive Care
--   11 (Rodriguez, Family Medicine):  Office Visit, Established, New Patient
--   12 (Miller, Psychiatry):          Established, Behavioral Assessment
--   13 (Thompson, Cardiology):        Office Visit, Established, New Patient
--
-- Provider IDs: 10=OConnor, 11=Rodriguez, 12=Miller, 13=Thompson
-- Patient pool: PIDs 100-129, cycling through providers
-- =============================================================================

-- =============================================================================
-- WEEKDAY-ONLY DATE COMPUTATION
--
-- Compute day-variables (@day1 through @day14) as the next 14 weekday dates starting tomorrow
-- (or the following Monday if tomorrow is Sat/Sun). MariaDB's WEEKDAY() returns
-- 0=Mon, 1=Tue, ..., 4=Fri, 5=Sat, 6=Sun. The N-th weekday from @apt_base is:
--   @apt_base + (N-1) + FLOOR(((N-1) + WEEKDAY(@apt_base)) / 5) * 2  days
-- This adds 2 calendar days every time we'd cross a weekend.
-- =============================================================================

SET @apt_base = DATE_ADD(CURDATE(), INTERVAL 1 DAY);
SET @apt_base = CASE WEEKDAY(@apt_base)
                  WHEN 5 THEN DATE_ADD(@apt_base, INTERVAL 2 DAY)  -- Sat → Mon
                  WHEN 6 THEN DATE_ADD(@apt_base, INTERVAL 1 DAY)  -- Sun → Mon
                  ELSE @apt_base
                END;
SET @apt_dow = WEEKDAY(@apt_base);

SET @day1  = DATE_ADD(@apt_base, INTERVAL ( 0 + FLOOR(( 0 + @apt_dow) / 5) * 2) DAY);
SET @day2  = DATE_ADD(@apt_base, INTERVAL ( 1 + FLOOR(( 1 + @apt_dow) / 5) * 2) DAY);
SET @day3  = DATE_ADD(@apt_base, INTERVAL ( 2 + FLOOR(( 2 + @apt_dow) / 5) * 2) DAY);
SET @day4  = DATE_ADD(@apt_base, INTERVAL ( 3 + FLOOR(( 3 + @apt_dow) / 5) * 2) DAY);
SET @day5  = DATE_ADD(@apt_base, INTERVAL ( 4 + FLOOR(( 4 + @apt_dow) / 5) * 2) DAY);
SET @day6  = DATE_ADD(@apt_base, INTERVAL ( 5 + FLOOR(( 5 + @apt_dow) / 5) * 2) DAY);
SET @day7  = DATE_ADD(@apt_base, INTERVAL ( 6 + FLOOR(( 6 + @apt_dow) / 5) * 2) DAY);
SET @day8  = DATE_ADD(@apt_base, INTERVAL ( 7 + FLOOR(( 7 + @apt_dow) / 5) * 2) DAY);
SET @day9  = DATE_ADD(@apt_base, INTERVAL ( 8 + FLOOR(( 8 + @apt_dow) / 5) * 2) DAY);
SET @day10 = DATE_ADD(@apt_base, INTERVAL ( 9 + FLOOR(( 9 + @apt_dow) / 5) * 2) DAY);
SET @day11 = DATE_ADD(@apt_base, INTERVAL (10 + FLOOR((10 + @apt_dow) / 5) * 2) DAY);
SET @day12 = DATE_ADD(@apt_base, INTERVAL (11 + FLOOR((11 + @apt_dow) / 5) * 2) DAY);
SET @day13 = DATE_ADD(@apt_base, INTERVAL (12 + FLOOR((12 + @apt_dow) / 5) * 2) DAY);
SET @day14 = DATE_ADD(@apt_base, INTERVAL (13 + FLOOR((13 + @apt_dow) / 5) * 2) DAY);

INSERT INTO `openemr_postcalendar_events` (
    `pc_catid`, `pc_multiple`, `pc_aid`, `pc_pid`,
    `pc_title`, `pc_time`, `pc_hometext`,
    `pc_eventDate`, `pc_endDate`,
    `pc_duration`, `pc_recurrtype`, `pc_recurrfreq`,
    `pc_recurrspec`, `pc_location`,
    `pc_startTime`, `pc_endTime`,
    `pc_alldayevent`, `pc_apptstatus`, `pc_eventstatus`,
    `pc_sharing`, `pc_facility`, `pc_billing_location`,
    `pc_informant`, `pc_sendalertsms`, `pc_sendalertemail`,
    `uuid`
) VALUES

-- =============================================================================
-- DAY 1
-- =============================================================================
-- OConnor: pid 100 new patient, then pid 104 established
(@new_patient_catid,    0, '10', '100', 'New Patient',           NOW(), 'Initial intake visit',
 @day1, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@office_visit_catid,   0, '10', '104', 'Office Visit',          NOW(), 'Routine follow-up',
 @day1, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '10:00:00', '10:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- Rodriguez: pid 101 new patient zoom, then pid 105 established
(@new_patient_zoom_catid, 0, '11', '101', 'New Patient Zoom',    NOW(), 'New patient intake',
 @day1, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '09:00:00', '09:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '11', '105', 'Established Patient',     NOW(), 'Follow-up',
 @day1, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- Miller (Psychiatry): pid 103 new patient zoom, then pid 106 telehealth
(@new_patient_zoom_catid, 0, '12', '103', 'New Patient Zoom',    NOW(), 'New psychiatric patient',
 @day1, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '09:00:00', '09:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '12', '106', 'Established Patient',     NOW(), 'Psychiatric check-in',
 @day1, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- Thompson (Cardiology): pid 102 new patient, then pid 107 telehealth
(@new_patient_catid,    0, '13', '102', 'New Patient',           NOW(), 'Initial cardiology consult',
 @day1, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '13', '107', 'Established Patient',     NOW(), 'Cardiac follow-up',
 @day1, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 2
-- =============================================================================
(@established_catid,    0, '10', '100', 'Established Patient',   NOW(), 'Follow-up visit',
 @day2, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid,     0, '10', '108', 'Preventive Care',       NOW(), 'Annual wellness screening',
 @day2, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '10:30:00', '10:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '101', 'Established Patient',   NOW(), 'Follow-up visit',
 @day2, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '109', 'New Patient Zoom',    NOW(), 'New patient intake',
 @day2, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@behavioral_catid,     0, '12', '103', 'Behavioral Assessment', NOW(), 'Mental health assessment',
 @day2, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '12', '110', 'Established Patient',     NOW(), 'Therapy session',
 @day2, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '102', 'Established Patient',   NOW(), 'Cardiology follow-up',
 @day2, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '13', '111', 'New Patient Zoom',    NOW(), 'New cardiology patient',
 @day2, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 3
-- =============================================================================
(@established_catid,  0, '10', '100', 'Established Patient',     NOW(), 'Medication review',
 @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '10', '112', 'New Patient',           NOW(), 'Initial intake visit',
 @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '11', '105', 'Established Patient',     NOW(), 'Follow-up',
 @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '11', '109', 'Established Patient',   NOW(), 'Follow-up visit',
 @day3, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '13:00:00', '13:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '12', '106', 'Established Patient',     NOW(), 'Psychiatric follow-up',
 @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '113', 'New Patient Zoom',    NOW(), 'New psychiatric patient',
 @day3, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '13', '107', 'Established Patient',     NOW(), 'Cardiac check-in',
 @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '13', '111', 'Established Patient',   NOW(), 'Cardiology follow-up',
 @day3, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 4
-- =============================================================================
(@office_visit_catid,   0, '10', '104', 'Office Visit',          NOW(), 'Routine office visit',
 @day4, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '10', '112', 'Established Patient',     NOW(), 'Follow-up',
 @day4, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@office_visit_catid,   0, '11', '101', 'Office Visit',          NOW(), 'Routine office visit',
 @day4, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '114', 'New Patient Zoom',    NOW(), 'New patient intake',
 @day4, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '12', '110', 'Established Patient',   NOW(), 'Therapy follow-up',
 @day4, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '12', '113', 'Established Patient',     NOW(), 'Psychiatric follow-up',
 @day4, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@office_visit_catid,   0, '13', '102', 'Office Visit',          NOW(), 'Cardiology office visit',
 @day4, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '13', '115', 'New Patient Zoom',    NOW(), 'New cardiology patient',
 @day4, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 5
-- =============================================================================
(@preventive_catid,     0, '10', '108', 'Preventive Care',       NOW(), 'Preventive screening follow-up',
 @day5, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '10', '100', 'Established Patient',     NOW(), 'Annual wellness',
 @day5, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '11', '109', 'Established Patient',     NOW(), 'Follow-up',
 @day5, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '11', '114', 'Established Patient',   NOW(), 'Follow-up visit',
 @day5, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@behavioral_catid,     0, '12', '106', 'Behavioral Assessment', NOW(), 'Psychiatric behavioral assessment',
 @day5, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '12', '110', 'Established Patient',     NOW(), 'Therapy session',
 @day5, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '13', '115', 'Established Patient',     NOW(), 'Cardiology follow-up',
 @day5, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '13', '111', 'Established Patient',   NOW(), 'Cardiology established visit',
 @day5, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 6
-- =============================================================================
(@office_visit_catid,   0, '10', '112', 'Office Visit',          NOW(), 'Office visit follow-up',
 @day6, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '10', '116', 'New Patient',           NOW(), 'Initial intake visit',
 @day6, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@office_visit_catid,   0, '11', '105', 'Office Visit',          NOW(), 'Routine office visit',
 @day6, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '117', 'New Patient Zoom',    NOW(), 'New patient intake',
 @day6, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '12', '113', 'Established Patient',     NOW(), 'Psychiatric session',
 @day6, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '118', 'New Patient Zoom',    NOW(), 'New psychiatric patient',
 @day6, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '11:00:00', '11:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '13', '107', 'Established Patient',     NOW(), 'Cardiac monitoring',
 @day6, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '13', '119', 'New Patient',           NOW(), 'Initial cardiology consult',
 @day6, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 7
-- =============================================================================
(@established_catid,  0, '10', '116', 'Established Patient',     NOW(), 'Follow-up',
 @day7, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '10', '104', 'Established Patient',   NOW(), 'Established patient visit',
 @day7, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '117', 'Established Patient',   NOW(), 'Follow-up visit',
 @day7, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '11', '109', 'Established Patient',     NOW(), 'Telehealth check-in',
 @day7, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '12', '118', 'Established Patient',     NOW(), 'Psychiatric follow-up',
 @day7, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '120', 'New Patient Zoom',    NOW(), 'New psychiatric patient',
 @day7, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '119', 'Established Patient',   NOW(), 'Cardiology follow-up',
 @day7, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '13', '115', 'Established Patient',     NOW(), 'Cardiac check-in',
 @day7, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 8
-- =============================================================================
(@office_visit_catid,   0, '10', '116', 'Office Visit',          NOW(), 'Office visit',
 @day8, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '10', '120', 'New Patient',           NOW(), 'Initial intake visit',
 @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '11', '117', 'Established Patient',     NOW(), 'Follow-up',
 @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '121', 'New Patient Zoom',    NOW(), 'New patient intake',
 @day8, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '12', '120', 'Established Patient',   NOW(), 'Therapy follow-up',
 @day8, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '12', '118', 'Established Patient',     NOW(), 'Psychiatric session',
 @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '13', '119', 'Established Patient',     NOW(), 'Post-procedure follow-up',
 @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '13', '122', 'New Patient',           NOW(), 'Initial cardiology consult',
 @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 9
-- =============================================================================
(@established_catid,  0, '10', '120', 'Established Patient',     NOW(), 'Follow-up',
 @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid,     0, '10', '104', 'Preventive Care',       NOW(), 'Annual wellness check',
 @day9, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '121', 'Established Patient',   NOW(), 'Follow-up visit',
 @day9, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '11', '105', 'Established Patient',     NOW(), 'Telehealth check-in',
 @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '12', '113', 'Established Patient',     NOW(), 'Psychiatric session',
 @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '123', 'New Patient Zoom',    NOW(), 'New psychiatric patient',
 @day9, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '122', 'Established Patient',   NOW(), 'Cardiology follow-up',
 @day9, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '13', '119', 'Established Patient',     NOW(), 'Cardiac monitoring',
 @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 10
-- =============================================================================
(@established_catid,    0, '10', '112', 'Established Patient',   NOW(), 'Established patient visit',
 @day10, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '10', '116', 'Established Patient',     NOW(), 'Follow-up',
 @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@office_visit_catid,   0, '11', '109', 'Office Visit',          NOW(), 'Routine office visit',
 @day10, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '124', 'New Patient Zoom',    NOW(), 'New patient intake',
 @day10, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@behavioral_catid,     0, '12', '120', 'Behavioral Assessment', NOW(), 'Psychiatric behavioral assessment',
 @day10, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '12', '123', 'Established Patient',     NOW(), 'Psychiatric session',
 @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '13', '122', 'Established Patient',     NOW(), 'Cardiac check-in',
 @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '13', '125', 'New Patient',           NOW(), 'Initial cardiology consult',
 @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 11
-- =============================================================================
(@established_catid,  0, '10', '120', 'Established Patient',     NOW(), 'Medication review',
 @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@office_visit_catid,   0, '10', '108', 'Office Visit',          NOW(), 'Office visit',
 @day11, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '124', 'Established Patient',   NOW(), 'Follow-up visit',
 @day11, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '11', '121', 'Established Patient',     NOW(), 'Telehealth check-in',
 @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '12', '118', 'Established Patient',     NOW(), 'Psychiatric session',
 @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '126', 'New Patient Zoom',    NOW(), 'New psychiatric patient',
 @day11, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '11:00:00', '11:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '125', 'Established Patient',   NOW(), 'Cardiology follow-up',
 @day11, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '13', '122', 'Established Patient',     NOW(), 'Cardiac monitoring',
 @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 12
-- =============================================================================
(@established_catid,    0, '10', '116', 'Established Patient',   NOW(), 'Established patient visit',
 @day12, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '10', '104', 'Established Patient',     NOW(), 'Follow-up',
 @day12, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '11', '124', 'Established Patient',     NOW(), 'Follow-up',
 @day12, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '127', 'New Patient Zoom',    NOW(), 'New patient intake',
 @day12, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '11:00:00', '11:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@behavioral_catid,     0, '12', '123', 'Behavioral Assessment', NOW(), 'Psychiatric behavioral assessment',
 @day12, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '12', '126', 'Established Patient',     NOW(), 'Psychiatric follow-up',
 @day12, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '13', '125', 'Established Patient',     NOW(), 'Cardiac follow-up',
 @day12, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '13', '128', 'New Patient',           NOW(), 'Initial cardiology consult',
 @day12, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 13
-- =============================================================================
(@office_visit_catid,   0, '10', '120', 'Office Visit',          NOW(), 'Office visit',
 @day13, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '10', '124', 'New Patient',           NOW(), 'Initial intake visit',
 @day13, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '127', 'Established Patient',   NOW(), 'Follow-up visit',
 @day13, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '11', '109', 'Established Patient',     NOW(), 'Telehealth check-in',
 @day13, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '12', '126', 'Established Patient',     NOW(), 'Psychiatric session',
 @day13, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '129', 'New Patient Zoom',    NOW(), 'New psychiatric patient',
 @day13, '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '11:00:00', '11:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '128', 'Established Patient',   NOW(), 'Cardiology follow-up',
 @day13, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '13', '125', 'Established Patient',     NOW(), 'Cardiac check-in',
 @day13, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 14
-- =============================================================================
(@established_catid,  0, '10', '124', 'Established Patient',     NOW(), 'Follow-up',
 @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid,     0, '10', '116', 'Preventive Care',       NOW(), 'Annual preventive care',
 @day14, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '14:00:00', '14:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '11', '127', 'Established Patient',     NOW(), 'Follow-up',
 @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '11', '121', 'Established Patient',   NOW(), 'Follow-up visit',
 @day14, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '12', '129', 'Established Patient',   NOW(), 'Therapy follow-up',
 @day14, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,  0, '12', '126', 'Established Patient',     NOW(), 'Psychiatric session',
 @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,  0, '13', '128', 'Established Patient',     NOW(), 'Cardiac follow-up',
 @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '13', '122', 'Established Patient',   NOW(), 'Cardiology established visit',
 @day14, '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '14:00:00', '14:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', '')));


-- =============================================================================
-- APPOINTMENT CATEGORY PIVOT  (S13 update)
--
-- Original Sprint 12 / S12-02 pivot moved every seeded appointment onto the
-- Zoom-prefixed telehealth categories. Sprint 13 reverses that: no SQL-seeded
-- appointment should be Zoom-typed, because the pre-seeded calendar slots
-- never have real Zoom meetings attached — only the Hydrate Demo Data flow
-- (server/app/services/hydrate*) creates Zoom-typed appointments alongside
-- actual Zoom meetings. The Zoom-prefixed categories still exist in
-- openemr_postcalendar_categories so SEs can pick them for ad-hoc calendar
-- creation; they just aren't pre-populated.
--
-- Persona retargets below use OpenEMR built-in categories instead:
--   New Patient (first visits), Behavioral Assessment (psych / BH-PC),
--   Preventive Care (HYA touchpoints), Established Patient (catch-all
--   chronic / MAT / cardiology follow-ups).
-- Mapping still driven by the S12-01 persona matrix above.
-- =============================================================================

-- 1. Universal: every first-visit appointment → New Patient
UPDATE openemr_postcalendar_events
   SET pc_catid = @new_patient_catid
 WHERE pc_aid IN ('10','11','12','13')
   AND pc_catid IN (@new_patient_catid, @new_patient_zoom_catid);

-- 2. Miller (psychiatry) established → Behavioral Assessment
UPDATE openemr_postcalendar_events
   SET pc_catid = @behavioral_catid
 WHERE pc_aid = '12'
   AND pc_catid != @new_patient_catid;

-- 4. BH-PC patients (PCP-managed depression / anxiety) → Behavioral Assessment
UPDATE openemr_postcalendar_events
   SET pc_catid = @behavioral_catid
 WHERE pc_pid IN ('101','104','109','129')
   AND pc_catid != @new_patient_catid;

-- 5. SUD patient (PID 120, buprenorphine maintenance) → Established Patient
--    (no OpenEMR built-in MAT category — Established Patient is the closest fit)
UPDATE openemr_postcalendar_events
   SET pc_catid = @established_catid
 WHERE pc_pid = '120'
   AND pc_catid != @new_patient_catid;

-- 6. HYA preventive-touchpoint patients → Preventive Care
UPDATE openemr_postcalendar_events
   SET pc_catid = @preventive_catid
 WHERE pc_pid IN ('121','125','128')
   AND pc_catid != @new_patient_catid;

-- 7. Catch-all: remaining established appointments → Established Patient
--    (CHR, GER, NEW personas — OConnor + Rodriguez chronic disease follow-ups)
UPDATE openemr_postcalendar_events
   SET pc_catid = @established_catid
 WHERE pc_aid IN ('10','11','12','13')
   AND pc_catid NOT IN (
       @new_patient_catid,
       @behavioral_catid,
       @established_catid,
       @preventive_catid
   );

-- Sync pc_title to match the new category so the calendar display matches
UPDATE openemr_postcalendar_events SET pc_title = 'New Patient'          WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @new_patient_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Behavioral Assessment' WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @behavioral_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Established Patient'   WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @established_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Preventive Care'       WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @preventive_catid;

-- Drop the legacy suffix-style custom categories — no appointments reference
-- them anymore. The newer Zoom-prefixed entries (Zoom Behavioral Health,
-- Zoom Chronic Care, Zoom MAT (Suboxone), Zoom New Patient, Zoom Preventive)
-- stay available in the calendar's appointment-type dropdown for ad-hoc
-- creation by SEs.
DELETE FROM openemr_postcalendar_categories
 WHERE pc_catname IN ('Telehealth Zoom', 'New Patient Zoom');


--
-- Step 1: retarget ALL existing 112 appointments so pc_aid matches each
-- patient's new providerID. Single JOIN-based UPDATE.
-- Step 2: add 72 appointments for PIDs 130-150 plus Sarah Chen's 168-170
-- panel (3 per patient over the 14-day window). Each appointment uses the patient's providerID (pc_aid) and
-- a persona-appropriate OpenEMR built-in category (Behavioral Assessment /
-- Established Patient / Preventive Care / New Patient). Zoom-typed
-- appointments come from the Hydrate Demo Data flow, not from seed.
-- =============================================================================

UPDATE openemr_postcalendar_events e
JOIN patient_data pd ON pd.pid = CAST(e.pc_pid AS UNSIGNED)
   SET e.pc_aid = CAST(pd.providerID AS CHAR)
 WHERE e.pc_pid REGEXP '^[0-9]+$'
   AND CAST(e.pc_pid AS UNSIGNED) BETWEEN 100 AND 207;

-- New appointments for PIDs 130-150 plus Sarah Chen's 168-170 panel (3 each, spread across days 1-14)
INSERT INTO `openemr_postcalendar_events` (
    `pc_catid`, `pc_multiple`, `pc_aid`, `pc_pid`,
    `pc_title`, `pc_time`, `pc_hometext`,
    `pc_eventDate`, `pc_endDate`,
    `pc_duration`, `pc_recurrtype`, `pc_recurrfreq`,
    `pc_recurrspec`, `pc_location`,
    `pc_startTime`, `pc_endTime`,
    `pc_alldayevent`, `pc_apptstatus`, `pc_eventstatus`,
    `pc_sharing`, `pc_facility`, `pc_billing_location`,
    `pc_informant`, `pc_sendalertsms`, `pc_sendalertemail`,
    `uuid`
) VALUES
-- PID 130 Tom Bell (PSY-S, Eriksson 17) — 3 behavioral health visits
(@behavioral_catid, 0, '17', '130', 'Behavioral Assessment', NOW(), 'OCD med management', @day2, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '17', '130', 'Behavioral Assessment', NOW(), 'OCD therapy follow-up', @day7, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '17', '130', 'Behavioral Assessment', NOW(), 'OCD med check', @day13, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 131 Janelle Cho (PSY-S, Priya Patel 15)
(@behavioral_catid, 0, '15', '131', 'Behavioral Assessment', NOW(), 'PTSD med management', @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '15', '131', 'Behavioral Assessment', NOW(), 'PTSD follow-up', @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '15', '131', 'Behavioral Assessment', NOW(), 'PTSD med check', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 132 Bryan Roberts (SUD AUD, Lucas Johnson 22)
(@established_catid, 0, '22', '132', 'Established Patient', NOW(), 'Naltrexone monthly check-in', @day4, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '22', '132', 'Established Patient', NOW(), 'AUD counseling', @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '22', '132', 'Established Patient', NOW(), 'Naltrexone refill', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 133 Ashley Cohen (SUD OUD, Lucas Johnson 22)
(@established_catid, 0, '22', '133', 'Established Patient', NOW(), 'Suboxone monthly check-in', @day5, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '22', '133', 'Established Patient', NOW(), 'Suboxone refill', @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '22', '133', 'Established Patient', NOW(), 'OUD counseling', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 134 Marcus Hill (NEW, Chen 16) — first-visit intake + follow-ups
(@new_patient_catid, 0, '16', '134', 'New Patient', NOW(), 'New patient intake', @day2, '0000-00-00', 2700, 0, 0, @recurrspec, @location, '13:00:00', '13:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '16', '134', 'Established Patient', NOW(), 'Follow-up visit', @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '16', '134', 'Established Patient', NOW(), 'Lab review', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 135 Linda Kapoor (CHR, Chen 16)
(@established_catid, 0, '16', '135', 'Established Patient', NOW(), 'T2DM quarterly check-in', @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '16', '135', 'Established Patient', NOW(), 'A1c follow-up', @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '16', '135', 'Established Patient', NOW(), 'Med refill check', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 136 Roberto Cruz (CHR, Garcia 19)
(@established_catid, 0, '19', '136', 'Established Patient', NOW(), 'HTN + HLD check-in', @day4, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '19', '136', 'Established Patient', NOW(), 'Quarterly follow-up', @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '19', '136', 'Established Patient', NOW(), 'Lipid panel review', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 137 Sasha Yang (HYA, Garcia 19)
(@preventive_catid, 0, '19', '137', 'Preventive Care', NOW(), 'Annual preventive visit', @day5, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '19', '137', 'Preventive Care', NOW(), 'MH screening follow-up', @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '19', '137', 'Preventive Care', NOW(), 'Contraception consult', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 138 Tyler Murphy (HYA, Amy Martin 21)
(@preventive_catid, 0, '21', '138', 'Preventive Care', NOW(), 'Sports physical', @day6, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '21', '138', 'Preventive Care', NOW(), 'Cholesterol screen follow-up', @day12, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '21', '138', 'Preventive Care', NOW(), 'Smoking cessation counseling', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 139 Christina Knight (BH-PC, Amy Martin 21)
(@behavioral_catid, 0, '21', '139', 'Behavioral Assessment', NOW(), 'Postpartum depression follow-up', @day7, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '21', '139', 'Behavioral Assessment', NOW(), 'SSRI tolerance check', @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '21', '139', 'Behavioral Assessment', NOW(), 'GAD med review', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 140 Hannah Kelly (HYA, Amy Martin 21)
(@preventive_catid, 0, '21', '140', 'Preventive Care', NOW(), 'Annual well-woman visit', @day2, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '21', '140', 'Preventive Care', NOW(), 'MH screening', @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '21', '140', 'Preventive Care', NOW(), 'Contraception counseling', @day13, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 141 Frank Burke (CHR, Lisa Patel 25)
(@established_catid, 0, '25', '141', 'Established Patient', NOW(), 'HTN + HLD med review', @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '25', '141', 'Established Patient', NOW(), 'Quarterly follow-up', @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '25', '141', 'Established Patient', NOW(), 'BP check + statin review', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 142 Margaret Sullivan (GER, Lisa Patel 25)
(@established_catid, 0, '25', '142', 'Established Patient', NOW(), 'Geriatric polypharmacy review', @day4, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '25', '142', 'Established Patient', NOW(), 'OA pain management', @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '25', '142', 'Established Patient', NOW(), 'Osteoporosis follow-up', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 143 Devon Banks (HYA, Lisa Patel 25)
(@preventive_catid, 0, '25', '143', 'Preventive Care', NOW(), 'Annual preventive visit', @day5, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '25', '143', 'Preventive Care', NOW(), 'MH screening', @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '25', '143', 'Preventive Care', NOW(), 'Lifestyle counseling', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 144 Mia Davies (BH-PC, Nelson 14)
(@behavioral_catid, 0, '14', '144', 'Behavioral Assessment', NOW(), 'GAD med management', @day6, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '14', '144', 'Behavioral Assessment', NOW(), 'Anxiety follow-up', @day12, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '14', '144', 'Behavioral Assessment', NOW(), 'SSRI tolerance check', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 145 Jordan Hayes (HYA, Hiroshi Tanaka 26)
(@preventive_catid, 0, '26', '145', 'Preventive Care', NOW(), 'Annual preventive visit', @day2, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '26', '145', 'Preventive Care', NOW(), 'Sports physical', @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '26', '145', 'Preventive Care', NOW(), 'Injury follow-up', @day13, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 146 Beatrice Reed (GER, Hiroshi Tanaka 26)
(@established_catid, 0, '26', '146', 'Established Patient', NOW(), 'Geriatric polypharmacy review', @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '26', '146', 'Established Patient', NOW(), 'Hypothyroid follow-up', @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '26', '146', 'Established Patient', NOW(), 'Memory screen', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 147 Caleb Cole (NEW, Anderson 23)
(@new_patient_catid, 0, '23', '147', 'New Patient', NOW(), 'New patient intake', @day4, '0000-00-00', 2700, 0, 0, @recurrspec, @location, '13:00:00', '13:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '23', '147', 'Established Patient', NOW(), 'Follow-up visit', @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '23', '147', 'Established Patient', NOW(), 'Lab review', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 148 Olivia Davis (NEW, Joe Smith 24)
(@new_patient_catid, 0, '24', '148', 'New Patient', NOW(), 'New patient intake', @day5, '0000-00-00', 2700, 0, 0, @recurrspec, @location, '13:00:00', '13:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '24', '148', 'Established Patient', NOW(), 'Follow-up visit', @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '24', '148', 'Established Patient', NOW(), 'Lab review', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 149 Marcus Curtis (HYA, Joe Smith 24)
(@preventive_catid, 0, '24', '149', 'Preventive Care', NOW(), 'Annual preventive visit', @day6, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '24', '149', 'Preventive Care', NOW(), 'Sports physical', @day12, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '24', '149', 'Preventive Care', NOW(), 'MH screening', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 150 Patricia Diaz (CHR, Joe Smith 24)
(@established_catid, 0, '24', '150', 'Established Patient', NOW(), 'HTN + HLD bilingual check-in', @day7, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '24', '150', 'Established Patient', NOW(), 'T2DM quarterly check-in', @day11, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '24', '150', 'Established Patient', NOW(), 'Med refill review', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- Sarah Chen's panel (Boston, provider 37) — PIDs 168-170 regulars, 171 diabetes
-- demo target (no future appts; past_encounter.py creates today's 8am locked one)
-- PID 168 Janet Hill (CHR, Sarah Chen 37) — HTN + HLD management
(@established_catid, 0, '37', '168', 'Established Patient', NOW(), 'HTN + HLD check-in', @day3, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '37', '168', 'Established Patient', NOW(), 'Med refill review', @day8, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid, 0, '37', '168', 'Established Patient', NOW(), 'Lipid panel review', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 169 Tasha Brooks (BH, Sarah Chen 37) — GAD/MDD care coordination
(@behavioral_catid, 0, '37', '169', 'Behavioral Assessment', NOW(), 'GAD + MDD med coordination', @day4, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '37', '169', 'Behavioral Assessment', NOW(), 'Sertraline tolerance follow-up', @day9, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@behavioral_catid, 0, '37', '169', 'Behavioral Assessment', NOW(), 'Care coordination check-in', @day13, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 170 Erik Nguyen (HYA, Sarah Chen 37) — annual wellness touchpoint
(@preventive_catid, 0, '37', '170', 'Preventive Care', NOW(), 'Annual wellness visit', @day5, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '08:30:00', '09:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '37', '170', 'Preventive Care', NOW(), 'Flu vaccine + screening', @day10, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid, 0, '37', '170', 'Preventive Care', NOW(), 'Lipid screen', @day14, '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:30:00', '16:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', '')));

-- S13/S14 panel expansion appointments — three visits per new patient.
DROP TEMPORARY TABLE IF EXISTS zoomly_panel_expansion_appts;
CREATE TEMPORARY TABLE zoomly_panel_expansion_appts (
    pid INT PRIMARY KEY,
    persona VARCHAR(8) NOT NULL,
    reason1 VARCHAR(255) NOT NULL,
    reason2 VARCHAR(255) NOT NULL,
    reason3 VARCHAR(255) NOT NULL
);

INSERT INTO zoomly_panel_expansion_appts (pid, persona, reason1, reason2, reason3) VALUES
(172, 'CHR', 'T2DM + HTN follow-up', 'A1c review', 'Medication review'),
(173, 'HYA', 'Annual preventive visit', 'Smoking cessation counseling', 'Lifestyle follow-up'),
(174, 'CHR', 'Diabetes follow-up', 'BP log review', 'Medication refill'),
(175, 'BH',  'Anxiety follow-up', 'SSRI tolerance check', 'Mood check-in'),
(176, 'BH',  'MDD med management', 'Sleep follow-up', 'Care coordination'),
(177, 'BH',  'PTSD follow-up', 'Prazosin tolerance check', 'Therapy coordination'),
(178, 'CHR', 'CAD + HTN follow-up', 'Lipid panel review', 'Medication review'),
(179, 'HYA', 'Annual preventive visit', 'Exercise counseling', 'Lab review'),
(180, 'GER', 'Geriatric wellness review', 'Polypharmacy follow-up', 'Osteoporosis check-in'),
(181, 'HYA', 'Annual preventive visit', 'Travel health counseling', 'Lifestyle follow-up'),
(182, 'BH',  'GAD med management', 'SSRI tolerance check', 'Anxiety follow-up'),
(183, 'BH',  'Bipolar II follow-up', 'Mood stabilizer review', 'Sleep check-in'),
(184, 'CHR', 'Hypertension follow-up', 'Home BP review', 'Medication refill'),
(185, 'HYA', 'Annual preventive visit', 'Sports injury follow-up', 'Wellness check'),
(186, 'BH',  'OCD follow-up', 'Sertraline review', 'Behavioral health check-in'),
(187, 'BH',  'Depression follow-up', 'Medication tolerance check', 'Mood check-in'),
(188, 'BH',  'Adjustment disorder follow-up', 'CBT progress review', 'Care coordination'),
(189, 'BH',  'MDD follow-up', 'Bupropion review', 'Mood check-in'),
(190, 'CHR', 'HTN + HLD follow-up', 'Lipid panel review', 'Medication refill'),
(191, 'HYA', 'Preventive visit', 'Smoking cessation counseling', 'Wellness follow-up'),
(192, 'CHR', 'Diabetes follow-up', 'A1c review', 'Medication review'),
(193, 'HYA', 'Well-woman preventive visit', 'Contraception counseling', 'MH screening'),
(194, 'SUD', 'Buprenorphine monthly check-in', 'Recovery counseling', 'MAT refill'),
(195, 'SUD', 'Naltrexone follow-up', 'AUD counseling', 'Medication refill'),
(196, 'CHR', 'HTN + HLD check-in', 'Lab review', 'Medication review'),
(197, 'NEW', 'New patient intake', 'Follow-up visit', 'Lab review'),
(198, 'CHR', 'Diabetes follow-up', 'BP review', 'Medication refill'),
(199, 'HYA', 'Annual preventive visit', 'Sports physical', 'Lifestyle counseling'),
(200, 'GER', 'Geriatric wellness review', 'Polypharmacy follow-up', 'OA pain management'),
(201, 'CHR', 'Hypertension follow-up', 'Lipid panel review', 'Medication refill'),
(202, 'CHR', 'Diabetes follow-up', 'A1c review', 'Medication refill'),
(203, 'HYA', 'Annual preventive visit', 'Smoking cessation counseling', 'Wellness follow-up'),
(204, 'GER', 'Geriatric wellness review', 'Fall risk review', 'Medication reconciliation'),
(205, 'CHR', 'HTN + HLD follow-up', 'Lab review', 'Medication refill'),
(206, 'CHR', 'Diabetes follow-up', 'A1c review', 'Medication review'),
(207, 'BH',  'Behavioral health follow-up', 'SSRI tolerance check', 'Care coordination');

INSERT INTO `openemr_postcalendar_events` (
    `pc_catid`, `pc_multiple`, `pc_aid`, `pc_pid`,
    `pc_title`, `pc_time`, `pc_hometext`,
    `pc_eventDate`, `pc_endDate`,
    `pc_duration`, `pc_recurrtype`, `pc_recurrfreq`,
    `pc_recurrspec`, `pc_location`,
    `pc_startTime`, `pc_endTime`,
    `pc_alldayevent`, `pc_apptstatus`, `pc_eventstatus`,
    `pc_sharing`, `pc_facility`, `pc_billing_location`,
    `pc_informant`, `pc_sendalertsms`, `pc_sendalertemail`,
    `uuid`
)
SELECT
    CASE
        WHEN e.persona = 'BH' THEN @behavioral_catid
        WHEN e.persona = 'HYA' THEN @preventive_catid
        WHEN e.persona = 'NEW' AND visit.seq = 1 THEN @new_patient_catid
        ELSE @established_catid
    END,
    0,
    CAST(pd.providerID AS CHAR),
    CAST(pd.pid AS CHAR),
    CASE
        WHEN e.persona = 'BH' THEN 'Behavioral Assessment'
        WHEN e.persona = 'HYA' THEN 'Preventive Care'
        WHEN e.persona = 'NEW' AND visit.seq = 1 THEN 'New Patient'
        ELSE 'Established Patient'
    END,
    NOW(),
    CASE visit.seq WHEN 1 THEN e.reason1 WHEN 2 THEN e.reason2 ELSE e.reason3 END,
    CASE MOD(e.pid - 172 + ((visit.seq - 1) * 5), 14)
        WHEN 0 THEN @day1 WHEN 1 THEN @day2 WHEN 2 THEN @day3 WHEN 3 THEN @day4
        WHEN 4 THEN @day5 WHEN 5 THEN @day6 WHEN 6 THEN @day7 WHEN 7 THEN @day8
        WHEN 8 THEN @day9 WHEN 9 THEN @day10 WHEN 10 THEN @day11 WHEN 11 THEN @day12
        WHEN 12 THEN @day13 ELSE @day14
    END,
    '0000-00-00',
    CASE WHEN e.persona = 'NEW' AND visit.seq = 1 THEN 2700 ELSE 1800 END,
    0, 0, @recurrspec, @location,
    CASE visit.seq WHEN 1 THEN '08:00:00' WHEN 2 THEN '12:30:00' ELSE '16:00:00' END,
    CASE
        WHEN e.persona = 'NEW' AND visit.seq = 1 THEN '08:45:00'
        WHEN visit.seq = 1 THEN '08:30:00'
        WHEN visit.seq = 2 THEN '13:00:00'
        ELSE '16:30:00'
    END,
    0, '-', 1, 1, 1, 1, 1, 'NO', 'NO',
    UNHEX(REPLACE(UUID(), '-', ''))
  FROM patient_data pd
  JOIN zoomly_panel_expansion_appts e ON e.pid = pd.pid
  JOIN (
        SELECT 1 AS seq UNION ALL SELECT 2 UNION ALL SELECT 3
  ) visit;

-- =============================================================================
-- f) pc_facility + pc_billing_location retarget — every row above was inserted
-- with pc_facility=1 hardcoded. Set it to the provider's home facility so
-- the calendar's facility filter actually scopes correctly. pc_billing_location
-- matches the same facility (visit billing flows through the visit's facility).
-- =============================================================================

UPDATE openemr_postcalendar_events e
JOIN users u ON u.id = CAST(e.pc_aid AS UNSIGNED)
   SET e.pc_facility = u.facility_id,
       e.pc_billing_location = u.facility_id
 WHERE e.pc_pid REGEXP '^[0-9]+$'
   AND CAST(e.pc_pid AS UNSIGNED) BETWEEN 100 AND 207;

-- =============================================================================
-- PATIENT_TRACKER ROWS
--
-- OpenEMR's PHP path (manage_tracker_status) creates the patient_tracker row
-- when an appointment's status changes via the UI. Direct DB inserts of
-- openemr_postcalendar_events skip that, so the Patient Flow Board's
-- Encounter column would read blank for every seeded appointment. Insert a
-- tracker row per event with encounter=0; encounter gets populated later by
-- the past-encounter seeder, the Hydrate Demo Data button's create_encounter
-- path, or by OpenEMR's own UI when status flips to Arrived. Done at the end
-- of 06 so it covers both the initial INSERT block and the second new-patient
-- INSERT block above.
-- =============================================================================
INSERT INTO `patient_tracker`
    (date, apptdate, appttime, eid, pid, original_user, encounter, lastseq, drug_screen_completed)
SELECT NOW(), ev.pc_eventDate, ev.pc_startTime, ev.pc_eid,
       CAST(ev.pc_pid AS UNSIGNED), 'seed', 0, '1', 0
  FROM openemr_postcalendar_events ev
 WHERE ev.pc_pid REGEXP '^[0-9]+$'
   AND CAST(ev.pc_pid AS UNSIGNED) BETWEEN 100 AND 207;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
