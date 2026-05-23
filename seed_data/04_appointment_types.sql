-- =============================================================================
-- 04 — APPOINTMENT TYPES (5 Zoom-prefixed telehealth categories)
-- =============================================================================

-- =============================================================================
-- CUSTOM APPOINTMENT TYPES
-- Only Zoomly-specific types — use OpenEMR built-ins for everything else
-- =============================================================================

-- Legacy suffix-style categories (referenced by the existing appointment
-- INSERT block below). Removed at end of file by the S12-02 retarget step
-- once every appointment has been moved to a Zoom-prefixed category.
INSERT INTO `openemr_postcalendar_categories` (
    `pc_catname`, `pc_catcolor`, `pc_catdesc`,
    `pc_duration`, `pc_cattype`, `pc_active`, `pc_seq`,
    `pc_recurrtype`, `pc_recurrfreq`, `pc_end_date_flag`,
    `pc_end_date_freq`, `pc_end_all_day`, `pc_dailylimit`,
    `aco_spec`, `pc_constant_id`
) VALUES
('Telehealth Zoom', '#b4d0f8', 'Zoom telehealth video appointment — established patient',
 1800, 0, 1, 10, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_telehealth'),
('New Patient Zoom', '#0b5cff', 'New patient intake via Zoom video',
 2700, 0, 1, 20, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'new_patient_zoom');

-- S12-02 Zoom-prefixed telehealth-themed categories
INSERT INTO `openemr_postcalendar_categories` (
    `pc_catname`, `pc_catcolor`, `pc_catdesc`,
    `pc_duration`, `pc_cattype`, `pc_active`, `pc_seq`,
    `pc_recurrtype`, `pc_recurrfreq`, `pc_end_date_flag`,
    `pc_end_date_freq`, `pc_end_all_day`, `pc_dailylimit`,
    `aco_spec`, `pc_constant_id`
) VALUES
('Zoom Behavioral Health', '#7E57C2', 'Psychiatry / behavioral health video visit',
 1800, 0, 1, 30, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_behavioral_health'),
('Zoom Chronic Care',      '#0B5CFF', 'Chronic disease stable follow-up video visit',
 1800, 0, 1, 50, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_chronic_care'),
('Zoom MAT (Suboxone)',    '#43A047', 'Buprenorphine / MAT maintenance video visit',
 1800, 0, 1, 60, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_mat'),
('Zoom New Patient',       '#FB8C00', 'New patient intake via Zoom — any specialty',
 2700, 0, 1, 70, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_new_patient'),
('Zoom Preventive',        '#00ACC1', 'Preventive / wellness video touchpoint',
 1800, 0, 1, 80, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_preventive');

-- =============================================================================
-- CATEGORY ID VARIABLES
-- Custom types: looked up by name after insert
-- OpenEMR built-ins: hardcoded from verified pc_catid values
-- =============================================================================

SET @zoom_telehealth_catid  = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Telehealth Zoom');
SET @new_patient_zoom_catid = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'New Patient Zoom');

SET @zoom_behavioral_health_catid = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom Behavioral Health');
SET @zoom_chronic_care_catid      = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom Chronic Care');
SET @zoom_mat_catid               = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom MAT (Suboxone)');
SET @zoom_new_patient_catid       = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom New Patient');
SET @zoom_preventive_catid        = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom Preventive');
SET @zoom_established_patient_catid = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom Established Patient');

-- OpenEMR built-in category IDs (verified from openemr_postcalendar_categories)
SET @office_visit_catid     = 5;   -- Office Visit (15 min)
SET @established_catid      = 9;   -- Established Patient (15 min)
SET @new_patient_catid      = 10;  -- New Patient (30 min)
SET @behavioral_catid       = 12;  -- Health and Behavioral Assessment (15 min)
SET @preventive_catid       = 13;  -- Preventive Care Services (15 min)
SET @ophthalm_catid         = 14;  -- Ophthalmological Services (15 min)

-- =============================================================================
-- CALENDAR SERIALIZED FIELDS
-- =============================================================================

SET @recurrspec = 'a:6:{s:17:"event_repeat_freq";s:1:"0";s:22:"event_repeat_freq_type";s:1:"0";s:19:"event_repeat_on_num";s:1:"1";s:19:"event_repeat_on_day";s:1:"0";s:20:"event_repeat_on_freq";s:1:"0";s:6:"exdate";s:0:"";}';
SET @location   = 'a:6:{s:14:"event_location";s:0:"";s:13:"event_street1";s:0:"";s:13:"event_street2";s:0:"";s:10:"event_city";s:0:"";s:11:"event_state";s:0:"";s:12:"event_postal";s:0:"";}';

-- =============================================================================
-- NON-ZOOM CATEGORY COLOR REFRESH
--
-- Reset built-in OpenEMR clinical categories to bright, distinct hues so
-- Zoom appointments stand out against them on the calendar. Zoom appointments
-- occupy the blue family (#0b5cff strong + #b4d0f8 soft) — non-Zoom visit
-- rows get oranges, greens, purples, magentas, teals, etc. Scheduling-control
-- rows (No Show, In Office, Out Of Office, Vacation, Holidays, Closed,
-- Lunch, Reserved) stay on their default muted palette so they fade into
-- the background.
-- =============================================================================
UPDATE openemr_postcalendar_categories
SET pc_catcolor = CASE pc_catid
    WHEN 5  THEN '#F97316'  -- Office Visit                     → orange
    WHEN 9  THEN '#22C55E'  -- Established Patient              → green
    WHEN 10 THEN '#EC4899'  -- New Patient                      → magenta
    WHEN 12 THEN '#A855F7'  -- Health and Behavioral Assessment → violet
    WHEN 13 THEN '#14B8A6'  -- Preventive Care Services         → teal
    WHEN 14 THEN '#F43F5E'  -- Ophthalmological Services        → rose
    WHEN 15 THEN '#EAB308'  -- Group Therapy                    → yellow
END
WHERE pc_catid IN (5, 9, 10, 12, 13, 14, 15);


