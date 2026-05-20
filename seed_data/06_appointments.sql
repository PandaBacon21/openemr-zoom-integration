-- =============================================================================
-- 06 — APPOINTMENTS (175 total: 112 original + 63 new)
--
-- Order in file:
--   a) Original 112 appointments across 14 days (DAY 1 ... DAY 14)
--   b) S12-02 retarget UPDATEs (Zoom category remap + pc_title sync)
--   c) S12-20 drop Zoom Cardiology (absorbed into Zoom Chronic Care)
--   d) S12-29 pc_aid retarget UPDATE (point at each patient's new providerID)
--   e) 63 new appointments for PIDs 130-150
-- =============================================================================

-- =============================================================================
-- APPOINTMENTS
--
-- 2 appointments per provider per day × 4 providers × 14 days = 112 total
--
-- Patient assignment strategy:
--   - Each patient's FIRST appointment with a provider = New Patient or New Patient Zoom
--   - Subsequent appointments = Established Patient, Office Visit, or Telehealth Zoom
--   - Mix in Preventive Care, Behavioral, Ophthalmological sparingly for realism
--
-- Provider → specialty → realistic appointment mix:
--   10 (OConnor, Internal Medicine):  Office Visit, Established, Telehealth Zoom, Preventive Care
--   11 (Rodriguez, Family Medicine):  Office Visit, Established, Telehealth Zoom, New Patient Zoom
--   12 (Miller, Psychiatry):          Telehealth Zoom, Established, Behavioral Assessment
--   13 (Thompson, Cardiology):        Office Visit, Established, Telehealth Zoom, New Patient Zoom
--
-- Provider IDs: 10=OConnor, 11=Rodriguez, 12=Miller, 13=Thompson
-- Patient pool: PIDs 100-129, cycling through providers
-- =============================================================================

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
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@office_visit_catid,   0, '10', '104', 'Office Visit',          NOW(), 'Routine follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '10:00:00', '10:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- Rodriguez: pid 101 new patient zoom, then pid 105 established
(@new_patient_zoom_catid, 0, '11', '101', 'New Patient Zoom',    NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '09:00:00', '09:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '11', '105', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- Miller (Psychiatry): pid 103 new patient zoom, then pid 106 telehealth
(@new_patient_zoom_catid, 0, '12', '103', 'New Patient Zoom',    NOW(), 'New psychiatric patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '09:00:00', '09:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '12', '106', 'Telehealth Zoom',     NOW(), 'Psychiatric check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- Thompson (Cardiology): pid 102 new patient, then pid 107 telehealth
(@new_patient_catid,    0, '13', '102', 'New Patient',           NOW(), 'Initial cardiology consult',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '13', '107', 'Telehealth Zoom',     NOW(), 'Cardiac follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 2
-- =============================================================================
(@established_catid,    0, '10', '100', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid,     0, '10', '108', 'Preventive Care',       NOW(), 'Annual wellness screening',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '10:30:00', '10:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '101', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '109', 'New Patient Zoom',    NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@behavioral_catid,     0, '12', '103', 'Behavioral Assessment', NOW(), 'Mental health assessment',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '12', '110', 'Telehealth Zoom',     NOW(), 'Therapy session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '102', 'Established Patient',   NOW(), 'Cardiology follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '13', '111', 'New Patient Zoom',    NOW(), 'New cardiology patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 3
-- =============================================================================
(@zoom_telehealth_catid,  0, '10', '100', 'Telehealth Zoom',     NOW(), 'Medication review via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '10', '112', 'New Patient',           NOW(), 'Initial intake visit',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '11', '105', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '11', '109', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '13:00:00', '13:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '12', '106', 'Telehealth Zoom',     NOW(), 'Psychiatric follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '113', 'New Patient Zoom',    NOW(), 'New psychiatric patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '13', '107', 'Telehealth Zoom',     NOW(), 'Cardiac check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '13', '111', 'Established Patient',   NOW(), 'Cardiology follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 4
-- =============================================================================
(@office_visit_catid,   0, '10', '104', 'Office Visit',          NOW(), 'Routine office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '10', '112', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@office_visit_catid,   0, '11', '101', 'Office Visit',          NOW(), 'Routine office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '114', 'New Patient Zoom',    NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '12', '110', 'Established Patient',   NOW(), 'Therapy follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '12', '113', 'Telehealth Zoom',     NOW(), 'Psychiatric follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@office_visit_catid,   0, '13', '102', 'Office Visit',          NOW(), 'Cardiology office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '13', '115', 'New Patient Zoom',    NOW(), 'New cardiology patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 5
-- =============================================================================
(@preventive_catid,     0, '10', '108', 'Preventive Care',       NOW(), 'Preventive screening follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '10', '100', 'Telehealth Zoom',     NOW(), 'Annual wellness via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '11', '109', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '11', '114', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@behavioral_catid,     0, '12', '106', 'Behavioral Assessment', NOW(), 'Psychiatric behavioral assessment',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '12', '110', 'Telehealth Zoom',     NOW(), 'Therapy session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '13', '115', 'Telehealth Zoom',     NOW(), 'Cardiology follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '13', '111', 'Established Patient',   NOW(), 'Cardiology established visit',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 6
-- =============================================================================
(@office_visit_catid,   0, '10', '112', 'Office Visit',          NOW(), 'Office visit follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '10', '116', 'New Patient',           NOW(), 'Initial intake visit',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@office_visit_catid,   0, '11', '105', 'Office Visit',          NOW(), 'Routine office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '117', 'New Patient Zoom',    NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '12', '113', 'Telehealth Zoom',     NOW(), 'Psychiatric session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '118', 'New Patient Zoom',    NOW(), 'New psychiatric patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '11:00:00', '11:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '13', '107', 'Telehealth Zoom',     NOW(), 'Cardiac monitoring via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '13', '119', 'New Patient',           NOW(), 'Initial cardiology consult',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 7
-- =============================================================================
(@zoom_telehealth_catid,  0, '10', '116', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '10', '104', 'Established Patient',   NOW(), 'Established patient visit',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '117', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '11', '109', 'Telehealth Zoom',     NOW(), 'Telehealth check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '12', '118', 'Telehealth Zoom',     NOW(), 'Psychiatric follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '120', 'New Patient Zoom',    NOW(), 'New psychiatric patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '119', 'Established Patient',   NOW(), 'Cardiology follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '13', '115', 'Telehealth Zoom',     NOW(), 'Cardiac check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 8
-- =============================================================================
(@office_visit_catid,   0, '10', '116', 'Office Visit',          NOW(), 'Office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '10', '120', 'New Patient',           NOW(), 'Initial intake visit',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '11', '117', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '121', 'New Patient Zoom',    NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '12', '120', 'Established Patient',   NOW(), 'Therapy follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '12', '118', 'Telehealth Zoom',     NOW(), 'Psychiatric session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '13', '119', 'Telehealth Zoom',     NOW(), 'Post-procedure follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '13', '122', 'New Patient',           NOW(), 'Initial cardiology consult',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 9
-- =============================================================================
(@zoom_telehealth_catid,  0, '10', '120', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid,     0, '10', '104', 'Preventive Care',       NOW(), 'Annual wellness check',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '121', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '11', '105', 'Telehealth Zoom',     NOW(), 'Telehealth check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '12', '113', 'Telehealth Zoom',     NOW(), 'Psychiatric session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '123', 'New Patient Zoom',    NOW(), 'New psychiatric patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '122', 'Established Patient',   NOW(), 'Cardiology follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '13', '119', 'Telehealth Zoom',     NOW(), 'Cardiac monitoring via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 10
-- =============================================================================
(@established_catid,    0, '10', '112', 'Established Patient',   NOW(), 'Established patient visit',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '10', '116', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@office_visit_catid,   0, '11', '109', 'Office Visit',          NOW(), 'Routine office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '124', 'New Patient Zoom',    NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@behavioral_catid,     0, '12', '120', 'Behavioral Assessment', NOW(), 'Psychiatric behavioral assessment',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '12', '123', 'Telehealth Zoom',     NOW(), 'Psychiatric session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '13', '122', 'Telehealth Zoom',     NOW(), 'Cardiac check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '13', '125', 'New Patient',           NOW(), 'Initial cardiology consult',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 11
-- =============================================================================
(@zoom_telehealth_catid,  0, '10', '120', 'Telehealth Zoom',     NOW(), 'Medication review via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@office_visit_catid,   0, '10', '108', 'Office Visit',          NOW(), 'Office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '124', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '11', '121', 'Telehealth Zoom',     NOW(), 'Telehealth check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '12', '118', 'Telehealth Zoom',     NOW(), 'Psychiatric session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '126', 'New Patient Zoom',    NOW(), 'New psychiatric patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '11:00:00', '11:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '125', 'Established Patient',   NOW(), 'Cardiology follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '13', '122', 'Telehealth Zoom',     NOW(), 'Cardiac monitoring via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 12
-- =============================================================================
(@established_catid,    0, '10', '116', 'Established Patient',   NOW(), 'Established patient visit',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '10', '104', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '11', '124', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '11', '127', 'New Patient Zoom',    NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '11:00:00', '11:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@behavioral_catid,     0, '12', '123', 'Behavioral Assessment', NOW(), 'Psychiatric behavioral assessment',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '12', '126', 'Telehealth Zoom',     NOW(), 'Psychiatric follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '13', '125', 'Telehealth Zoom',     NOW(), 'Cardiac follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '13', '128', 'New Patient',           NOW(), 'Initial cardiology consult',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 13
-- =============================================================================
(@office_visit_catid,   0, '10', '120', 'Office Visit',          NOW(), 'Office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_catid,    0, '10', '124', 'New Patient',           NOW(), 'Initial intake visit',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '11', '127', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '11', '109', 'Telehealth Zoom',     NOW(), 'Telehealth check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '12', '126', 'Telehealth Zoom',     NOW(), 'Psychiatric session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@new_patient_zoom_catid, 0, '12', '129', 'New Patient Zoom',    NOW(), 'New psychiatric patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '11:00:00', '11:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '13', '128', 'Established Patient',   NOW(), 'Cardiology follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '13', '125', 'Telehealth Zoom',     NOW(), 'Cardiac check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 14
-- =============================================================================
(@zoom_telehealth_catid,  0, '10', '124', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@preventive_catid,     0, '10', '116', 'Preventive Care',       NOW(), 'Annual preventive care',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '14:00:00', '14:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '11', '127', 'Telehealth Zoom',     NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '11', '121', 'Established Patient',   NOW(), 'Follow-up visit',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@established_catid,    0, '12', '129', 'Established Patient',   NOW(), 'Therapy follow-up',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_telehealth_catid,  0, '12', '126', 'Telehealth Zoom',     NOW(), 'Psychiatric session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid,  0, '13', '128', 'Telehealth Zoom',     NOW(), 'Cardiac follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@established_catid,    0, '13', '122', 'Established Patient',   NOW(), 'Cardiology established visit',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '14:00:00', '14:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', '')));


-- =============================================================================
-- TELEHEALTH APPOINTMENT CATEGORY PIVOT  (Sprint 12 / S12-02)
--
-- Retarget the 112 appointment rows above from OpenEMR built-in categories
-- (Office Visit, Established Patient, New Patient, Behavioral Assessment,
-- Preventive Care) and the legacy suffix-style custom categories (Telehealth
-- Zoom, New Patient Zoom) onto the 6 Zoom-prefixed telehealth categories.
-- Mapping driven by the S12-01 persona matrix above.
-- =============================================================================

-- 1. Universal: every first-visit appointment → Zoom New Patient
UPDATE openemr_postcalendar_events
   SET pc_catid = @zoom_new_patient_catid
 WHERE pc_aid IN ('10','11','12','13')
   AND pc_catid IN (@new_patient_catid, @new_patient_zoom_catid);

-- 2. Miller (psychiatry) established → Zoom Behavioral Health
UPDATE openemr_postcalendar_events
   SET pc_catid = @zoom_behavioral_health_catid
 WHERE pc_aid = '12'
   AND pc_catid != @zoom_new_patient_catid;

-- 4. BH-PC patients (PCP-managed depression / anxiety) → Zoom Behavioral Health
UPDATE openemr_postcalendar_events
   SET pc_catid = @zoom_behavioral_health_catid
 WHERE pc_pid IN ('101','104','109','129')
   AND pc_catid != @zoom_new_patient_catid;

-- 5. SUD patient (PID 120, buprenorphine maintenance) → Zoom MAT (Suboxone)
UPDATE openemr_postcalendar_events
   SET pc_catid = @zoom_mat_catid
 WHERE pc_pid = '120'
   AND pc_catid != @zoom_new_patient_catid;

-- 6. HYA preventive-touchpoint patients → Zoom Preventive
UPDATE openemr_postcalendar_events
   SET pc_catid = @zoom_preventive_catid
 WHERE pc_pid IN ('121','125','128')
   AND pc_catid != @zoom_new_patient_catid;

-- 7. Catch-all: remaining established appointments → Zoom Chronic Care
--    (CHR, GER, NEW personas — OConnor + Rodriguez chronic disease follow-ups)
UPDATE openemr_postcalendar_events
   SET pc_catid = @zoom_chronic_care_catid
 WHERE pc_aid IN ('10','11','12','13')
   AND pc_catid NOT IN (
       @zoom_new_patient_catid,
       @zoom_behavioral_health_catid,
       @zoom_mat_catid,
       @zoom_preventive_catid
   );

-- Sync pc_title to match the new category so the calendar display matches
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom New Patient'       WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_new_patient_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom Behavioral Health' WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_behavioral_health_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom Chronic Care'      WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_chronic_care_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom MAT (Suboxone)'    WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_mat_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom Preventive'        WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_preventive_catid;

-- Drop the legacy suffix-style custom categories — no appointments reference
-- them anymore and we want only Zoom-prefixed entries in the calendar dropdown.
DELETE FROM openemr_postcalendar_categories
 WHERE pc_catname IN ('Telehealth Zoom', 'New Patient Zoom');


--
-- Step 1: retarget ALL existing 112 appointments so pc_aid matches each
-- patient's new providerID. Single JOIN-based UPDATE.
-- Step 2: add 63 new appointments for PIDs 130-150 (3 per patient over the
-- 14-day window). Each appointment uses the patient's providerID (pc_aid) and
-- persona-appropriate Zoom category (pc_catid).
-- =============================================================================

UPDATE openemr_postcalendar_events e
JOIN patient_data pd ON pd.pid = CAST(e.pc_pid AS UNSIGNED)
   SET e.pc_aid = CAST(pd.providerID AS CHAR)
 WHERE CAST(e.pc_pid AS UNSIGNED) BETWEEN 100 AND 150;

-- New appointments for the 21 new patients (3 each, spread across days 1-14)
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
(@zoom_behavioral_health_catid, 0, '17', '130', 'Zoom Behavioral Health', NOW(), 'OCD med management', DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_behavioral_health_catid, 0, '17', '130', 'Zoom Behavioral Health', NOW(), 'OCD therapy follow-up', DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_behavioral_health_catid, 0, '17', '130', 'Zoom Behavioral Health', NOW(), 'OCD med check', DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 131 Janelle Cho (PSY-S, Priya Patel 15)
(@zoom_behavioral_health_catid, 0, '15', '131', 'Zoom Behavioral Health', NOW(), 'PTSD med management', DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_behavioral_health_catid, 0, '15', '131', 'Zoom Behavioral Health', NOW(), 'PTSD follow-up', DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_behavioral_health_catid, 0, '15', '131', 'Zoom Behavioral Health', NOW(), 'PTSD med check', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 132 Bryan Roberts (SUD AUD, Lucas Johnson 22)
(@zoom_mat_catid, 0, '22', '132', 'Zoom MAT (Suboxone)', NOW(), 'Naltrexone monthly check-in', DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_mat_catid, 0, '22', '132', 'Zoom MAT (Suboxone)', NOW(), 'AUD counseling', DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_mat_catid, 0, '22', '132', 'Zoom MAT (Suboxone)', NOW(), 'Naltrexone refill', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 133 Ashley Cohen (SUD OUD, Lucas Johnson 22)
(@zoom_mat_catid, 0, '22', '133', 'Zoom MAT (Suboxone)', NOW(), 'Suboxone monthly check-in', DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_mat_catid, 0, '22', '133', 'Zoom MAT (Suboxone)', NOW(), 'Suboxone refill', DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_mat_catid, 0, '22', '133', 'Zoom MAT (Suboxone)', NOW(), 'OUD counseling', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 134 Marcus Hill (NEW, Chen 16) — first-visit intake + follow-ups
(@zoom_new_patient_catid, 0, '16', '134', 'Zoom New Patient', NOW(), 'New patient intake', DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location, '13:00:00', '13:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '16', '134', 'Zoom Chronic Care', NOW(), 'Follow-up visit', DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '16', '134', 'Zoom Chronic Care', NOW(), 'Lab review', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 135 Linda Kapoor (CHR, Chen 16)
(@zoom_chronic_care_catid, 0, '16', '135', 'Zoom Chronic Care', NOW(), 'T2DM quarterly check-in', DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '16', '135', 'Zoom Chronic Care', NOW(), 'A1c follow-up', DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '16', '135', 'Zoom Chronic Care', NOW(), 'Med refill check', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 136 Roberto Cruz (CHR, Garcia 19)
(@zoom_chronic_care_catid, 0, '19', '136', 'Zoom Chronic Care', NOW(), 'HTN + HLD check-in', DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '19', '136', 'Zoom Chronic Care', NOW(), 'Quarterly follow-up', DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '19', '136', 'Zoom Chronic Care', NOW(), 'Lipid panel review', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 137 Sasha Yang (HYA, Garcia 19)
(@zoom_preventive_catid, 0, '19', '137', 'Zoom Preventive', NOW(), 'Annual preventive visit', DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '19', '137', 'Zoom Preventive', NOW(), 'MH screening follow-up', DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '19', '137', 'Zoom Preventive', NOW(), 'Contraception consult', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 138 Tyler Murphy (HYA, Amy Martin 21)
(@zoom_preventive_catid, 0, '21', '138', 'Zoom Preventive', NOW(), 'Sports physical', DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '21', '138', 'Zoom Preventive', NOW(), 'Cholesterol screen follow-up', DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '21', '138', 'Zoom Preventive', NOW(), 'Smoking cessation counseling', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 139 Christina Knight (BH-PC, Amy Martin 21)
(@zoom_behavioral_health_catid, 0, '21', '139', 'Zoom Behavioral Health', NOW(), 'Postpartum depression follow-up', DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_behavioral_health_catid, 0, '21', '139', 'Zoom Behavioral Health', NOW(), 'SSRI tolerance check', DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_behavioral_health_catid, 0, '21', '139', 'Zoom Behavioral Health', NOW(), 'GAD med review', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 140 Hannah Kelly (HYA, Amy Martin 21)
(@zoom_preventive_catid, 0, '21', '140', 'Zoom Preventive', NOW(), 'Annual well-woman visit', DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '21', '140', 'Zoom Preventive', NOW(), 'MH screening', DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '21', '140', 'Zoom Preventive', NOW(), 'Contraception counseling', DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 141 Frank Burke (CHR, Lisa Patel 25)
(@zoom_chronic_care_catid, 0, '25', '141', 'Zoom Chronic Care', NOW(), 'HTN + HLD med review', DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '25', '141', 'Zoom Chronic Care', NOW(), 'Quarterly follow-up', DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '25', '141', 'Zoom Chronic Care', NOW(), 'BP check + statin review', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 142 Margaret Sullivan (GER, Lisa Patel 25)
(@zoom_chronic_care_catid, 0, '25', '142', 'Zoom Chronic Care', NOW(), 'Geriatric polypharmacy review', DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '25', '142', 'Zoom Chronic Care', NOW(), 'OA pain management', DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '25', '142', 'Zoom Chronic Care', NOW(), 'Osteoporosis follow-up', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 143 Devon Banks (HYA, Lisa Patel 25)
(@zoom_preventive_catid, 0, '25', '143', 'Zoom Preventive', NOW(), 'Annual preventive visit', DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '25', '143', 'Zoom Preventive', NOW(), 'MH screening', DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '25', '143', 'Zoom Preventive', NOW(), 'Lifestyle counseling', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 144 Mia Davies (BH-PC, Nelson 14)
(@zoom_behavioral_health_catid, 0, '14', '144', 'Zoom Behavioral Health', NOW(), 'GAD med management', DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_behavioral_health_catid, 0, '14', '144', 'Zoom Behavioral Health', NOW(), 'Anxiety follow-up', DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_behavioral_health_catid, 0, '14', '144', 'Zoom Behavioral Health', NOW(), 'SSRI tolerance check', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 145 Jordan Hayes (HYA, Hiroshi Tanaka 26)
(@zoom_preventive_catid, 0, '26', '145', 'Zoom Preventive', NOW(), 'Annual preventive visit', DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '26', '145', 'Zoom Preventive', NOW(), 'Sports physical', DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '26', '145', 'Zoom Preventive', NOW(), 'Injury follow-up', DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 146 Beatrice Reed (GER, Hiroshi Tanaka 26)
(@zoom_chronic_care_catid, 0, '26', '146', 'Zoom Chronic Care', NOW(), 'Geriatric polypharmacy review', DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '26', '146', 'Zoom Chronic Care', NOW(), 'Hypothyroid follow-up', DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '26', '146', 'Zoom Chronic Care', NOW(), 'Memory screen', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 147 Caleb Cole (NEW, Anderson 23)
(@zoom_new_patient_catid, 0, '23', '147', 'Zoom New Patient', NOW(), 'New patient intake', DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location, '13:00:00', '13:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '23', '147', 'Zoom Chronic Care', NOW(), 'Follow-up visit', DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '23', '147', 'Zoom Chronic Care', NOW(), 'Lab review', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 148 Olivia Davis (NEW, Joe Smith 24)
(@zoom_new_patient_catid, 0, '24', '148', 'Zoom New Patient', NOW(), 'New patient intake', DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location, '13:00:00', '13:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '24', '148', 'Zoom Chronic Care', NOW(), 'Follow-up visit', DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '24', '148', 'Zoom Chronic Care', NOW(), 'Lab review', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 149 Marcus Curtis (HYA, Joe Smith 24)
(@zoom_preventive_catid, 0, '24', '149', 'Zoom Preventive', NOW(), 'Annual preventive visit', DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '24', '149', 'Zoom Preventive', NOW(), 'Sports physical', DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_preventive_catid, 0, '24', '149', 'Zoom Preventive', NOW(), 'MH screening', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
-- PID 150 Patricia Diaz (CHR, Joe Smith 24)
(@zoom_chronic_care_catid, 0, '24', '150', 'Zoom Chronic Care', NOW(), 'HTN + HLD bilingual check-in', DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '24', '150', 'Zoom Chronic Care', NOW(), 'T2DM quarterly check-in', DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),
(@zoom_chronic_care_catid, 0, '24', '150', 'Zoom Chronic Care', NOW(), 'Med refill review', DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location, '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', '')));

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
