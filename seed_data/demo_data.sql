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
--   Zoom Behavioral Health, Zoom Cardiology, Zoom Chronic Care,
--   Zoom MAT (Suboxone), Zoom New Patient, Zoom Preventive
--
-- Every appointment row in this seed lives under one of the six categories
-- above. OpenEMR built-in categories (Office Visit, Established Patient,
-- New Patient, etc.) remain in the DB but are no longer referenced. Zoomly's
-- per-account AppointmentTypeFilter can opt in/out of the Zoom set as a
-- group, or by specialty (e.g. a cardiology-focused SE picks only
-- Zoom Cardiology + Zoom New Patient).
--
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- Widen pc_website to accommodate full Zoom start URLs with zak tokens
ALTER TABLE openemr_postcalendar_events MODIFY pc_website VARCHAR(1024);

-- Hide SQL debug modal pop up screen
UPDATE globals SET gl_value = '1' WHERE gl_name = 'sql_string_no_show_screen';

-- Disable provider availability check 
UPDATE globals SET gl_value = '0' WHERE gl_name = 'schedule_limit';

-- =============================================================================
-- FACILITY
-- =============================================================================

UPDATE `facility` SET `inactive` = 1, `name` = 'Default Facility (Unused)' WHERE `id` = 3;

INSERT INTO `facility` (
    `id`, `uuid`, `name`, `phone`,
    `street`, `city`, `state`, `postal_code`, `country_code`,
    `facility_npi`, `color`,
    `service_location`, `billing_location`, `accepts_assignment`,
    `primary_business_entity`, `inactive`
) VALUES (
    1, UNHEX(REPLACE(UUID(), '-', '')),
    'Zoomly Medical Center', '303-555-0100',
    '100 Health Plaza', 'Denver', 'CO', '80201', 'USA',
    '1234567890', '#0b5cff',
    1, 1, 1, 1, 0
);

UPDATE `users` SET `facility_id` = 1 WHERE `id` = 1;

-- =============================================================================
-- PROVIDERS (physicians) — IDs 10-13
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`, `physician_type`, `npi`
) VALUES
(10, UNHEX(REPLACE(UUID(), '-', '')), 'moconnor', '', 1, 1,
 'Michael', 'OConnor', 'Dr.', 'Internal Medicine', 'michael.oconnor@example.org', 'michael.oconnor@example.org',
 1, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567890'),
(11, UNHEX(REPLACE(UUID(), '-', '')), 'erodriguez', '', 1, 1,
 'Elena', 'Rodriguez', 'Dr.', 'Family Medicine', 'elena.rodriguez@example.org', 'elena.rodriguez@example.org',
 1, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567891'),
(12, UNHEX(REPLACE(UUID(), '-', '')), 'amiller', '', 1, 1,
 'Amelia', 'Miller', 'Dr.', 'Psychiatry', 'amelia.miller@example.org', 'amelia.miller@example.org',
 1, 1, 'physician', '2084P0800X', 'standard', 'standard', 'MD', '1234567892'),
(13, UNHEX(REPLACE(UUID(), '-', '')), 'mthompson', '', 1, 1,
 'Marcus', 'Thompson', 'Dr.', 'Cardiology', 'marcus.thompson@example.org', 'marcus.thompson@example.org',
 1, 1, 'physician', '207RC0000X', 'standard', 'standard', 'MD', '1234567893');

-- =============================================================================
-- NURSES — IDs 20-21
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`
) VALUES
(20, UNHEX(REPLACE(UUID(), '-', '')), 'blee', '', 0, 1,
 'Bill', 'Lee', 'RN', 'Nursing', 'bill.lee@example.org', 'bill.lee@example.org',
 1, 0, 'nurse', '163W00000X', 'standard', 'standard'),
(21, UNHEX(REPLACE(UUID(), '-', '')), 'amartin', '', 0, 1,
 'Amy', 'Martin', 'RN', 'Nursing', 'amy.martin@example.org', 'amy.martin@example.org',
 1, 0, 'nurse', '163W00000X', 'standard', 'standard');

-- =============================================================================
-- MEDICAL ASSISTANTS — IDs 30-31
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`
) VALUES
(30, UNHEX(REPLACE(UUID(), '-', '')), 'bwilliams', '', 0, 1,
 'Ben', 'Williams', 'MA', 'Medical Assistant', 'ben.williams@example.org', 'ben.williams@example.org',
 1, 0, 'med_asst', '356AM0700X', 'standard', 'standard'),
(31, UNHEX(REPLACE(UUID(), '-', '')), 'hsong', '', 0, 1,
 'Hana', 'Song', 'MA', 'Medical Assistant', 'hana.song@example.org', 'hana.song@example.org',
 1, 0, 'med_asst', '356AM0700X', 'standard', 'standard');

-- =============================================================================
-- STAFF SECURE PASSWORDS (ZoomDem0!)
-- =============================================================================

INSERT INTO users_secure (id, username, password, last_update_password) VALUES
(10, 'moconnor',   '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(11, 'erodriguez', '$2y$12$w1I6JUkBsl1O9yuo7LSmte0DEGC.4ewzgNISqDRglz9PNPsFDMJ6y', NOW()),
(12, 'amiller',    '$2y$12$HFxqNhdpiD3tXpi7ZebNae7ClwQZ/5IAO9Ll8zBAbxzSrXwnZGXzS', NOW()),
(13, 'mthompson',  '$2y$12$9Bx9nibZUz2LzKaYCphJCeFrEeSfE1tPjaGLXccaDN7QZaqV9kLdS', NOW()),
(20, 'blee',       '$2y$12$4GWtwxpsqqwSYwAE58stXuyHu9wE7YYkQh/mvBb/Jw3tFXPZ9155m', NOW()),
(21, 'amartin',    '$2y$12$LfXdio/YMJ7br6BFTgWd3e9kgMKf173W2dqUzXoBjmIcmPXmrlDnS', NOW()),
(30, 'bwilliams',  '$2y$12$CBV47dDP/2CvTxaO7bER4.XTm0z6zTJSrfKLcz6gOk5ViFJWGTFHi', NOW()),
(31, 'hsong',      '$2y$12$9jMeSDX.LGvUw61ENWAXyenoSGfXrQ4gMS2rI6klVr0kdF5LP6kxK', NOW());

-- =============================================================================
-- ACL
-- =============================================================================

INSERT IGNORE INTO gacl_aro (id, section_value, value, order_value, name, hidden) VALUES
(12, 'users', 'moconnor',   10, 'Michael OConnor',  0),
(13, 'users', 'amiller',    10, 'Amelia Miller',    0),
(14, 'users', 'mthompson',  10, 'Marcus Thompson',  0),
(15, 'users', 'blee',       10, 'Bill Lee',         0),
(16, 'users', 'amartin',    10, 'Amy Martin',       0),
(17, 'users', 'bwilliams',  10, 'Ben Williams',     0),
(18, 'users', 'hsong',      10, 'Hana Song',        0),
(19, 'users', 'erodriguez', 10, 'Elena Rodriguez',  0);

INSERT IGNORE INTO gacl_groups_aro_map (group_id, aro_id) VALUES
(13,12),(13,19),(13,13),(13,14),
(12,15),(12,16),(12,17),(12,18);

INSERT IGNORE INTO groups (name, user) VALUES
('Physicians', 'moconnor'),
('Physicians', 'erodriguez'),
('Physicians', 'amiller'),
('Physicians', 'mthompson'),
('Clinicians', 'blee'),
('Clinicians', 'amartin'),
('Clinicians', 'bwilliams'),
('Clinicians', 'hsong');

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
('Telehealth Zoom', '#00053D', 'Zoom telehealth video appointment — established patient',
 1800, 0, 1, 10, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_telehealth'),
('New Patient Zoom', '#b4d0f8', 'New patient intake via Zoom video',
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
('Zoom Cardiology',        '#E53935', 'Cardiology follow-up video visit',
 1800, 0, 1, 40, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_cardiology'),
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

-- S12-02 Zoom-prefixed telehealth-themed categories
SET @zoom_behavioral_health_catid = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom Behavioral Health');
SET @zoom_cardiology_catid        = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom Cardiology');
SET @zoom_chronic_care_catid      = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom Chronic Care');
SET @zoom_mat_catid               = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom MAT (Suboxone)');
SET @zoom_new_patient_catid       = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom New Patient');
SET @zoom_preventive_catid        = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'Zoom Preventive');

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
-- PATIENTS — PIDs 100-129
-- =============================================================================

INSERT INTO `patient_data` (
    `pid`, `uuid`, `fname`, `lname`, `mname`, `title`,
    `DOB`, `sex`, `status`,
    `street`, `city`, `state`, `postal_code`, `country_code`,
    `phone_cell`, `email`,
    `providerID`, `pubpid`,
    `hipaa_mail`, `hipaa_voice`, `hipaa_notice`, `hipaa_message`,
    `hipaa_allowsms`, `hipaa_allowemail`,
    `language`, `financial`, `date`
) VALUES
(100, UNHEX(REPLACE(UUID(), '-', '')), 'James', 'Harrison', 'A', 'Mr.',
 '1978-03-14', 'Male', 'married', '412 Elm Street', 'Denver', 'CO', '80201', 'USA',
 '303-555-0101', 'james.harrison@example.org', 10, '100', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(101, UNHEX(REPLACE(UUID(), '-', '')), 'Sofia', 'Reyes', 'M', 'Ms.',
 '1990-07-22', 'Female', 'single', '88 Maple Avenue', 'Denver', 'CO', '80202', 'USA',
 '303-555-0102', 'sofia.reyes@example.org', 11, '101', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(102, UNHEX(REPLACE(UUID(), '-', '')), 'David', 'Kim', '', 'Mr.',
 '1965-11-05', 'Male', 'married', '209 Oak Lane', 'Denver', 'CO', '80203', 'USA',
 '303-555-0103', 'david.kim@example.org', 13, '102', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(103, UNHEX(REPLACE(UUID(), '-', '')), 'Rachel', 'Nguyen', 'T', 'Ms.',
 '1985-02-28', 'Female', 'single', '56 Pine Road', 'Denver', 'CO', '80204', 'USA',
 '303-555-0104', 'rachel.nguyen@example.org', 12, '103', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(104, UNHEX(REPLACE(UUID(), '-', '')), 'Carlos', 'Mendez', 'R', 'Mr.',
 '1972-09-17', 'Male', 'married', '731 Cedar Blvd', 'Denver', 'CO', '80205', 'USA',
 '303-555-0105', 'carlos.mendez@example.org', 10, '104', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(105, UNHEX(REPLACE(UUID(), '-', '')), 'Linda', 'Patel', '', 'Mrs.',
 '1958-06-30', 'Female', 'married', '1020 Birch Court', 'Denver', 'CO', '80206', 'USA',
 '303-555-0106', 'linda.patel@example.org', 11, '105', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(106, UNHEX(REPLACE(UUID(), '-', '')), 'Ethan', 'Brooks', 'J', 'Mr.',
 '1995-04-11', 'Male', 'single', '348 Walnut Street', 'Denver', 'CO', '80207', 'USA',
 '303-555-0107', 'ethan.brooks@example.org', 12, '106', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(107, UNHEX(REPLACE(UUID(), '-', '')), 'Maria', 'Chen', 'L', 'Ms.',
 '1982-12-03', 'Female', 'divorced', '675 Spruce Way', 'Denver', 'CO', '80208', 'USA',
 '303-555-0108', 'maria.chen@example.org', 13, '107', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(108, UNHEX(REPLACE(UUID(), '-', '')), 'Thomas', 'Walsh', 'P', 'Mr.',
 '1969-08-19', 'Male', 'married', '512 Hickory Drive', 'Denver', 'CO', '80209', 'USA',
 '303-555-0109', 'thomas.walsh@example.org', 10, '108', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(109, UNHEX(REPLACE(UUID(), '-', '')), 'Aisha', 'Johnson', 'K', 'Ms.',
 '1993-01-25', 'Female', 'single', '890 Willow Lane', 'Denver', 'CO', '80210', 'USA',
 '303-555-0110', 'aisha.johnson@example.org', 11, '109', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(110, UNHEX(REPLACE(UUID(), '-', '')), 'Brian', 'Foster', 'E', 'Mr.',
 '1980-05-12', 'Male', 'married', '23 Aspen Court', 'Denver', 'CO', '80211', 'USA',
 '303-555-0111', 'brian.foster@example.org', 12, '110', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(111, UNHEX(REPLACE(UUID(), '-', '')), 'Yuki', 'Tanaka', '', 'Ms.',
 '1997-08-03', 'Female', 'single', '67 Larimer Street', 'Denver', 'CO', '80212', 'USA',
 '303-555-0112', 'yuki.tanaka@example.org', 13, '111', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(112, UNHEX(REPLACE(UUID(), '-', '')), 'Omar', 'Hassan', 'A', 'Mr.',
 '1975-03-29', 'Male', 'married', '140 Colfax Ave', 'Denver', 'CO', '80213', 'USA',
 '303-555-0113', 'omar.hassan@example.org', 10, '112', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(113, UNHEX(REPLACE(UUID(), '-', '')), 'Patricia', 'Monroe', 'J', 'Mrs.',
 '1962-11-17', 'Female', 'married', '555 Broadway', 'Denver', 'CO', '80214', 'USA',
 '303-555-0114', 'patricia.monroe@example.org', 11, '113', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(114, UNHEX(REPLACE(UUID(), '-', '')), 'Kevin', 'Park', '', 'Mr.',
 '1988-06-22', 'Male', 'single', '789 Speer Blvd', 'Denver', 'CO', '80215', 'USA',
 '303-555-0115', 'kevin.park@example.org', 12, '114', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(115, UNHEX(REPLACE(UUID(), '-', '')), 'Fatima', 'Ali', 'Z', 'Ms.',
 '1991-09-14', 'Female', 'single', '321 Downing Street', 'Denver', 'CO', '80216', 'USA',
 '303-555-0116', 'fatima.ali@example.org', 13, '115', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(116, UNHEX(REPLACE(UUID(), '-', '')), 'Gregory', 'Stone', 'B', 'Mr.',
 '1955-02-08', 'Male', 'widowed', '44 Monaco Pkwy', 'Denver', 'CO', '80217', 'USA',
 '303-555-0117', 'gregory.stone@example.org', 10, '116', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(117, UNHEX(REPLACE(UUID(), '-', '')), 'Nadia', 'Okafor', 'C', 'Ms.',
 '1986-04-30', 'Female', 'single', '888 York Street', 'Denver', 'CO', '80218', 'USA',
 '303-555-0118', 'nadia.okafor@example.org', 11, '117', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(118, UNHEX(REPLACE(UUID(), '-', '')), 'Samuel', 'Wright', 'D', 'Mr.',
 '1970-07-16', 'Male', 'married', '202 Pearl Street', 'Denver', 'CO', '80219', 'USA',
 '303-555-0119', 'samuel.wright@example.org', 12, '118', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(119, UNHEX(REPLACE(UUID(), '-', '')), 'Claire', 'Bennett', 'F', 'Ms.',
 '1994-12-01', 'Female', 'single', '1100 Grant Street', 'Denver', 'CO', '80220', 'USA',
 '303-555-0120', 'claire.bennett@example.org', 13, '119', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(120, UNHEX(REPLACE(UUID(), '-', '')), 'Andre', 'Dubois', '', 'Mr.',
 '1983-10-25', 'Male', 'married', '77 Logan Street', 'Denver', 'CO', '80221', 'USA',
 '303-555-0121', 'andre.dubois@example.org', 10, '120', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(121, UNHEX(REPLACE(UUID(), '-', '')), 'Priya', 'Sharma', 'N', 'Ms.',
 '1992-03-18', 'Female', 'single', '456 Humboldt Street', 'Denver', 'CO', '80222', 'USA',
 '303-555-0122', 'priya.sharma@example.org', 11, '121', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(122, UNHEX(REPLACE(UUID(), '-', '')), 'Robert', 'Castillo', 'M', 'Mr.',
 '1967-08-09', 'Male', 'married', '933 Josephine Street', 'Denver', 'CO', '80223', 'USA',
 '303-555-0123', 'robert.castillo@example.org', 12, '122', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(123, UNHEX(REPLACE(UUID(), '-', '')), 'Hannah', 'Scott', 'R', 'Ms.',
 '1989-05-27', 'Female', 'single', '215 Fillmore Street', 'Denver', 'CO', '80224', 'USA',
 '303-555-0124', 'hannah.scott@example.org', 13, '123', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(124, UNHEX(REPLACE(UUID(), '-', '')), 'Derek', 'Nguyen', 'T', 'Mr.',
 '1976-01-14', 'Male', 'divorced', '678 Gilpin Street', 'Denver', 'CO', '80225', 'USA',
 '303-555-0125', 'derek.nguyen@example.org', 10, '124', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(125, UNHEX(REPLACE(UUID(), '-', '')), 'Isabelle', 'Martin', 'A', 'Ms.',
 '1998-11-03', 'Female', 'single', '342 Clarkson Street', 'Denver', 'CO', '80226', 'USA',
 '303-555-0126', 'isabelle.martin@example.org', 11, '125', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(126, UNHEX(REPLACE(UUID(), '-', '')), 'Jerome', 'Washington', 'L', 'Mr.',
 '1960-06-20', 'Male', 'married', '119 Corona Street', 'Denver', 'CO', '80227', 'USA',
 '303-555-0127', 'jerome.washington@example.org', 12, '126', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(127, UNHEX(REPLACE(UUID(), '-', '')), 'Mei', 'Liu', '', 'Ms.',
 '1987-09-11', 'Female', 'married', '87 Emerson Street', 'Denver', 'CO', '80228', 'USA',
 '303-555-0128', 'mei.liu@example.org', 13, '127', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(128, UNHEX(REPLACE(UUID(), '-', '')), 'Tyler', 'Hughes', 'W', 'Mr.',
 '1996-02-28', 'Male', 'single', '504 Vine Street', 'Denver', 'CO', '80229', 'USA',
 '303-555-0129', 'tyler.hughes@example.org', 10, '128', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(129, UNHEX(REPLACE(UUID(), '-', '')), 'Amara', 'Diallo', 'S', 'Ms.',
 '1984-07-07', 'Female', 'single', '261 Humboldt Street', 'Denver', 'CO', '80230', 'USA',
 '303-555-0130', 'amara.diallo@example.org', 11, '129', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW());

-- =============================================================================
-- PATIENT PORTAL ACCESS
-- =============================================================================

UPDATE globals SET gl_value = '1' WHERE gl_name = 'portal_onsite_two_enable';
UPDATE globals SET gl_value = '0' WHERE gl_name = 'use_email_for_portal_username';
UPDATE globals SET gl_value = 'https://openemr-dev.theloosemoose.us/portal' WHERE gl_name = 'portal_onsite_two_address';

UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'james.harrison' WHERE pid = 100;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'sofia.reyes'    WHERE pid = 101;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'david.kim'      WHERE pid = 102;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'rachel.nguyen'  WHERE pid = 103;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'carlos.mendez'  WHERE pid = 104;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'linda.patel'    WHERE pid = 105;

-- =============================================================================
-- PATIENT PASSWORDS (ZoomDem0!)
-- =============================================================================

INSERT IGNORE INTO patient_access_onsite
    (pid, portal_username, portal_pwd, portal_pwd_status, portal_login_username)
VALUES
    (100, 'james.harrison', '$2y$12$EIpHTZKZfZeol9IvJczpLe5wuan4k.hxDz1laRkBPpOcdOgYkv.wK', 1, 'james.harrison'),
    (101, 'sofia.reyes',    '$2y$12$ijYVMFvrTW915U5a6H9oAe1BaAgDDnkiMxTD1O5luDwnLWaKFWysi', 1, 'sofia.reyes'),
    (102, 'david.kim',      '$2y$12$y0OO0j0eanYZh7tZX61OdOd3Ax.FMF15kgcyiXEuWtdwFS0kA49tm', 1, 'david.kim'),
    (103, 'rachel.nguyen',  '$2y$12$DJHYhWP.Y/pl4OWBRKCOOuEsJwbSuPQ6xWtgjaO3ak0CajnBUdffu', 1, 'rachel.nguyen'),
    (104, 'carlos.mendez',  '$2y$12$x//cQ7uVV1QpGENhd3MQu.o/.EAfV6mVin2n1nj4/uv0YSgFFYSpW', 1, 'carlos.mendez'),
    (105, 'linda.patel',    '$2y$12$8JnLYbEzToMoMYIQ1Lsm8ulVHXye46./se7QyURqhkS2MAswPxrAO', 1, 'linda.patel');

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
-- CLINICAL DATA — PERSONA MATRIX  (Sprint 12 / S12-01)
--
-- Source of truth for how PIDs 100–129 map to clinical personas. Every
-- downstream Sprint 12 seed section (categories, encounters, allergies,
-- problems, medications, prescriptions, vitals, labs, history, immunizations,
-- insurance) consults this matrix to decide what to seed per patient.
--
-- The personas are deliberately telehealth-skewed. Every condition is one a
-- clinician can realistically manage via Zoom — chronic disease follow-up,
-- behavioral health, post-event cardiology, MAT — not acute presentations
-- that need in-person exam or imaging.
--
-- Persona codes (with telehealth use case):
--   PSY-S  Severe Psychiatric         "Monthly med management video visit, 30 min"
--   BH-PC  Behavioral Health in PC    "SSRI refill + side-effect check, 15 min"
--   CHR    Chronic Disease Follow-up  "Quarterly check-in, home BP/glucose review"
--   CV-F   Cardiology Follow-up       "Post-event or anticoag follow-up, no new sx"
--   GER    Geriatric polypharmacy     "Annual wellness video visit w/ caregiver"
--   SUD    Substance Use MAT          "Monthly buprenorphine refill via video"
--   HYA    Healthy young adult        "Contraception / MH screening / smoking cessation"
--   NEW    New patient first visit    Intentionally sparse — "fresh chart" demo target
--
-- Primary provider key (patient_data.providerID):
--   10  OConnor    Internal Medicine
--   11  Rodriguez  Family Medicine
--   12  Miller     Psychiatry
--   13  Thompson   Cardiology
--
-- Specialty → persona alignment:
--   All Miller patients     → PSY-S  (psychiatry practice ≡ psych dx)
--   All Thompson patients   → CV-F   (cardiology practice ≡ cardiac dx)
--   OConnor + Rodriguez     → CHR / BH-PC / GER / HYA / SUD / NEW mix by age + sex
--
-- PID  Age  Sex  Provider     Persona  Headline phenotype + telehealth context
-- ---  ---  ---  -----------  -------  --------------------------------------------
-- 100   48   M   OConnor      CHR      HTN + HLD stable, home BP log review
-- 101   35   F   Rodriguez    BH-PC    Postpartum depression on sertraline
-- 102   60   M   Thompson     CV-F     CAD s/p PCI 2024, on optimal medical therapy
-- 103   41   F   Miller       PSY-S    GAD severe, sertraline monthly mgmt
-- 104   53   M   OConnor      BH-PC    HTN + comorbid MDD on sertraline
-- 105   67   F   Rodriguez    GER      OA + osteoporosis + hypothyroid, caregiver-assist
-- 106   31   M   Miller       PSY-S    Adult ADHD, extended-release stimulant refill
-- 107   43   F   Thompson     CV-F     Post-ablation SVT, stable follow-up
-- 108   56   M   OConnor      CHR      T2DM + HTN + HLD          ← dashboard test pt
-- 109   33   F   Rodriguez    BH-PC    GAD + weight mgmt on escitalopram
-- 110   46   M   Miller       PSY-S    MDD recurrent, bupropion augmentation
-- 111   28   F   Thompson     CV-F     MVP asymptomatic, annual telehealth check
-- 112   51   M   OConnor      CHR      HTN stable
-- 113   63   F   Rodriguez    GER      HTN + HLD + hypothyroid
-- 114   37   M   Miller       PSY-S    Bipolar II, lamotrigine, mood log review
-- 115   34   F   Thompson     CV-F     PSVT post-EP study, follow-up
-- 116   71   M   OConnor      GER      HTN + HLD + BPH + CKD3 polypharmacy
-- 117   40   F   Rodriguez    CHR      Prediabetes + HLD lifestyle counseling
-- 118   55   M   Miller       PSY-S    MDD recurrent + GAD, duloxetine
-- 119   31   F   Thompson     CV-F     Inappropriate sinus tach on metoprolol
-- 120   42   M   OConnor      SUD      Buprenorphine maintenance for OUD — telehealth MAT
-- 121   34   F   Rodriguez    HYA      Contraception consult, MH screening
-- 122   58   M   Miller       PSY-S    MDD + insomnia on mirtazapine
-- 123   36   F   Thompson     CV-F     PVCs low burden, reassurance visit
-- 124   50   M   OConnor      NEW      Sparse — new-patient telehealth intake demo
-- 125   27   F   Rodriguez    HYA      Preventive video visit, smoking cessation
-- 126   65   M   Miller       PSY-S    MDD chronic + insomnia, careful prescriber
-- 127   38   F   Thompson     CV-F     Paroxysmal afib on apixaban + metoprolol
-- 128   30   M   OConnor      HYA      Smoking cessation telehealth touchpoint
-- 129   41   F   Rodriguez    BH-PC    Perimenopausal mood + HTN
--
-- Persona totals: PSY-S=7  CV-F=7  CHR=4  BH-PC=4  GER=3  HYA=3  SUD=1  NEW=1 = 30
-- =============================================================================

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

-- 3. Thompson (cardiology) established → Zoom Cardiology
UPDATE openemr_postcalendar_events
   SET pc_catid = @zoom_cardiology_catid
 WHERE pc_aid = '13'
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
       @zoom_cardiology_catid,
       @zoom_mat_catid,
       @zoom_preventive_catid
   );

-- Sync pc_title to match the new category so the calendar display matches
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom New Patient'       WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_new_patient_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom Behavioral Health' WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_behavioral_health_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom Cardiology'        WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_cardiology_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom Chronic Care'      WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_chronic_care_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom MAT (Suboxone)'    WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_mat_catid;
UPDATE openemr_postcalendar_events SET pc_title = 'Zoom Preventive'        WHERE pc_aid IN ('10','11','12','13') AND pc_catid = @zoom_preventive_catid;

-- Drop the legacy suffix-style custom categories — no appointments reference
-- them anymore and we want only Zoom-prefixed entries in the calendar dropdown.
DELETE FROM openemr_postcalendar_categories
 WHERE pc_catname IN ('Telehealth Zoom', 'New Patient Zoom');

-- =============================================================================
-- INSURANCE COMPANY MASTER DATA  (Sprint 12 / S12-03)
--
-- Fixed-ID payer master records (200–207). Per-patient insurance_data rows in
-- S12-14 FK back to these via the `provider` column. ins_type_code values pull
-- from insurance_type_codes lookup table.
-- =============================================================================

INSERT INTO `insurance_companies` (id, uuid, name, cms_id, ins_type_code, inactive) VALUES
(200, UNHEX(REPLACE(UUID(), '-', '')), 'Aetna',                       '60054', 17, 0),
(201, UNHEX(REPLACE(UUID(), '-', '')), 'BCBS Colorado',               '00060',  6, 0),
(202, UNHEX(REPLACE(UUID(), '-', '')), 'UnitedHealthcare',            '87726', 17, 0),
(203, UNHEX(REPLACE(UUID(), '-', '')), 'Cigna',                       '62308', 17, 0),
(204, UNHEX(REPLACE(UUID(), '-', '')), 'Kaiser Permanente Colorado',  '93079', 19, 0),
(205, UNHEX(REPLACE(UUID(), '-', '')), 'Medicare',                    '00580',  2, 0),
(206, UNHEX(REPLACE(UUID(), '-', '')), 'Medicaid Colorado',           '00781',  3, 0),
(207, UNHEX(REPLACE(UUID(), '-', '')), 'Tricare',                     '99726',  5, 0);

INSERT INTO `addresses` (id, line1, city, state, zip, country, foreign_id) VALUES
(200, '151 Farmington Avenue',  'Hartford',     'CT', '06156', 'USA', 200),
(201, '700 Broadway',           'Denver',       'CO', '80273', 'USA', 201),
(202, '9700 Health Care Lane',  'Minnetonka',   'MN', '55343', 'USA', 202),
(203, '900 Cottage Grove Rd',   'Bloomfield',   'CT', '06002', 'USA', 203),
(204, '10350 E Dakota Ave',     'Denver',       'CO', '80231', 'USA', 204),
(205, '7500 Security Blvd',     'Baltimore',    'MD', '21244', 'USA', 205),
(206, '303 E 17th Avenue',      'Denver',       'CO', '80203', 'USA', 206),
(207, '16401 East Centretech',  'Aurora',       'CO', '80011', 'USA', 207);

-- =============================================================================
-- PATIENT DEMOGRAPHIC ENRICHMENT  (Sprint 12 / S12-04)
--
-- Fill race / ethnicity / occupation / emergency contact on PIDs 100–129 so
-- the OpenEMR Demographics panel displays real data instead of blanks.
-- Race + ethnicity use OpenEMR's list_options option_id values (race, ethnicity).
-- Occupations chosen to lean telehealth-friendly (knowledge workers, parents,
-- retirees, remote-flexible roles). Emergency contact relationship varies by
-- the patient's existing marital status; phone_contact uses a synthetic
-- 303-555-02xx range to keep them visually distinct from the 303-555-01xx
-- primary cell numbers in the original seed.
-- =============================================================================

UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Software Engineer',     contact_relationship='Spouse',  phone_contact='303-555-0201' WHERE pid=100;
UPDATE patient_data SET race='white',              ethnicity='hisp_or_latin',     occupation='Marketing Manager',     contact_relationship='Parent',  phone_contact='303-555-0202' WHERE pid=101;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Retired Accountant',    contact_relationship='Spouse',  phone_contact='303-555-0203' WHERE pid=102;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Attorney',              contact_relationship='Sibling', phone_contact='303-555-0204' WHERE pid=103;
UPDATE patient_data SET race='white',              ethnicity='hisp_or_latin',     occupation='Construction Manager',  contact_relationship='Spouse',  phone_contact='303-555-0205' WHERE pid=104;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Retired Teacher',       contact_relationship='Spouse',  phone_contact='303-555-0206' WHERE pid=105;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Graphic Designer',      contact_relationship='Parent',  phone_contact='303-555-0207' WHERE pid=106;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Restaurant Owner',      contact_relationship='Sibling', phone_contact='303-555-0208' WHERE pid=107;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Sales Director',        contact_relationship='Spouse',  phone_contact='303-555-0209' WHERE pid=108;
UPDATE patient_data SET race='black_or_afri_amer', ethnicity='not_hisp_or_latin', occupation='Registered Nurse',      contact_relationship='Parent',  phone_contact='303-555-0210' WHERE pid=109;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Architect',             contact_relationship='Spouse',  phone_contact='303-555-0211' WHERE pid=110;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Software Developer',    contact_relationship='Parent',  phone_contact='303-555-0212' WHERE pid=111;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Restaurant Manager',    contact_relationship='Spouse',  phone_contact='303-555-0213' WHERE pid=112;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Retired Librarian',     contact_relationship='Spouse',  phone_contact='303-555-0214' WHERE pid=113;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Product Manager',       contact_relationship='Parent',  phone_contact='303-555-0215' WHERE pid=114;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Pharmacist',            contact_relationship='Sibling', phone_contact='303-555-0216' WHERE pid=115;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Retired Engineer',      contact_relationship='Child',   phone_contact='303-555-0217' WHERE pid=116;
UPDATE patient_data SET race='black_or_afri_amer', ethnicity='not_hisp_or_latin', occupation='University Professor',  contact_relationship='Sibling', phone_contact='303-555-0218' WHERE pid=117;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Insurance Agent',       contact_relationship='Spouse',  phone_contact='303-555-0219' WHERE pid=118;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Veterinarian',          contact_relationship='Parent',  phone_contact='303-555-0220' WHERE pid=119;
UPDATE patient_data SET race='black_or_afri_amer', ethnicity='not_hisp_or_latin', occupation='Auto Mechanic',         contact_relationship='Spouse',  phone_contact='303-555-0221' WHERE pid=120;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Data Scientist',        contact_relationship='Sibling', phone_contact='303-555-0222' WHERE pid=121;
UPDATE patient_data SET race='white',              ethnicity='hisp_or_latin',     occupation='Real Estate Agent',     contact_relationship='Spouse',  phone_contact='303-555-0223' WHERE pid=122;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Physical Therapist',    contact_relationship='Sibling', phone_contact='303-555-0224' WHERE pid=123;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Restaurant Owner',      contact_relationship='Sibling', phone_contact='303-555-0225' WHERE pid=124;
UPDATE patient_data SET race='white',              ethnicity='hisp_or_latin',     occupation='Graduate Student',      contact_relationship='Parent',  phone_contact='303-555-0226' WHERE pid=125;
UPDATE patient_data SET race='black_or_afri_amer', ethnicity='not_hisp_or_latin', occupation='Retired Postal Worker', contact_relationship='Spouse',  phone_contact='303-555-0227' WHERE pid=126;
UPDATE patient_data SET race='Asian',              ethnicity='not_hisp_or_latin', occupation='Financial Analyst',     contact_relationship='Spouse',  phone_contact='303-555-0228' WHERE pid=127;
UPDATE patient_data SET race='white',              ethnicity='not_hisp_or_latin', occupation='Personal Trainer',      contact_relationship='Parent',  phone_contact='303-555-0229' WHERE pid=128;
UPDATE patient_data SET race='black_or_afri_amer', ethnicity='not_hisp_or_latin', occupation='Marketing Director',    contact_relationship='Sibling', phone_contact='303-555-0230' WHERE pid=129;

-- =============================================================================
-- HISTORICAL TELEHEALTH ENCOUNTER SCAFFOLD  (Sprint 12 / S12-05)
--
-- One past telehealth encounter per patient (encounter numbers 30001–30029,
-- dated 30–59 days ago), serving as the anchor encounter for the vitals
-- (S12-10) and lab results (S12-11) seeded later. Encounter pc_catid matches
-- the patient's persona category from S12-02 so the chart's prior visit
-- appears under the correct telehealth specialty. pos_code=10 (CMS Place of
-- Service: Telehealth Provided in Patient's Home) marks every encounter as a
-- video visit.
--
-- PID 124 (NEW persona) is intentionally excluded — the demo wants his chart
-- to look fresh, with no historical encounter, vitals, labs, problems, or
-- meds. He still has scheduled future appointments per the original seed.
-- =============================================================================

INSERT INTO `form_encounter`
    (encounter, uuid, date, pid, provider_id, pc_catid, facility_id, reason,
     pos_code, class_code, encounter_type_code, encounter_type_description)
VALUES
(30001, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 30 DAY), 100, 10, @zoom_chronic_care_catid,      1, 'Quarterly chronic care check-in — HTN, HLD',          10, 'AMB', 'VR', 'virtual'),
(30002, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 31 DAY), 101, 11, @zoom_behavioral_health_catid, 1, 'Postpartum depression follow-up — sertraline check',  10, 'AMB', 'VR', 'virtual'),
(30003, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 32 DAY), 102, 13, @zoom_cardiology_catid,        1, 'Cardiology follow-up — post-PCI med review',          10, 'AMB', 'VR', 'virtual'),
(30004, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 33 DAY), 103, 12, @zoom_behavioral_health_catid, 1, 'Psychiatric med management — GAD',                    10, 'AMB', 'VR', 'virtual'),
(30005, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 34 DAY), 104, 10, @zoom_behavioral_health_catid, 1, 'Depression follow-up — sertraline refill',            10, 'AMB', 'VR', 'virtual'),
(30006, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 35 DAY), 105, 11, @zoom_chronic_care_catid,      1, 'Geriatric wellness video visit',                      10, 'AMB', 'VR', 'virtual'),
(30007, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 36 DAY), 106, 12, @zoom_behavioral_health_catid, 1, 'Adult ADHD med management — methylphenidate ER',      10, 'AMB', 'VR', 'virtual'),
(30008, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 37 DAY), 107, 13, @zoom_cardiology_catid,        1, 'Post-ablation follow-up — SVT',                       10, 'AMB', 'VR', 'virtual'),
(30009, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 38 DAY), 108, 10, @zoom_chronic_care_catid,      1, 'Quarterly chronic care check-in — T2DM, HTN, HLD',    10, 'AMB', 'VR', 'virtual'),
(30010, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 39 DAY), 109, 11, @zoom_behavioral_health_catid, 1, 'GAD follow-up — escitalopram tolerance',              10, 'AMB', 'VR', 'virtual'),
(30011, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 40 DAY), 110, 12, @zoom_behavioral_health_catid, 1, 'MDD med management — bupropion augmentation',         10, 'AMB', 'VR', 'virtual'),
(30012, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 41 DAY), 111, 13, @zoom_cardiology_catid,        1, 'Annual cardiology check-in — MVP',                    10, 'AMB', 'VR', 'virtual'),
(30013, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 42 DAY), 112, 10, @zoom_chronic_care_catid,      1, 'HTN follow-up',                                       10, 'AMB', 'VR', 'virtual'),
(30014, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 43 DAY), 113, 11, @zoom_chronic_care_catid,      1, 'Geriatric wellness video visit',                      10, 'AMB', 'VR', 'virtual'),
(30015, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 44 DAY), 114, 12, @zoom_behavioral_health_catid, 1, 'Bipolar II med management — lamotrigine mood log',    10, 'AMB', 'VR', 'virtual'),
(30016, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 45 DAY), 115, 13, @zoom_cardiology_catid,        1, 'Post-EP study follow-up — PSVT',                      10, 'AMB', 'VR', 'virtual'),
(30017, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 46 DAY), 116, 10, @zoom_chronic_care_catid,      1, 'Geriatric polypharmacy review',                       10, 'AMB', 'VR', 'virtual'),
(30018, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 47 DAY), 117, 11, @zoom_chronic_care_catid,      1, 'Prediabetes + HLD lifestyle counseling',              10, 'AMB', 'VR', 'virtual'),
(30019, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 48 DAY), 118, 12, @zoom_behavioral_health_catid, 1, 'MDD/GAD med management — duloxetine',                 10, 'AMB', 'VR', 'virtual'),
(30020, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 49 DAY), 119, 13, @zoom_cardiology_catid,        1, 'Inappropriate sinus tachycardia follow-up',           10, 'AMB', 'VR', 'virtual'),
(30021, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 50 DAY), 120, 10, @zoom_mat_catid,               1, 'Buprenorphine maintenance — monthly check-in',        10, 'AMB', 'VR', 'virtual'),
(30022, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 51 DAY), 121, 11, @zoom_preventive_catid,        1, 'Contraception consult + annual MH screening',         10, 'AMB', 'VR', 'virtual'),
(30023, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 52 DAY), 122, 12, @zoom_behavioral_health_catid, 1, 'MDD + insomnia med management — mirtazapine',         10, 'AMB', 'VR', 'virtual'),
(30024, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 53 DAY), 123, 13, @zoom_cardiology_catid,        1, 'PVC follow-up — reassurance visit',                   10, 'AMB', 'VR', 'virtual'),
-- PID 124 (NEW persona) intentionally skipped — sparse fresh-chart demo target
(30025, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 55 DAY), 125, 11, @zoom_preventive_catid,        1, 'Preventive video visit — smoking cessation',          10, 'AMB', 'VR', 'virtual'),
(30026, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 56 DAY), 126, 12, @zoom_behavioral_health_catid, 1, 'MDD chronic + insomnia — med management',             10, 'AMB', 'VR', 'virtual'),
(30027, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 57 DAY), 127, 13, @zoom_cardiology_catid,        1, 'Paroxysmal afib follow-up — anticoag review',         10, 'AMB', 'VR', 'virtual'),
(30028, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 58 DAY), 128, 10, @zoom_preventive_catid,        1, 'Annual preventive video visit',                       10, 'AMB', 'VR', 'virtual'),
(30029, UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 59 DAY), 129, 11, @zoom_behavioral_health_catid, 1, 'Perimenopausal mood + HTN follow-up',                 10, 'AMB', 'VR', 'virtual');

-- Forms registry row per encounter so it shows up in Visit History tab
INSERT INTO `forms`
    (date, encounter, form_name, form_id, pid, user, groupname, authorized, deleted, formdir, provider_id)
SELECT fe.date, fe.encounter, 'New Patient Encounter', fe.id, fe.pid,
       u.username, 'Default', 1, 0, 'newpatient', fe.provider_id
  FROM form_encounter fe
  JOIN users u ON u.id = fe.provider_id
 WHERE fe.encounter BETWEEN 30001 AND 30029;

-- Bump sequences past our hardcoded encounter numbers so future
-- create_encounter() calls don't collide.
UPDATE sequences SET id = GREATEST(id, 30029);

-- =============================================================================
-- ALLERGIES  (Sprint 12 / S12-06)
--
-- 27 allergy rows across 20 patients. 9 patients have NKDA (no rows). PID 124
-- (NEW persona) intentionally skipped — sparse fresh-chart demo target.
-- `reaction` uses OpenEMR's reaction list_options vocabulary (hives / nausea /
-- shortness_of_breath / unassigned); `severity_al` uses severity_ccda
-- (mild / moderate / severe). `user` set to the patient's PCP username so
-- the chart attribution is coherent.
-- =============================================================================

INSERT INTO `lists`
    (uuid, type, subtype, title, pid, date, begdate, activity, user, severity_al, reaction)
VALUES
-- PID 100 James Harrison (CHR M48)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Penicillin',  100, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR),  1, 'moconnor',   'moderate', 'hives'),
-- PID 102 David Kim (CV-F M60)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Aspirin',     102, NOW(), DATE_SUB(NOW(), INTERVAL 12 YEAR), 1, 'mthompson',  'mild',     'nausea'),
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Sulfa drugs', 102, NOW(), DATE_SUB(NOW(), INTERVAL 20 YEAR), 1, 'mthompson',  'moderate', 'hives'),
-- PID 103 Rachel Nguyen (PSY-S F41)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'environmental', 'Latex',    103, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR),  1, 'amiller',    'moderate', 'hives'),
-- PID 105 Linda Patel (GER F67)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Penicillin',  105, NOW(), DATE_SUB(NOW(), INTERVAL 30 YEAR), 1, 'erodriguez', 'mild',     'hives'),
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Codeine',     105, NOW(), DATE_SUB(NOW(), INTERVAL 15 YEAR), 1, 'erodriguez', 'mild',     'nausea'),
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Iodine contrast', 105, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'erodriguez', 'moderate', 'hives'),
-- PID 106 Ethan Brooks (PSY-S M31)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'food', 'Peanuts',           106, NOW(), DATE_SUB(NOW(), INTERVAL 25 YEAR), 1, 'amiller',    'severe',   'shortness_of_breath'),
-- PID 107 Maria Chen (CV-F F43)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'food', 'Shellfish',         107, NOW(), DATE_SUB(NOW(), INTERVAL 18 YEAR), 1, 'mthompson',  'moderate', 'hives'),
-- PID 108 Thomas Walsh (CHR M56) ← dashboard test pt
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Penicillin',  108, NOW(), DATE_SUB(NOW(), INTERVAL 20 YEAR), 1, 'moconnor',   'moderate', 'hives'),
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Sulfa drugs', 108, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'moconnor',   'moderate', 'hives'),
-- PID 110 Brian Foster (PSY-S M46)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'NSAIDs',      110, NOW(), DATE_SUB(NOW(), INTERVAL 7 YEAR),  1, 'amiller',    'mild',     'nausea'),
-- PID 112 Omar Hassan (CHR M51)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Penicillin',  112, NOW(), DATE_SUB(NOW(), INTERVAL 15 YEAR), 1, 'moconnor',   'mild',     'hives'),
-- PID 113 Patricia Monroe (GER F63)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Sulfa drugs', 113, NOW(), DATE_SUB(NOW(), INTERVAL 25 YEAR), 1, 'erodriguez', 'severe',   'hives'),
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'NSAIDs',      113, NOW(), DATE_SUB(NOW(), INTERVAL 6 YEAR),  1, 'erodriguez', 'severe',   'nausea'),
-- PID 115 Fatima Ali (CV-F F34)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'environmental', 'Latex',    115, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR),  1, 'mthompson',  'moderate', 'hives'),
-- PID 116 Gregory Stone (GER M71)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Penicillin',  116, NOW(), DATE_SUB(NOW(), INTERVAL 40 YEAR), 1, 'moconnor',   'mild',     'hives'),
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Codeine',     116, NOW(), DATE_SUB(NOW(), INTERVAL 22 YEAR), 1, 'moconnor',   'mild',     'nausea'),
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Lisinopril (ACE-induced cough)', 116, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR), 1, 'moconnor', 'moderate', 'unassigned'),
-- PID 117 Nadia Okafor (CHR F40)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'food', 'Tree nuts',         117, NOW(), DATE_SUB(NOW(), INTERVAL 20 YEAR), 1, 'erodriguez', 'severe',   'shortness_of_breath'),
-- PID 118 Samuel Wright (PSY-S M55)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Penicillin',  118, NOW(), DATE_SUB(NOW(), INTERVAL 12 YEAR), 1, 'amiller',    'moderate', 'hives'),
-- PID 121 Priya Sharma (HYA F34)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Penicillin',  121, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'erodriguez', 'mild',     'hives'),
-- PID 122 Robert Castillo (PSY-S M58)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Sulfa drugs', 122, NOW(), DATE_SUB(NOW(), INTERVAL 18 YEAR), 1, 'amiller',    'moderate', 'hives'),
-- PID 125 Isabelle Martin (HYA F27)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'environmental', 'Latex',    125, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR),  1, 'erodriguez', 'mild',     'hives'),
-- PID 126 Jerome Washington (PSY-S M65)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Penicillin',  126, NOW(), DATE_SUB(NOW(), INTERVAL 35 YEAR), 1, 'amiller',    'mild',     'hives'),
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'Sulfa drugs', 126, NOW(), DATE_SUB(NOW(), INTERVAL 28 YEAR), 1, 'amiller',    'moderate', 'hives'),
-- PID 127 Mei Liu (CV-F F38)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'food', 'Shellfish',         127, NOW(), DATE_SUB(NOW(), INTERVAL 14 YEAR), 1, 'mthompson',  'moderate', 'hives'),
-- PID 129 Amara Diallo (BH-PC F41)
(UNHEX(REPLACE(UUID(),'-','')), 'allergy', 'medication', 'NSAIDs',      129, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR),  1, 'erodriguez', 'mild',     'nausea');

-- =============================================================================
-- MEDICAL PROBLEMS  (Sprint 12 / S12-07)
--
-- ~58 problem rows across 25 patients, ICD-10 coded per OpenEMR convention
-- (`ICD10:CODE` in the `diagnosis` column). HYA persona patients (121, 125,
-- 128) intentionally have no chronic problems — preventive-only chart. PID
-- 124 (NEW) skipped. Diagnoses chosen to align with each persona's medication
-- regimen seeded in S12-08.
-- =============================================================================

INSERT INTO `lists`
    (uuid, type, subtype, title, diagnosis, pid, date, begdate, activity, user, outcome)
VALUES
-- PID 100 James Harrison (CHR M48)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    100, NOW(), DATE_SUB(NOW(), INTERVAL 6 YEAR),  1, 'moconnor',   0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Hyperlipidemia',                'ICD10:E78.5',  100, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR),  1, 'moconnor',   0),
-- PID 101 Sofia Reyes (BH-PC F35)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Major depressive disorder, recurrent, mild', 'ICD10:F33.0', 101, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Generalized anxiety disorder',  'ICD10:F41.1',  101, NOW(), DATE_SUB(NOW(), INTERVAL 1 YEAR),  1, 'erodriguez', 0),
-- PID 102 David Kim (CV-F M60)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Coronary artery disease',       'ICD10:I25.10', 102, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR),  1, 'mthompson',  0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Old myocardial infarction',     'ICD10:I25.2',  102, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR),  1, 'mthompson',  0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    102, NOW(), DATE_SUB(NOW(), INTERVAL 12 YEAR), 1, 'mthompson',  0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Hyperlipidemia',                'ICD10:E78.5',  102, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'mthompson',  0),
-- PID 103 Rachel Nguyen (PSY-S F41)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Generalized anxiety disorder',  'ICD10:F41.1',  103, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR),  1, 'amiller',    0),
-- PID 104 Carlos Mendez (BH-PC M53)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    104, NOW(), DATE_SUB(NOW(), INTERVAL 7 YEAR),  1, 'moconnor',   0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Major depressive disorder, recurrent, moderate', 'ICD10:F33.1', 104, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR), 1, 'moconnor', 0),
-- PID 105 Linda Patel (GER F67)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Osteoarthritis',                'ICD10:M19.90', 105, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Age-related osteoporosis',      'ICD10:M81.0',  105, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR),  1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Hypothyroidism',                'ICD10:E03.9',  105, NOW(), DATE_SUB(NOW(), INTERVAL 12 YEAR), 1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    105, NOW(), DATE_SUB(NOW(), INTERVAL 15 YEAR), 1, 'erodriguez', 0),
-- PID 106 Ethan Brooks (PSY-S M31)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Adult ADHD, inattentive type',  'ICD10:F90.0',  106, NOW(), DATE_SUB(NOW(), INTERVAL 6 YEAR),  1, 'amiller',    0),
-- PID 107 Maria Chen (CV-F F43)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Supraventricular tachycardia',  'ICD10:I47.1',  107, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR),  1, 'mthompson',  0),
-- PID 108 Thomas Walsh (CHR M56) ← dashboard test pt
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Type 2 diabetes mellitus',      'ICD10:E11.9',  108, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR),  1, 'moconnor',   0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    108, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR),  1, 'moconnor',   0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Hyperlipidemia',                'ICD10:E78.5',  108, NOW(), DATE_SUB(NOW(), INTERVAL 7 YEAR),  1, 'moconnor',   0),
-- PID 109 Aisha Johnson (BH-PC F33)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Generalized anxiety disorder',  'ICD10:F41.1',  109, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR),  1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Obesity',                       'ICD10:E66.9',  109, NOW(), DATE_SUB(NOW(), INTERVAL 6 YEAR),  1, 'erodriguez', 0),
-- PID 110 Brian Foster (PSY-S M46)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Major depressive disorder, recurrent, moderate', 'ICD10:F33.1', 110, NOW(), DATE_SUB(NOW(), INTERVAL 7 YEAR), 1, 'amiller', 0),
-- PID 111 Yuki Tanaka (CV-F F28)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Mitral valve prolapse',         'ICD10:I34.1',  111, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR),  1, 'mthompson',  0),
-- PID 112 Omar Hassan (CHR M51)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    112, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR),  1, 'moconnor',   0),
-- PID 113 Patricia Monroe (GER F63)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    113, NOW(), DATE_SUB(NOW(), INTERVAL 14 YEAR), 1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Hyperlipidemia',                'ICD10:E78.5',  113, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Hypothyroidism',                'ICD10:E03.9',  113, NOW(), DATE_SUB(NOW(), INTERVAL 9 YEAR),  1, 'erodriguez', 0),
-- PID 114 Kevin Park (PSY-S M37)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Bipolar II disorder',           'ICD10:F31.81', 114, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'amiller',    0),
-- PID 115 Fatima Ali (CV-F F34)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Paroxysmal supraventricular tachycardia', 'ICD10:I47.1', 115, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'mthompson', 0),
-- PID 116 Gregory Stone (GER M71)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    116, NOW(), DATE_SUB(NOW(), INTERVAL 20 YEAR), 1, 'moconnor',   0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Hyperlipidemia',                'ICD10:E78.5',  116, NOW(), DATE_SUB(NOW(), INTERVAL 15 YEAR), 1, 'moconnor',   0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Benign prostatic hyperplasia',  'ICD10:N40.0',  116, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR),  1, 'moconnor',   0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Chronic kidney disease, stage 3', 'ICD10:N18.3', 116, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR), 1, 'moconnor',   0),
-- PID 117 Nadia Okafor (CHR F40)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Prediabetes',                   'ICD10:R73.03', 117, NOW(), DATE_SUB(NOW(), INTERVAL 1 YEAR),  1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Hyperlipidemia',                'ICD10:E78.5',  117, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR),  1, 'erodriguez', 0),
-- PID 118 Samuel Wright (PSY-S M55)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Major depressive disorder, recurrent, moderate', 'ICD10:F33.1', 118, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR), 1, 'amiller', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Generalized anxiety disorder',  'ICD10:F41.1',  118, NOW(), DATE_SUB(NOW(), INTERVAL 6 YEAR),  1, 'amiller',    0),
-- PID 119 Claire Bennett (CV-F F31)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Inappropriate sinus tachycardia', 'ICD10:R00.0', 119, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'mthompson', 0),
-- PID 120 Andre Dubois (SUD M42)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Opioid dependence, in remission', 'ICD10:F11.21', 120, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR), 1, 'moconnor', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Long-term opiate analgesic management', 'ICD10:Z79.891', 120, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR), 1, 'moconnor', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Post-traumatic stress disorder', 'ICD10:F43.10', 120, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR), 1, 'moconnor',   0),
-- PID 122 Robert Castillo (PSY-S M58)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Major depressive disorder, recurrent, moderate', 'ICD10:F33.1', 122, NOW(), DATE_SUB(NOW(), INTERVAL 12 YEAR), 1, 'amiller', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Generalized anxiety disorder',  'ICD10:F41.1',  122, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'amiller',    0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Insomnia',                      'ICD10:G47.00', 122, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR),  1, 'amiller',    0),
-- PID 123 Hannah Scott (CV-F F36)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Premature ventricular complexes', 'ICD10:I49.3', 123, NOW(), DATE_SUB(NOW(), INTERVAL 1 YEAR), 1, 'mthompson', 0),
-- PID 126 Jerome Washington (PSY-S M65)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Major depressive disorder, recurrent, in full remission', 'ICD10:F33.42', 126, NOW(), DATE_SUB(NOW(), INTERVAL 15 YEAR), 1, 'amiller', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Primary insomnia',              'ICD10:F51.01', 126, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR),  1, 'amiller',    0),
-- PID 127 Mei Liu (CV-F F38)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Paroxysmal atrial fibrillation', 'ICD10:I48.0', 127, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'mthompson',  0),
-- PID 129 Amara Diallo (BH-PC F41)
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Major depressive disorder, single episode, moderate', 'ICD10:F32.1', 129, NOW(), DATE_SUB(NOW(), INTERVAL 1 YEAR), 1, 'erodriguez', 0),
(UNHEX(REPLACE(UUID(),'-','')), 'medical_problem', '', 'Essential hypertension',        'ICD10:I10',    129, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR),  1, 'erodriguez', 0);

-- =============================================================================
-- MEDICATIONS  (Sprint 12 / S12-08)
--
-- 49 medication rows across 22 patients. Real generic names with real RxNorm
-- CUIs in `rxnorm_drugcode` so the medications panel looks structured. HYA
-- persona patients (121/125/128) and select asymptomatic CV-F patients
-- (111/115/123) have no chronic meds. PID 124 (NEW) skipped.
--
-- Each lists row gets a companion lists_medication sidecar row via the
-- JOIN-based INSERT after this block — outpatient / order defaults.
-- =============================================================================

INSERT INTO `lists`
    (uuid, type, subtype, title, pid, date, begdate, activity, user, comments)
VALUES
-- PID 100 James Harrison (CHR HTN+HLD)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lisinopril 10mg tab',           100, NOW(), DATE_SUB(NOW(), INTERVAL 6 YEAR), 1, 'moconnor',   'rxnorm:314076 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Atorvastatin 20mg tab',         100, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR), 1, 'moconnor',   'rxnorm:617314 — 1 tab PO at bedtime'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Aspirin 81mg tab',              100, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR), 1, 'moconnor',   'rxnorm:243670 — 1 tab PO daily'),
-- PID 101 Sofia Reyes (BH-PC MDD+GAD)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Sertraline 50mg tab',           101, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'erodriguez', 'rxnorm:313989 — 1 tab PO daily'),
-- PID 102 David Kim (CV-F CAD+OldMI+HTN+HLD)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Aspirin 81mg tab',              102, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'mthompson',  'rxnorm:243670 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Atorvastatin 80mg tab',         102, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'mthompson',  'rxnorm:617318 — 1 tab PO at bedtime (high-intensity post-MI)'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Metoprolol succinate ER 50mg',  102, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'mthompson',  'rxnorm:866412 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lisinopril 20mg tab',           102, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'mthompson',  'rxnorm:314077 — 1 tab PO daily'),
-- PID 103 Rachel Nguyen (PSY-S GAD severe)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Sertraline 100mg tab',          103, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR), 1, 'amiller',    'rxnorm:313990 — 1 tab PO daily'),
-- PID 104 Carlos Mendez (BH-PC HTN+MDD)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lisinopril 10mg tab',           104, NOW(), DATE_SUB(NOW(), INTERVAL 7 YEAR), 1, 'moconnor',   'rxnorm:314076 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Sertraline 100mg tab',          104, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR), 1, 'moconnor',   'rxnorm:313990 — 1 tab PO daily'),
-- PID 105 Linda Patel (GER OA+osteoporosis+hypothyroid+HTN)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lisinopril 20mg tab',           105, NOW(), DATE_SUB(NOW(), INTERVAL 15 YEAR), 1, 'erodriguez', 'rxnorm:314077 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Levothyroxine 75mcg tab',       105, NOW(), DATE_SUB(NOW(), INTERVAL 12 YEAR), 1, 'erodriguez', 'rxnorm:966222 — 1 tab PO daily on empty stomach'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Alendronate 70mg tab',          105, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR),  1, 'erodriguez', 'rxnorm:197910 — 1 tab PO weekly on empty stomach'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Acetaminophen 500mg tab',       105, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'erodriguez', 'rxnorm:198440 — 1–2 tabs PO every 6 hours as needed for OA pain'),
-- PID 106 Ethan Brooks (PSY-S ADHD)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Methylphenidate ER 36mg tab',   106, NOW(), DATE_SUB(NOW(), INTERVAL 6 YEAR), 1, 'amiller',    'rxnorm:847218 — 1 tab PO every morning (Schedule II)'),
-- PID 107 Maria Chen (CV-F post-ablation SVT)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Metoprolol tartrate 25mg tab',  107, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'mthompson',  'rxnorm:866435 — 1 tab PO twice daily as needed for palpitations'),
-- PID 108 Thomas Walsh (CHR T2DM+HTN+HLD) ← dashboard test pt
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Metformin 1000mg tab',          108, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR), 1, 'moconnor',   'rxnorm:860975 — 1 tab PO twice daily with meals'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lisinopril 20mg tab',           108, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR), 1, 'moconnor',   'rxnorm:314077 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Atorvastatin 40mg tab',         108, NOW(), DATE_SUB(NOW(), INTERVAL 7 YEAR), 1, 'moconnor',   'rxnorm:617312 — 1 tab PO at bedtime'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Aspirin 81mg tab',              108, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR), 1, 'moconnor',   'rxnorm:243670 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Pioglitazone 30mg tab',         108, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR), 1, 'moconnor',   'rxnorm:261241 — 1 tab PO daily'),
-- PID 109 Aisha Johnson (BH-PC GAD+Obesity)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Escitalopram 10mg tab',         109, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR), 1, 'erodriguez', 'rxnorm:321988 — 1 tab PO daily'),
-- PID 110 Brian Foster (PSY-S MDD recurrent)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Sertraline 100mg tab',          110, NOW(), DATE_SUB(NOW(), INTERVAL 7 YEAR), 1, 'amiller',    'rxnorm:313990 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Bupropion XL 300mg tab',        110, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR), 1, 'amiller',    'rxnorm:1232588 — 1 tab PO every morning (augmentation)'),
-- PID 112 Omar Hassan (CHR HTN)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lisinopril 20mg tab',           112, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR), 1, 'moconnor',   'rxnorm:314077 — 1 tab PO daily'),
-- PID 113 Patricia Monroe (GER HTN+HLD+hypothyroid)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lisinopril 10mg tab',           113, NOW(), DATE_SUB(NOW(), INTERVAL 14 YEAR), 1, 'erodriguez', 'rxnorm:314076 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Atorvastatin 20mg tab',         113, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'erodriguez', 'rxnorm:617314 — 1 tab PO at bedtime'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Levothyroxine 100mcg tab',      113, NOW(), DATE_SUB(NOW(), INTERVAL 9 YEAR),  1, 'erodriguez', 'rxnorm:966224 — 1 tab PO daily on empty stomach'),
-- PID 114 Kevin Park (PSY-S Bipolar II)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lamotrigine 200mg tab',         114, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'amiller',    'rxnorm:197716 — 1 tab PO daily (mood stabilizer)'),
-- PID 116 Gregory Stone (GER HTN+HLD+BPH+CKD3 polypharmacy)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Amlodipine 5mg tab',            116, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR),  1, 'moconnor',   'rxnorm:308135 — 1 tab PO daily (CKD3 — avoid ACEi)'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Atorvastatin 40mg tab',         116, NOW(), DATE_SUB(NOW(), INTERVAL 15 YEAR), 1, 'moconnor',   'rxnorm:617312 — 1 tab PO at bedtime'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Tamsulosin 0.4mg cap',          116, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR),  1, 'moconnor',   'rxnorm:313988 — 1 cap PO daily 30 min after dinner (BPH)'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Aspirin 81mg tab',              116, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'moconnor',   'rxnorm:243670 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Furosemide 20mg tab',           116, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR),  1, 'moconnor',   'rxnorm:310439 — 1 tab PO every morning (volume management)'),
-- PID 117 Nadia Okafor (CHR prediabetes+HLD)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Metformin 500mg tab',           117, NOW(), DATE_SUB(NOW(), INTERVAL 1 YEAR),  1, 'erodriguez', 'rxnorm:861007 — 1 tab PO twice daily with meals'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Atorvastatin 10mg tab',         117, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR),  1, 'erodriguez', 'rxnorm:617310 — 1 tab PO at bedtime'),
-- PID 118 Samuel Wright (PSY-S MDD+GAD)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Duloxetine 60mg cap',           118, NOW(), DATE_SUB(NOW(), INTERVAL 5 YEAR),  1, 'amiller',    'rxnorm:596926 — 1 cap PO daily'),
-- PID 119 Claire Bennett (CV-F IST)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Metoprolol tartrate 25mg tab',  119, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR),  1, 'mthompson',  'rxnorm:866435 — 1 tab PO twice daily'),
-- PID 120 Andre Dubois (SUD OUD remission + PTSD) — telehealth MAT
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Buprenorphine/Naloxone 8mg/2mg SL film', 120, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR), 1, 'moconnor', 'rxnorm:1010600 — 1 film SL daily (Suboxone; Schedule III; X-DEA prescribing)'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Sertraline 100mg tab',          120, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR),  1, 'moconnor',   'rxnorm:313990 — 1 tab PO daily (PTSD)'),
-- PID 122 Robert Castillo (PSY-S MDD+GAD+insomnia)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Mirtazapine 30mg tab',          122, NOW(), DATE_SUB(NOW(), INTERVAL 4 YEAR),  1, 'amiller',    'rxnorm:15996 — 1 tab PO at bedtime'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Sertraline 100mg tab',          122, NOW(), DATE_SUB(NOW(), INTERVAL 10 YEAR), 1, 'amiller',    'rxnorm:313990 — 1 tab PO daily'),
-- PID 126 Jerome Washington (PSY-S MDD remission + insomnia)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Sertraline 50mg tab',           126, NOW(), DATE_SUB(NOW(), INTERVAL 12 YEAR), 1, 'amiller',    'rxnorm:313989 — 1 tab PO daily (maintenance)'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Mirtazapine 15mg tab',          126, NOW(), DATE_SUB(NOW(), INTERVAL 8 YEAR),  1, 'amiller',    'rxnorm:313559 — 1 tab PO at bedtime'),
-- PID 127 Mei Liu (CV-F paroxysmal afib)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Apixaban 5mg tab',              127, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR),  1, 'mthompson',  'rxnorm:1364430 — 1 tab PO twice daily (anticoag)'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Metoprolol succinate ER 50mg',  127, NOW(), DATE_SUB(NOW(), INTERVAL 2 YEAR),  1, 'mthompson',  'rxnorm:866412 — 1 tab PO daily'),
-- PID 129 Amara Diallo (BH-PC MDD+HTN)
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Sertraline 50mg tab',           129, NOW(), DATE_SUB(NOW(), INTERVAL 1 YEAR),  1, 'erodriguez', 'rxnorm:313989 — 1 tab PO daily'),
(UNHEX(REPLACE(UUID(),'-','')), 'medication', '', 'Lisinopril 10mg tab',           129, NOW(), DATE_SUB(NOW(), INTERVAL 3 YEAR),  1, 'erodriguez', 'rxnorm:314076 — 1 tab PO daily');

-- Companion lists_medication sidecar row per medication (FHIR MedicationStatement
-- structure). All are outpatient telehealth-managed clinician-ordered meds.
INSERT INTO `lists_medication`
    (list_id, usage_category, usage_category_title, request_intent, request_intent_title, is_primary_record)
SELECT id, 'outpatient', 'Outpatient', 'order', 'Order', 1
  FROM `lists`
 WHERE type='medication' AND pid BETWEEN 100 AND 129;

-- =============================================================================
-- ACTIVE PRESCRIPTIONS  (Sprint 12 / S12-09)
--
-- ~38 active prescription rows — a clinically-realistic subset of each
-- patient's medication list (1–3 per patient). Drives the Prescriptions
-- dashboard panel. Controlled-substance flags: Methylphenidate ER (C-II)
-- and Buprenorphine/Naloxone (C-III, MAT) get refills=0 so the SE demo
-- reflects real DEA prescribing limits.
-- =============================================================================

INSERT INTO `prescriptions`
    (uuid, patient_id, provider_id, start_date, drug, drug_id, rxnorm_drugcode,
     dosage, quantity, route, refills, active, datetime, user, txDate,
     usage_category, usage_category_title, request_intent, request_intent_title)
VALUES
-- PID 100 James Harrison
(UNHEX(REPLACE(UUID(),'-','')), 100, 10, DATE_SUB(CURDATE(), INTERVAL 6 YEAR), 'Lisinopril 10mg tab',          0, '314076',  '10mg', '30', 'PO daily',          5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 100, 10, DATE_SUB(CURDATE(), INTERVAL 4 YEAR), 'Atorvastatin 20mg tab',         0, '617314',  '20mg', '30', 'PO at bedtime',     5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 101 Sofia Reyes
(UNHEX(REPLACE(UUID(),'-','')), 101, 11, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Sertraline 50mg tab',           0, '313989',  '50mg', '30', 'PO daily',          5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 102 David Kim
(UNHEX(REPLACE(UUID(),'-','')), 102, 13, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Aspirin 81mg tab',              0, '243670',  '81mg', '90', 'PO daily',          5, 1, NOW(), 'mthompson',  CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 102, 13, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Atorvastatin 80mg tab',         0, '617318',  '80mg', '30', 'PO at bedtime',     5, 1, NOW(), 'mthompson',  CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 102, 13, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Metoprolol succinate ER 50mg',  0, '866412',  '50mg', '30', 'PO daily',          5, 1, NOW(), 'mthompson',  CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 103 Rachel Nguyen
(UNHEX(REPLACE(UUID(),'-','')), 103, 12, DATE_SUB(CURDATE(), INTERVAL 8 YEAR), 'Sertraline 100mg tab',          0, '313990',  '100mg','30', 'PO daily',          5, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 104 Carlos Mendez
(UNHEX(REPLACE(UUID(),'-','')), 104, 10, DATE_SUB(CURDATE(), INTERVAL 7 YEAR), 'Lisinopril 10mg tab',          0, '314076',  '10mg', '30', 'PO daily',          5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 104, 10, DATE_SUB(CURDATE(), INTERVAL 3 YEAR), 'Sertraline 100mg tab',          0, '313990',  '100mg','30', 'PO daily',          5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 105 Linda Patel
(UNHEX(REPLACE(UUID(),'-','')), 105, 11, DATE_SUB(CURDATE(), INTERVAL 15 YEAR),'Lisinopril 20mg tab',          0, '314077',  '20mg', '30', 'PO daily',          5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 105, 11, DATE_SUB(CURDATE(), INTERVAL 12 YEAR),'Levothyroxine 75mcg tab',       0, '966222',  '75mcg','30', 'PO daily on empty stomach', 5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 105, 11, DATE_SUB(CURDATE(), INTERVAL 5 YEAR), 'Alendronate 70mg tab',          0, '197910',  '70mg', '4',  'PO weekly',         5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 106 Ethan Brooks (Schedule II — no auto-refill)
(UNHEX(REPLACE(UUID(),'-','')), 106, 12, DATE_SUB(CURDATE(), INTERVAL 6 YEAR), 'Methylphenidate ER 36mg tab',   0, '847218',  '36mg', '30', 'PO every morning',  0, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 107 Maria Chen
(UNHEX(REPLACE(UUID(),'-','')), 107, 13, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Metoprolol tartrate 25mg tab',  0, '866435',  '25mg', '60', 'PO twice daily PRN', 5, 1, NOW(), 'mthompson',  CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 108 Thomas Walsh ← dashboard test pt
(UNHEX(REPLACE(UUID(),'-','')), 108, 10, DATE_SUB(CURDATE(), INTERVAL 5 YEAR), 'Metformin 1000mg tab',          0, '860975',  '1000mg','60','PO twice daily with meals', 5, 1, NOW(), 'moconnor', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 108, 10, DATE_SUB(CURDATE(), INTERVAL 8 YEAR), 'Lisinopril 20mg tab',           0, '314077',  '20mg', '30', 'PO daily',          5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 108, 10, DATE_SUB(CURDATE(), INTERVAL 7 YEAR), 'Atorvastatin 40mg tab',         0, '617312',  '40mg', '30', 'PO at bedtime',     5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 109 Aisha Johnson
(UNHEX(REPLACE(UUID(),'-','')), 109, 11, DATE_SUB(CURDATE(), INTERVAL 4 YEAR), 'Escitalopram 10mg tab',         0, '321988',  '10mg', '30', 'PO daily',          5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 110 Brian Foster
(UNHEX(REPLACE(UUID(),'-','')), 110, 12, DATE_SUB(CURDATE(), INTERVAL 7 YEAR), 'Sertraline 100mg tab',          0, '313990',  '100mg','30', 'PO daily',          5, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 110, 12, DATE_SUB(CURDATE(), INTERVAL 3 YEAR), 'Bupropion XL 300mg tab',        0, '1232588', '300mg','30', 'PO every morning',  5, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 112 Omar Hassan
(UNHEX(REPLACE(UUID(),'-','')), 112, 10, DATE_SUB(CURDATE(), INTERVAL 5 YEAR), 'Lisinopril 20mg tab',           0, '314077',  '20mg', '30', 'PO daily',          5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 113 Patricia Monroe
(UNHEX(REPLACE(UUID(),'-','')), 113, 11, DATE_SUB(CURDATE(), INTERVAL 14 YEAR),'Lisinopril 10mg tab',          0, '314076',  '10mg', '30', 'PO daily',          5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 113, 11, DATE_SUB(CURDATE(), INTERVAL 10 YEAR),'Atorvastatin 20mg tab',         0, '617314',  '20mg', '30', 'PO at bedtime',     5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 113, 11, DATE_SUB(CURDATE(), INTERVAL 9 YEAR), 'Levothyroxine 100mcg tab',      0, '966224',  '100mcg','30','PO daily on empty stomach', 5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 114 Kevin Park
(UNHEX(REPLACE(UUID(),'-','')), 114, 12, DATE_SUB(CURDATE(), INTERVAL 10 YEAR),'Lamotrigine 200mg tab',         0, '197716',  '200mg','30', 'PO daily',          5, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 116 Gregory Stone
(UNHEX(REPLACE(UUID(),'-','')), 116, 10, DATE_SUB(CURDATE(), INTERVAL 4 YEAR), 'Amlodipine 5mg tab',            0, '308135',  '5mg',  '30', 'PO daily',          5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 116, 10, DATE_SUB(CURDATE(), INTERVAL 15 YEAR),'Atorvastatin 40mg tab',         0, '617312',  '40mg', '30', 'PO at bedtime',     5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 116, 10, DATE_SUB(CURDATE(), INTERVAL 8 YEAR), 'Tamsulosin 0.4mg cap',          0, '313988',  '0.4mg','30', 'PO daily 30 min after dinner', 5, 1, NOW(), 'moconnor', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 117 Nadia Okafor
(UNHEX(REPLACE(UUID(),'-','')), 117, 11, DATE_SUB(CURDATE(), INTERVAL 1 YEAR), 'Metformin 500mg tab',           0, '861007',  '500mg','60', 'PO twice daily with meals', 5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 117, 11, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Atorvastatin 10mg tab',         0, '617310',  '10mg', '30', 'PO at bedtime',     5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 118 Samuel Wright
(UNHEX(REPLACE(UUID(),'-','')), 118, 12, DATE_SUB(CURDATE(), INTERVAL 5 YEAR), 'Duloxetine 60mg cap',           0, '596926',  '60mg', '30', 'PO daily',          5, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 119 Claire Bennett
(UNHEX(REPLACE(UUID(),'-','')), 119, 13, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Metoprolol tartrate 25mg tab',  0, '866435',  '25mg', '60', 'PO twice daily',    5, 1, NOW(), 'mthompson',  CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 120 Andre Dubois (Schedule III — MAT, monthly refill cycle, no auto-refill)
(UNHEX(REPLACE(UUID(),'-','')), 120, 10, DATE_SUB(CURDATE(), INTERVAL 3 YEAR), 'Buprenorphine/Naloxone 8mg/2mg SL film', 0, '1010600', '8/2mg','30','SL daily', 0, 1, NOW(), 'moconnor', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 120, 10, DATE_SUB(CURDATE(), INTERVAL 4 YEAR), 'Sertraline 100mg tab',          0, '313990',  '100mg','30', 'PO daily',          5, 1, NOW(), 'moconnor',   CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 122 Robert Castillo
(UNHEX(REPLACE(UUID(),'-','')), 122, 12, DATE_SUB(CURDATE(), INTERVAL 4 YEAR), 'Mirtazapine 30mg tab',          0, '15996',   '30mg', '30', 'PO at bedtime',     5, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 122, 12, DATE_SUB(CURDATE(), INTERVAL 10 YEAR),'Sertraline 100mg tab',          0, '313990',  '100mg','30', 'PO daily',          5, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 126 Jerome Washington
(UNHEX(REPLACE(UUID(),'-','')), 126, 12, DATE_SUB(CURDATE(), INTERVAL 12 YEAR),'Sertraline 50mg tab',           0, '313989',  '50mg', '30', 'PO daily',          5, 1, NOW(), 'amiller',    CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 127 Mei Liu
(UNHEX(REPLACE(UUID(),'-','')), 127, 13, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Apixaban 5mg tab',              0, '1364430', '5mg',  '60', 'PO twice daily',    5, 1, NOW(), 'mthompson',  CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 127, 13, DATE_SUB(CURDATE(), INTERVAL 2 YEAR), 'Metoprolol succinate ER 50mg',  0, '866412',  '50mg', '30', 'PO daily',          5, 1, NOW(), 'mthompson',  CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
-- PID 129 Amara Diallo
(UNHEX(REPLACE(UUID(),'-','')), 129, 11, DATE_SUB(CURDATE(), INTERVAL 1 YEAR), 'Sertraline 50mg tab',           0, '313989',  '50mg', '30', 'PO daily',          5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order'),
(UNHEX(REPLACE(UUID(),'-','')), 129, 11, DATE_SUB(CURDATE(), INTERVAL 3 YEAR), 'Lisinopril 10mg tab',           0, '314076',  '10mg', '30', 'PO daily',          5, 1, NOW(), 'erodriguez', CURDATE(), 'outpatient', 'Outpatient', 'order', 'Order');

-- =============================================================================
-- VITALS  (Sprint 12 / S12-10)
--
-- One form_vitals row per patient (29 patients; PID 124 NEW persona skipped),
-- dated to match the S12-05 historical encounter (30–59 days ago, offset by
-- 30 + (PID - 100) days). Values tuned per persona:
--   CHR / GER w/ HTN: BP 130–155 / 80–95, BMI 28–35
--   CV-F:             BP controlled 118–138 / 70–85
--   PSY-S / BH-PC:    Mostly normal BP, weight varies (some psych meds → gain)
--   HYA:              Normal across the board
--   SUD:              Normal, slightly underweight
-- Matching forms registry row inserted via JOIN-based INSERT so the visit
-- shows vitals under its Visit History entry.
-- =============================================================================

INSERT INTO `form_vitals`
    (uuid, date, pid, user, groupname, authorized, activity,
     bps, bpd, weight, height, BMI, temperature, pulse, respiration, oxygen_saturation)
VALUES
-- PID 100 James Harrison CHR HTN+HLD M48
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 30 DAY), 100, 'moconnor',   'Default', 1, 1, '138', '88',  198.0, 71.0, 27.6, 98.4, 76, 16, 98.00),
-- PID 101 Sofia Reyes BH-PC F35
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 31 DAY), 101, 'erodriguez', 'Default', 1, 1, '118', '76',  135.0, 64.0, 23.2, 98.6, 72, 14, 99.00),
-- PID 102 David Kim CV-F CAD+OldMI M60
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 32 DAY), 102, 'mthompson',  'Default', 1, 1, '128', '78',  175.0, 68.0, 26.6, 98.2, 68, 14, 97.00),
-- PID 103 Rachel Nguyen PSY-S F41
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 33 DAY), 103, 'amiller',    'Default', 1, 1, '116', '74',  142.0, 65.0, 23.6, 98.6, 80, 16, 99.00),
-- PID 104 Carlos Mendez BH-PC HTN+MDD M53
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 34 DAY), 104, 'moconnor',   'Default', 1, 1, '142', '90',  215.0, 70.0, 30.8, 98.4, 78, 16, 97.00),
-- PID 105 Linda Patel GER F67
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 35 DAY), 105, 'erodriguez', 'Default', 1, 1, '146', '82',  148.0, 62.0, 27.1, 98.0, 70, 16, 96.00),
-- PID 106 Ethan Brooks PSY-S ADHD M31
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 36 DAY), 106, 'amiller',    'Default', 1, 1, '120', '76',  160.0, 70.0, 23.0, 98.6, 74, 14, 99.00),
-- PID 107 Maria Chen CV-F SVT F43
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 37 DAY), 107, 'mthompson',  'Default', 1, 1, '122', '78',  138.0, 64.0, 23.7, 98.4, 72, 16, 99.00),
-- PID 108 Thomas Walsh CHR T2DM+HTN+HLD M56 ← dashboard test pt
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 38 DAY), 108, 'moconnor',   'Default', 1, 1, '148', '92',  225.0, 70.0, 32.3, 98.4, 82, 18, 96.00),
-- PID 109 Aisha Johnson BH-PC GAD+Obesity F33
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 39 DAY), 109, 'erodriguez', 'Default', 1, 1, '126', '82',  198.0, 65.0, 32.9, 98.6, 78, 16, 98.00),
-- PID 110 Brian Foster PSY-S MDD M46
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 40 DAY), 110, 'amiller',    'Default', 1, 1, '124', '80',  188.0, 71.0, 26.2, 98.4, 76, 16, 98.00),
-- PID 111 Yuki Tanaka CV-F MVP F28
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 41 DAY), 111, 'mthompson',  'Default', 1, 1, '114', '72',  118.0, 63.0, 20.9, 98.6, 68, 14, 100.00),
-- PID 112 Omar Hassan CHR HTN M51
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 42 DAY), 112, 'moconnor',   'Default', 1, 1, '136', '86',  185.0, 69.0, 27.3, 98.4, 74, 16, 98.00),
-- PID 113 Patricia Monroe GER HTN+HLD+hypothyroid F63
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 43 DAY), 113, 'erodriguez', 'Default', 1, 1, '144', '84',  168.0, 64.0, 28.8, 98.2, 72, 16, 97.00),
-- PID 114 Kevin Park PSY-S Bipolar II M37
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 44 DAY), 114, 'amiller',    'Default', 1, 1, '122', '78',  178.0, 70.0, 25.5, 98.6, 78, 16, 99.00),
-- PID 115 Fatima Ali CV-F PSVT F34
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 45 DAY), 115, 'mthompson',  'Default', 1, 1, '116', '74',  130.0, 63.0, 23.0, 98.6, 70, 14, 99.00),
-- PID 116 Gregory Stone GER HTN+HLD+BPH+CKD3 M71 polypharmacy
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 46 DAY), 116, 'moconnor',   'Default', 1, 1, '152', '86',  168.0, 69.0, 24.8, 98.0, 68, 18, 95.00),
-- PID 117 Nadia Okafor CHR prediabetes+HLD F40
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 47 DAY), 117, 'erodriguez', 'Default', 1, 1, '128', '82',  175.0, 67.0, 27.4, 98.4, 76, 16, 98.00),
-- PID 118 Samuel Wright PSY-S MDD+GAD M55
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 48 DAY), 118, 'amiller',    'Default', 1, 1, '128', '82',  195.0, 71.0, 27.2, 98.4, 76, 16, 98.00),
-- PID 119 Claire Bennett CV-F IST F31
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 49 DAY), 119, 'mthompson',  'Default', 1, 1, '110', '70',  128.0, 65.0, 21.3, 98.6, 88, 16, 99.00),
-- PID 120 Andre Dubois SUD OUD+PTSD M42
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 50 DAY), 120, 'moconnor',   'Default', 1, 1, '122', '78',  155.0, 70.0, 22.2, 98.4, 76, 16, 98.00),
-- PID 121 Priya Sharma HYA F34
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 51 DAY), 121, 'erodriguez', 'Default', 1, 1, '110', '70',  128.0, 64.0, 22.0, 98.6, 70, 14, 100.00),
-- PID 122 Robert Castillo PSY-S MDD+GAD+insomnia M58
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 52 DAY), 122, 'amiller',    'Default', 1, 1, '124', '78',  205.0, 70.0, 29.4, 98.4, 74, 16, 97.00),
-- PID 123 Hannah Scott CV-F PVCs F36
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 53 DAY), 123, 'mthompson',  'Default', 1, 1, '116', '74',  135.0, 65.0, 22.5, 98.6, 72, 14, 99.00),
-- PID 124 NEW persona — skipped
-- PID 125 Isabelle Martin HYA F27
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 55 DAY), 125, 'erodriguez', 'Default', 1, 1, '108', '68',  120.0, 63.0, 21.3, 98.6, 68, 14, 100.00),
-- PID 126 Jerome Washington PSY-S MDD remission M65
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 56 DAY), 126, 'amiller',    'Default', 1, 1, '130', '80',  182.0, 70.0, 26.1, 98.4, 70, 16, 97.00),
-- PID 127 Mei Liu CV-F paroxysmal afib F38
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 57 DAY), 127, 'mthompson',  'Default', 1, 1, '120', '76',  140.0, 64.0, 24.0, 98.6, 74, 16, 99.00),
-- PID 128 Tyler Hughes HYA M30
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 58 DAY), 128, 'moconnor',   'Default', 1, 1, '118', '74',  165.0, 71.0, 23.0, 98.6, 64, 14, 100.00),
-- PID 129 Amara Diallo BH-PC MDD+HTN F41
(UNHEX(REPLACE(UUID(),'-','')), DATE_SUB(NOW(), INTERVAL 59 DAY), 129, 'erodriguez', 'Default', 1, 1, '136', '86',  155.0, 65.0, 25.8, 98.4, 74, 16, 98.00);

-- Forms registry row per vitals so it appears under the historical encounter
INSERT INTO `forms`
    (date, encounter, form_name, form_id, pid, user, groupname, authorized, deleted, formdir, provider_id)
SELECT fv.date, fe.encounter, 'Vitals', fv.id, fv.pid, u.username, 'Default', 1, 0, 'vitals', fe.provider_id
  FROM form_vitals fv
  JOIN form_encounter fe ON fe.pid = fv.pid AND fe.encounter BETWEEN 30001 AND 30029
  JOIN users u ON u.id = fe.provider_id
 WHERE fv.pid BETWEEN 100 AND 129;

-- =============================================================================
-- LAB RESULTS  (Sprint 12 / S12-11)
--
-- 10 lab panels across 6 chronic-disease patients via the four-table chain:
-- procedure_order → procedure_order_code → procedure_report → procedure_result.
-- Hardcoded IDs (orders 40001–40010, reports 50001–50010) so the chain can
-- reference itself in plain SQL without LAST_INSERT_ID gymnastics.
-- encounter_id is looked up by subquery against the S12-05 historical encounter.
-- LOINC codes in result_code; abnormal flag (H/L/'') reflects clinical reality.
--
-- Coverage:
--   PID 108 Thomas Walsh (CHR T2DM+HTN+HLD): CMP + Lipid + A1c        ← dashboard test pt
--   PID 102 David Kim    (CV-F post-MI):     Lipid + BNP
--   PID 116 Gregory Stone (GER CKD3):        CMP + Lipid              (creatinine elevated)
--   PID 105 Linda Patel   (GER hypothyroid): TSH
--   PID 117 Nadia Okafor  (CHR prediabetes): A1c
--   PID 118 Samuel Wright (PSY-S duloxetine):LFTs                     (drug monitoring)
-- =============================================================================

INSERT INTO `procedure_order`
    (procedure_order_id, uuid, provider_id, patient_id, encounter_id,
     date_collected, date_ordered, order_status, activity, procedure_order_type, order_intent, lab_id)
VALUES
(40001, UNHEX(REPLACE(UUID(),'-','')), 10, 108, (SELECT id FROM form_encounter WHERE encounter=30009 LIMIT 1), DATE_SUB(NOW(), INTERVAL 38 DAY), DATE_SUB(NOW(), INTERVAL 38 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40002, UNHEX(REPLACE(UUID(),'-','')), 10, 108, (SELECT id FROM form_encounter WHERE encounter=30009 LIMIT 1), DATE_SUB(NOW(), INTERVAL 38 DAY), DATE_SUB(NOW(), INTERVAL 38 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40003, UNHEX(REPLACE(UUID(),'-','')), 10, 108, (SELECT id FROM form_encounter WHERE encounter=30009 LIMIT 1), DATE_SUB(NOW(), INTERVAL 38 DAY), DATE_SUB(NOW(), INTERVAL 38 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40004, UNHEX(REPLACE(UUID(),'-','')), 13, 102, (SELECT id FROM form_encounter WHERE encounter=30003 LIMIT 1), DATE_SUB(NOW(), INTERVAL 32 DAY), DATE_SUB(NOW(), INTERVAL 32 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40005, UNHEX(REPLACE(UUID(),'-','')), 13, 102, (SELECT id FROM form_encounter WHERE encounter=30003 LIMIT 1), DATE_SUB(NOW(), INTERVAL 32 DAY), DATE_SUB(NOW(), INTERVAL 32 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40006, UNHEX(REPLACE(UUID(),'-','')), 10, 116, (SELECT id FROM form_encounter WHERE encounter=30017 LIMIT 1), DATE_SUB(NOW(), INTERVAL 46 DAY), DATE_SUB(NOW(), INTERVAL 46 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40007, UNHEX(REPLACE(UUID(),'-','')), 10, 116, (SELECT id FROM form_encounter WHERE encounter=30017 LIMIT 1), DATE_SUB(NOW(), INTERVAL 46 DAY), DATE_SUB(NOW(), INTERVAL 46 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40008, UNHEX(REPLACE(UUID(),'-','')), 11, 105, (SELECT id FROM form_encounter WHERE encounter=30006 LIMIT 1), DATE_SUB(NOW(), INTERVAL 35 DAY), DATE_SUB(NOW(), INTERVAL 35 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40009, UNHEX(REPLACE(UUID(),'-','')), 11, 117, (SELECT id FROM form_encounter WHERE encounter=30018 LIMIT 1), DATE_SUB(NOW(), INTERVAL 47 DAY), DATE_SUB(NOW(), INTERVAL 47 DAY), 'completed', 1, 'laboratory_test', 'order', 0),
(40010, UNHEX(REPLACE(UUID(),'-','')), 12, 118, (SELECT id FROM form_encounter WHERE encounter=30019 LIMIT 1), DATE_SUB(NOW(), INTERVAL 48 DAY), DATE_SUB(NOW(), INTERVAL 48 DAY), 'completed', 1, 'laboratory_test', 'order', 0);

-- Order codes — what was ordered (panel name + procedure code)
INSERT INTO `procedure_order_code`
    (procedure_order_id, procedure_order_seq, procedure_code, procedure_name, procedure_source, procedure_order_title)
VALUES
(40001, 1, '80053', 'Comprehensive Metabolic Panel',  '1', 'CMP'),
(40002, 1, '80061', 'Lipid Panel',                    '1', 'Lipid Panel'),
(40003, 1, '83036', 'Hemoglobin A1c',                 '1', 'HbA1c'),
(40004, 1, '80061', 'Lipid Panel',                    '1', 'Lipid Panel'),
(40005, 1, '83880', 'BNP (B-type Natriuretic Peptide)','1','BNP'),
(40006, 1, '80053', 'Comprehensive Metabolic Panel',  '1', 'CMP'),
(40007, 1, '80061', 'Lipid Panel',                    '1', 'Lipid Panel'),
(40008, 1, '84443', 'TSH (Thyroid Stimulating Hormone)','1','TSH'),
(40009, 1, '83036', 'Hemoglobin A1c',                 '1', 'HbA1c'),
(40010, 1, '80076', 'Hepatic Function Panel',         '1', 'LFTs');

-- Reports — final / reviewed
INSERT INTO `procedure_report`
    (procedure_report_id, uuid, procedure_order_id, procedure_order_seq,
     date_collected, date_report, source, specimen_num, report_status, review_status)
VALUES
(50001, UNHEX(REPLACE(UUID(),'-','')), 40001, 1, DATE_SUB(NOW(), INTERVAL 38 DAY), DATE_SUB(NOW(), INTERVAL 37 DAY), 1, 'SPEC108-CMP', 'final', 'reviewed'),
(50002, UNHEX(REPLACE(UUID(),'-','')), 40002, 1, DATE_SUB(NOW(), INTERVAL 38 DAY), DATE_SUB(NOW(), INTERVAL 37 DAY), 1, 'SPEC108-LIP', 'final', 'reviewed'),
(50003, UNHEX(REPLACE(UUID(),'-','')), 40003, 1, DATE_SUB(NOW(), INTERVAL 38 DAY), DATE_SUB(NOW(), INTERVAL 37 DAY), 1, 'SPEC108-A1C', 'final', 'reviewed'),
(50004, UNHEX(REPLACE(UUID(),'-','')), 40004, 1, DATE_SUB(NOW(), INTERVAL 32 DAY), DATE_SUB(NOW(), INTERVAL 31 DAY), 1, 'SPEC102-LIP', 'final', 'reviewed'),
(50005, UNHEX(REPLACE(UUID(),'-','')), 40005, 1, DATE_SUB(NOW(), INTERVAL 32 DAY), DATE_SUB(NOW(), INTERVAL 31 DAY), 1, 'SPEC102-BNP', 'final', 'reviewed'),
(50006, UNHEX(REPLACE(UUID(),'-','')), 40006, 1, DATE_SUB(NOW(), INTERVAL 46 DAY), DATE_SUB(NOW(), INTERVAL 45 DAY), 1, 'SPEC116-CMP', 'final', 'reviewed'),
(50007, UNHEX(REPLACE(UUID(),'-','')), 40007, 1, DATE_SUB(NOW(), INTERVAL 46 DAY), DATE_SUB(NOW(), INTERVAL 45 DAY), 1, 'SPEC116-LIP', 'final', 'reviewed'),
(50008, UNHEX(REPLACE(UUID(),'-','')), 40008, 1, DATE_SUB(NOW(), INTERVAL 35 DAY), DATE_SUB(NOW(), INTERVAL 34 DAY), 1, 'SPEC105-TSH', 'final', 'reviewed'),
(50009, UNHEX(REPLACE(UUID(),'-','')), 40009, 1, DATE_SUB(NOW(), INTERVAL 47 DAY), DATE_SUB(NOW(), INTERVAL 46 DAY), 1, 'SPEC117-A1C', 'final', 'reviewed'),
(50010, UNHEX(REPLACE(UUID(),'-','')), 40010, 1, DATE_SUB(NOW(), INTERVAL 48 DAY), DATE_SUB(NOW(), INTERVAL 47 DAY), 1, 'SPEC118-LFT', 'final', 'reviewed');

-- Individual results — LOINC-coded with reference ranges + abnormal flags
INSERT INTO `procedure_result`
    (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status)
VALUES
-- 50001 PID 108 CMP (glucose elevated, creatinine borderline, potassium normal)
(UNHEX(REPLACE(UUID(),'-','')), 50001, 'N', '2345-7',  'Glucose',       DATE_SUB(NOW(), INTERVAL 37 DAY), 'mg/dL',  '168', '70-99',    'H', 'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50001, 'N', '2160-0',  'Creatinine',    DATE_SUB(NOW(), INTERVAL 37 DAY), 'mg/dL',  '1.05','0.7-1.3',  '',  'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50001, 'N', '2823-3',  'Potassium',     DATE_SUB(NOW(), INTERVAL 37 DAY), 'mmol/L', '4.2', '3.5-5.0',  '',  'final'),
-- 50002 PID 108 Lipid (elevated despite statin)
(UNHEX(REPLACE(UUID(),'-','')), 50002, 'N', '2093-3',  'Total Cholesterol', DATE_SUB(NOW(), INTERVAL 37 DAY), 'mg/dL', '212', '<200',    'H', 'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50002, 'N', '2085-9',  'HDL',            DATE_SUB(NOW(), INTERVAL 37 DAY), 'mg/dL', '38',  '>40',      'L', 'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50002, 'N', '2089-1',  'LDL',            DATE_SUB(NOW(), INTERVAL 37 DAY), 'mg/dL', '128', '<100',     'H', 'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50002, 'N', '2571-8',  'Triglycerides',  DATE_SUB(NOW(), INTERVAL 37 DAY), 'mg/dL', '188', '<150',     'H', 'final'),
-- 50003 PID 108 A1c (uncontrolled T2DM)
(UNHEX(REPLACE(UUID(),'-','')), 50003, 'N', '4548-4',  'Hemoglobin A1c', DATE_SUB(NOW(), INTERVAL 37 DAY), '%',     '7.8', '<7.0',     'H', 'final'),
-- 50004 PID 102 Lipid (well-controlled on atorvastatin 80mg)
(UNHEX(REPLACE(UUID(),'-','')), 50004, 'N', '2093-3',  'Total Cholesterol', DATE_SUB(NOW(), INTERVAL 31 DAY), 'mg/dL', '162', '<200',  '',  'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50004, 'N', '2085-9',  'HDL',            DATE_SUB(NOW(), INTERVAL 31 DAY), 'mg/dL', '48',  '>40',      '',  'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50004, 'N', '2089-1',  'LDL',            DATE_SUB(NOW(), INTERVAL 31 DAY), 'mg/dL', '68',  '<70',      '',  'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50004, 'N', '2571-8',  'Triglycerides',  DATE_SUB(NOW(), INTERVAL 31 DAY), 'mg/dL', '142', '<150',     '',  'final'),
-- 50005 PID 102 BNP (mildly elevated, post-MI stable)
(UNHEX(REPLACE(UUID(),'-','')), 50005, 'N', '30934-4', 'BNP',            DATE_SUB(NOW(), INTERVAL 31 DAY), 'pg/mL', '128', '<100',     'H', 'final'),
-- 50006 PID 116 CMP (creatinine elevated — CKD3)
(UNHEX(REPLACE(UUID(),'-','')), 50006, 'N', '2345-7',  'Glucose',       DATE_SUB(NOW(), INTERVAL 45 DAY), 'mg/dL',  '94',  '70-99',   '',  'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50006, 'N', '2160-0',  'Creatinine',    DATE_SUB(NOW(), INTERVAL 45 DAY), 'mg/dL',  '1.78','0.7-1.3', 'H', 'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50006, 'N', '2823-3',  'Potassium',     DATE_SUB(NOW(), INTERVAL 45 DAY), 'mmol/L', '4.5', '3.5-5.0', '',  'final'),
-- 50007 PID 116 Lipid (controlled on statin)
(UNHEX(REPLACE(UUID(),'-','')), 50007, 'N', '2093-3',  'Total Cholesterol', DATE_SUB(NOW(), INTERVAL 45 DAY), 'mg/dL', '178', '<200',  '',  'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50007, 'N', '2085-9',  'HDL',            DATE_SUB(NOW(), INTERVAL 45 DAY), 'mg/dL', '52',  '>40',      '',  'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50007, 'N', '2089-1',  'LDL',            DATE_SUB(NOW(), INTERVAL 45 DAY), 'mg/dL', '88',  '<100',     '',  'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50007, 'N', '2571-8',  'Triglycerides',  DATE_SUB(NOW(), INTERVAL 45 DAY), 'mg/dL', '162', '<150',     'H', 'final'),
-- 50008 PID 105 TSH (well-replaced on levothyroxine)
(UNHEX(REPLACE(UUID(),'-','')), 50008, 'N', '3024-7',  'TSH',            DATE_SUB(NOW(), INTERVAL 34 DAY), 'mIU/L', '2.4', '0.4-4.0',  '',  'final'),
-- 50009 PID 117 A1c (prediabetes range, lifestyle counseling)
(UNHEX(REPLACE(UUID(),'-','')), 50009, 'N', '4548-4',  'Hemoglobin A1c', DATE_SUB(NOW(), INTERVAL 46 DAY), '%',     '6.1', '<5.7',     'H', 'final'),
-- 50010 PID 118 LFTs (mild duloxetine-related ALT bump)
(UNHEX(REPLACE(UUID(),'-','')), 50010, 'N', '1742-6',  'ALT',            DATE_SUB(NOW(), INTERVAL 47 DAY), 'U/L',   '52',  '<40',      'H', 'final'),
(UNHEX(REPLACE(UUID(),'-','')), 50010, 'N', '1920-8',  'AST',            DATE_SUB(NOW(), INTERVAL 47 DAY), 'U/L',   '38',  '<35',      'H', 'final');

-- =============================================================================
-- LIFESTYLE + FAMILY HISTORY  (Sprint 12 / S12-12)
--
-- One history_data row per patient (29 rows; PID 124 NEW persona skipped).
-- Tobacco status clears the "Past Due Assessment: Tobacco" reminder for every
-- patient who has one set. Smoking-cessation HYA targets (PIDs 125, 128) are
-- intentionally current smokers so the telehealth counseling visit has a
-- legitimate reason. PID 120 (SUD persona) is also a current smoker, which
-- matches the high tobacco/OUD comorbidity in real practice.
--
-- Family history `relatives_*` flags use 'YES' / 'NO' strings to drive the
-- corresponding dashboard checkmarks.
-- =============================================================================

INSERT INTO `history_data`
    (uuid, pid, date, tobacco, alcohol, exercise_patterns, sleep_patterns, coffee, seatbelt_use,
     history_mother, history_father,
     relatives_cancer, relatives_diabetes, relatives_high_blood_pressure, relatives_heart_problems, relatives_stroke, relatives_mental_illness)
VALUES
-- PID 100 James Harrison CHR M48
(UNHEX(REPLACE(UUID(),'-','')), 100, NOW(), 'Former smoker',              'Light drinker (1-2/wk)',  'Moderate',  '7 hrs/night', '2 cups/day',   'Always', 'HTN, T2DM',         'HTN, CAD',          'NO',  'YES', 'YES', 'YES', 'NO',  'NO'),
-- PID 101 Sofia Reyes BH-PC F35
(UNHEX(REPLACE(UUID(),'-','')), 101, NOW(), 'Never smoker',               'Light drinker (1/wk)',    'Light',     '6 hrs/night', '1 cup/day',    'Always', 'Anxiety',           'Healthy',           'NO',  'NO',  'NO',  'NO',  'NO',  'YES'),
-- PID 102 David Kim CV-F M60
(UNHEX(REPLACE(UUID(),'-','')), 102, NOW(), 'Former smoker (quit 2024)',  'Non-drinker',             'Light',     '7 hrs/night', '1 cup/day',    'Always', 'HTN',               'CAD, MI age 58',    'NO',  'YES', 'YES', 'YES', 'YES', 'NO'),
-- PID 103 Rachel Nguyen PSY-S F41
(UNHEX(REPLACE(UUID(),'-','')), 103, NOW(), 'Never smoker',               'Moderate (4-6/wk)',       'Light',     '5 hrs/night', '3 cups/day',   'Always', 'Anxiety, depression', 'Healthy',         'NO',  'NO',  'NO',  'NO',  'NO',  'YES'),
-- PID 104 Carlos Mendez BH-PC M53
(UNHEX(REPLACE(UUID(),'-','')), 104, NOW(), 'Current Every Day Smoker (1 ppd, 30 yrs)', 'Heavy drinker (10+/wk)', 'Sedentary', '6 hrs/night', '3 cups/day', 'Sometimes', 'HTN, MDD', 'HTN, ETOH', 'NO', 'YES', 'YES', 'NO', 'NO', 'YES'),
-- PID 105 Linda Patel GER F67
(UNHEX(REPLACE(UUID(),'-','')), 105, NOW(), 'Never smoker',               'Non-drinker',             'Light',     '7 hrs/night', '1 cup/day',    'Always', 'Hypothyroid, OA',   'CAD',               'YES', 'NO',  'YES', 'YES', 'NO',  'NO'),
-- PID 106 Ethan Brooks PSY-S M31
(UNHEX(REPLACE(UUID(),'-','')), 106, NOW(), 'Former smoker (vapes)',      'Moderate (3-5/wk)',       'Vigorous',  '6 hrs/night', '4 cups/day',   'Always', 'ADHD',              'ADHD',              'NO',  'NO',  'NO',  'NO',  'NO',  'YES'),
-- PID 107 Maria Chen CV-F F43
(UNHEX(REPLACE(UUID(),'-','')), 107, NOW(), 'Never smoker',               'Light drinker',           'Moderate',  '7 hrs/night', '2 cups/day',   'Always', 'Healthy',           'SVT',               'NO',  'NO',  'NO',  'YES', 'NO',  'NO'),
-- PID 108 Thomas Walsh CHR M56 ← dashboard test pt
(UNHEX(REPLACE(UUID(),'-','')), 108, NOW(), 'Former smoker (quit 2018)',  'Moderate (5-7/wk)',       'Sedentary', '6 hrs/night', '3 cups/day',   'Always', 'T2DM, HTN',         'T2DM, MI age 62, CAD', 'YES', 'YES', 'YES', 'YES', 'NO',  'NO'),
-- PID 109 Aisha Johnson BH-PC F33
(UNHEX(REPLACE(UUID(),'-','')), 109, NOW(), 'Never smoker',               'Light drinker',           'Light',     '7 hrs/night', '2 cups/day',   'Always', 'Anxiety, obesity',  'HTN, T2DM',         'NO',  'YES', 'YES', 'NO',  'NO',  'YES'),
-- PID 110 Brian Foster PSY-S M46
(UNHEX(REPLACE(UUID(),'-','')), 110, NOW(), 'Current Every Day Smoker (0.5 ppd)', 'Moderate (5/wk)', 'Light',     '5 hrs/night', '4 cups/day',   'Always', 'MDD',               'MDD, ETOH',         'NO',  'NO',  'NO',  'NO',  'NO',  'YES'),
-- PID 111 Yuki Tanaka CV-F F28
(UNHEX(REPLACE(UUID(),'-','')), 111, NOW(), 'Never smoker',               'Non-drinker',             'Vigorous',  '8 hrs/night', '1 cup/day',    'Always', 'MVP',               'Healthy',           'NO',  'NO',  'NO',  'YES', 'NO',  'NO'),
-- PID 112 Omar Hassan CHR M51
(UNHEX(REPLACE(UUID(),'-','')), 112, NOW(), 'Former smoker',              'Non-drinker',             'Moderate',  '7 hrs/night', '2 cups/day',   'Always', 'HTN',               'HTN, T2DM',         'NO',  'YES', 'YES', 'NO',  'YES', 'NO'),
-- PID 113 Patricia Monroe GER F63
(UNHEX(REPLACE(UUID(),'-','')), 113, NOW(), 'Never smoker',               'Light drinker',           'Light',     '7 hrs/night', '1 cup/day',    'Always', 'Hypothyroid, HTN',  'HLD, stroke age 70', 'YES', 'NO', 'YES', 'NO',  'YES', 'NO'),
-- PID 114 Kevin Park PSY-S M37
(UNHEX(REPLACE(UUID(),'-','')), 114, NOW(), 'Current Every Day Smoker',   'Heavy (8-10/wk)',         'Light',     '5 hrs/night', '4 cups/day',   'Always', 'Bipolar',           'Bipolar',           'NO',  'NO',  'NO',  'NO',  'NO',  'YES'),
-- PID 115 Fatima Ali CV-F F34
(UNHEX(REPLACE(UUID(),'-','')), 115, NOW(), 'Never smoker',               'Non-drinker',             'Moderate',  '8 hrs/night', '1 cup/day',    'Always', 'Healthy',           'PSVT',              'NO',  'NO',  'NO',  'YES', 'NO',  'NO'),
-- PID 116 Gregory Stone GER M71 polypharmacy
(UNHEX(REPLACE(UUID(),'-','')), 116, NOW(), 'Former smoker (quit 1999)',  'Light drinker',           'Light',     '7 hrs/night', '2 cups/day',   'Always', 'HTN, stroke age 75', 'CAD, MI age 65',   'YES', 'NO',  'YES', 'YES', 'YES', 'NO'),
-- PID 117 Nadia Okafor CHR F40
(UNHEX(REPLACE(UUID(),'-','')), 117, NOW(), 'Never smoker',               'Light drinker',           'Moderate',  '7 hrs/night', '2 cups/day',   'Always', 'T2DM',              'T2DM, HTN',         'NO',  'YES', 'YES', 'NO',  'NO',  'NO'),
-- PID 118 Samuel Wright PSY-S M55
(UNHEX(REPLACE(UUID(),'-','')), 118, NOW(), 'Current Every Day Smoker',   'Moderate (5/wk)',         'Sedentary', '5 hrs/night', '4 cups/day',   'Always', 'MDD, HTN',          'MDD',               'NO',  'NO',  'YES', 'NO',  'NO',  'YES'),
-- PID 119 Claire Bennett CV-F F31
(UNHEX(REPLACE(UUID(),'-','')), 119, NOW(), 'Never smoker',               'Light drinker',           'Vigorous',  '7 hrs/night', '3 cups/day',   'Always', 'Anxiety',           'Healthy',           'NO',  'NO',  'NO',  'NO',  'NO',  'NO'),
-- PID 120 Andre Dubois SUD M42 — high tobacco/OUD comorbidity
(UNHEX(REPLACE(UUID(),'-','')), 120, NOW(), 'Current Every Day Smoker (1 ppd, 20 yrs)', 'Non-drinker (in recovery)', 'Sedentary', '6 hrs/night', '4 cups/day', 'Always', 'ETOH', 'OUD, ETOH', 'NO', 'NO', 'NO', 'NO', 'NO', 'YES'),
-- PID 121 Priya Sharma HYA F34
(UNHEX(REPLACE(UUID(),'-','')), 121, NOW(), 'Never smoker',               'Light drinker (2/wk)',    'Vigorous',  '8 hrs/night', '1 cup/day',    'Always', 'Healthy',           'Healthy',           'NO',  'NO',  'NO',  'NO',  'NO',  'NO'),
-- PID 122 Robert Castillo PSY-S M58
(UNHEX(REPLACE(UUID(),'-','')), 122, NOW(), 'Former smoker',              'Moderate (4-6/wk)',       'Light',     '5 hrs/night', '3 cups/day',   'Always', 'MDD',               'MDD, CAD',          'NO',  'NO',  'YES', 'YES', 'NO',  'YES'),
-- PID 123 Hannah Scott CV-F F36
(UNHEX(REPLACE(UUID(),'-','')), 123, NOW(), 'Never smoker',               'Light drinker',           'Moderate',  '7 hrs/night', '2 cups/day',   'Always', 'Healthy',           'Healthy',           'NO',  'NO',  'NO',  'NO',  'NO',  'NO'),
-- PID 124 (NEW) intentionally skipped
-- PID 125 Isabelle Martin HYA F27 — smoking cessation persona
(UNHEX(REPLACE(UUID(),'-','')), 125, NOW(), 'Current Every Day Smoker (0.5 ppd, 8 yrs)', 'Moderate (3-5/wk)', 'Light', '6 hrs/night', '2 cups/day', 'Always', 'Healthy', 'Healthy', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO'),
-- PID 126 Jerome Washington PSY-S M65
(UNHEX(REPLACE(UUID(),'-','')), 126, NOW(), 'Former smoker (quit 1990)',  'Non-drinker',             'Light',     '6 hrs/night', '2 cups/day',   'Always', 'MDD',               'HTN, MDD',          'NO',  'NO',  'YES', 'NO',  'NO',  'YES'),
-- PID 127 Mei Liu CV-F F38
(UNHEX(REPLACE(UUID(),'-','')), 127, NOW(), 'Never smoker',               'Light drinker',           'Moderate',  '7 hrs/night', '2 cups/day',   'Always', 'Afib',              'Afib, CAD',         'NO',  'NO',  'NO',  'YES', 'NO',  'NO'),
-- PID 128 Tyler Hughes HYA M30 — smoking cessation persona
(UNHEX(REPLACE(UUID(),'-','')), 128, NOW(), 'Current Every Day Smoker (1 ppd, 10 yrs)', 'Moderate (5-7/wk)', 'Vigorous', '7 hrs/night', '3 cups/day', 'Always', 'Healthy', 'HTN', 'NO', 'NO', 'YES', 'NO', 'NO', 'NO'),
-- PID 129 Amara Diallo BH-PC F41
(UNHEX(REPLACE(UUID(),'-','')), 129, NOW(), 'Former smoker (quit 2015)',  'Light drinker',           'Moderate',  '6 hrs/night', '2 cups/day',   'Always', 'Anxiety, HTN',      'HTN',               'YES', 'NO',  'YES', 'NO',  'NO',  'YES');

-- =============================================================================
-- IMMUNIZATIONS  (Sprint 12 / S12-13)
--
-- CVX-coded immunization rows applied by SELECT-based INSERTs against each
-- target cohort. PID 124 (NEW persona) skipped throughout.
--
-- Coverage strategy:
--   Flu (CVX 140)       — every non-skip patient,        current season
--   COVID booster (208) — every adult except HYA-young   2026-01-15
--   Tdap (CVX 115)      — every adult                    4 years ago
--   Shingrix (CVX 187)  — 50+                            2024-03-15
--   Pneumovax-23 (33)   — 65+                            2023-06-15
-- =============================================================================

-- Flu (current season, intramuscular, left deltoid)
INSERT INTO `immunizations`
    (uuid, patient_id, administered_date, cvx_code, manufacturer, lot_number,
     administered_by_id, route, administration_site, completion_status, added_erroneously, update_date)
SELECT UNHEX(REPLACE(UUID(),'-','')), pid, '2025-10-15', '140', 'Sanofi Pasteur', 'FL2025-Q4-A',
       providerID, 'Intramuscular', 'Left deltoid', 'Completed', 0, NOW()
  FROM patient_data
 WHERE pid BETWEEN 100 AND 129 AND pid != 124;

-- COVID booster (everyone except NEW + HYA-young)
INSERT INTO `immunizations`
    (uuid, patient_id, administered_date, cvx_code, manufacturer, lot_number,
     administered_by_id, route, administration_site, completion_status, added_erroneously, update_date)
SELECT UNHEX(REPLACE(UUID(),'-','')), pid, '2026-01-15', '208', 'Pfizer-BioNTech', 'COV2026A',
       providerID, 'Intramuscular', 'Right deltoid', 'Completed', 0, NOW()
  FROM patient_data
 WHERE pid BETWEEN 100 AND 129 AND pid NOT IN (124, 121, 125, 128);

-- Tdap (every non-skip adult, given ~4 years ago)
INSERT INTO `immunizations`
    (uuid, patient_id, administered_date, cvx_code, manufacturer, lot_number,
     administered_by_id, route, administration_site, completion_status, added_erroneously, update_date)
SELECT UNHEX(REPLACE(UUID(),'-','')), pid, '2022-05-15', '115', 'Sanofi Pasteur', 'TD2022B',
       providerID, 'Intramuscular', 'Left deltoid', 'Completed', 0, NOW()
  FROM patient_data
 WHERE pid BETWEEN 100 AND 129 AND pid != 124;

-- Shingrix — recombinant zoster vaccine for adults 50+
INSERT INTO `immunizations`
    (uuid, patient_id, administered_date, cvx_code, manufacturer, lot_number,
     administered_by_id, route, administration_site, completion_status, added_erroneously, update_date)
SELECT UNHEX(REPLACE(UUID(),'-','')), pid, '2024-03-15', '187', 'GSK', 'SHG2024A',
       providerID, 'Intramuscular', 'Left deltoid', 'Completed', 0, NOW()
  FROM patient_data
 WHERE pid BETWEEN 100 AND 129 AND pid != 124 AND DOB <= DATE_SUB(CURDATE(), INTERVAL 50 YEAR);

-- Pneumovax-23 — for adults 65+
INSERT INTO `immunizations`
    (uuid, patient_id, administered_date, cvx_code, manufacturer, lot_number,
     administered_by_id, route, administration_site, completion_status, added_erroneously, update_date)
SELECT UNHEX(REPLACE(UUID(),'-','')), pid, '2023-06-15', '33', 'Merck', 'PN2023A',
       providerID, 'Intramuscular', 'Right deltoid', 'Completed', 0, NOW()
  FROM patient_data
 WHERE pid BETWEEN 100 AND 129 AND pid != 124 AND DOB <= DATE_SUB(CURDATE(), INTERVAL 65 YEAR);

-- =============================================================================
-- INSURANCE ASSIGNMENT PER PATIENT  (Sprint 12 / S12-14)
--
-- One primary insurance_data row per patient (30 patients including PID 124),
-- FK'd to one of the S12-03 insurance_companies (id range 200–207).
-- Distribution: Medicare for 65+, Medicaid CO for the SUD patient + 2 young
-- adults, Tricare for 1 (military), commercial mix (Aetna/BCBS/UHC/Cigna/
-- Kaiser) across the rest. subscriber_* fields use 'self' relationship —
-- the patient is their own subscriber.
-- =============================================================================

INSERT INTO `insurance_data`
    (uuid, type, provider, plan_name, policy_number, group_number,
     subscriber_fname, subscriber_lname, subscriber_DOB, subscriber_relationship,
     pid, date)
SELECT UNHEX(REPLACE(UUID(),'-','')), 'primary',
       CASE pd.pid
           WHEN 100 THEN 207 WHEN 101 THEN 200 WHEN 102 THEN 202 WHEN 103 THEN 201
           WHEN 104 THEN 203 WHEN 105 THEN 205 WHEN 106 THEN 204 WHEN 107 THEN 200
           WHEN 108 THEN 202 WHEN 109 THEN 201 WHEN 110 THEN 203 WHEN 111 THEN 204
           WHEN 112 THEN 200 WHEN 113 THEN 202 WHEN 114 THEN 201 WHEN 115 THEN 203
           WHEN 116 THEN 205 WHEN 117 THEN 204 WHEN 118 THEN 200 WHEN 119 THEN 202
           WHEN 120 THEN 206 WHEN 121 THEN 206 WHEN 122 THEN 201 WHEN 123 THEN 203
           WHEN 124 THEN 204 WHEN 125 THEN 206 WHEN 126 THEN 205 WHEN 127 THEN 200
           WHEN 128 THEN 202 WHEN 129 THEN 201
       END AS provider,
       CASE pd.pid
           WHEN 100 THEN 'Tricare Select'             WHEN 101 THEN 'Aetna Choice POS II'
           WHEN 102 THEN 'UHC Choice Plus'             WHEN 103 THEN 'BCBS CO Anthem PPO'
           WHEN 104 THEN 'Cigna PPO Plus'              WHEN 105 THEN 'Medicare Part B'
           WHEN 106 THEN 'Kaiser Permanente HMO'       WHEN 107 THEN 'Aetna Open Access'
           WHEN 108 THEN 'UHC Choice Plus'             WHEN 109 THEN 'BCBS CO Anthem PPO'
           WHEN 110 THEN 'Cigna LocalPlus'             WHEN 111 THEN 'Kaiser Permanente HMO'
           WHEN 112 THEN 'Aetna Choice POS II'         WHEN 113 THEN 'UHC Navigate'
           WHEN 114 THEN 'BCBS CO Anthem HMO'          WHEN 115 THEN 'Cigna Connect'
           WHEN 116 THEN 'Medicare Part B + Medigap F' WHEN 117 THEN 'Kaiser Permanente HMO'
           WHEN 118 THEN 'Aetna PPO'                   WHEN 119 THEN 'UHC Choice Plus'
           WHEN 120 THEN 'Health First Colorado'       WHEN 121 THEN 'Health First Colorado'
           WHEN 122 THEN 'BCBS CO Anthem PPO'          WHEN 123 THEN 'Cigna PPO Plus'
           WHEN 124 THEN 'Kaiser Permanente HMO'       WHEN 125 THEN 'Health First Colorado'
           WHEN 126 THEN 'Medicare Part B'             WHEN 127 THEN 'Aetna Choice POS II'
           WHEN 128 THEN 'UHC Choice Plus'             WHEN 129 THEN 'BCBS CO Anthem HMO'
       END AS plan_name,
       CONCAT('POL', LPAD(pd.pid, 7, '0')) AS policy_number,
       CONCAT('GRP-ZOOMLY-', FLOOR(100 + (pd.pid - 100) / 5)) AS group_number,
       pd.fname, pd.lname, pd.DOB, 'self',
       pd.pid, DATE_SUB(CURDATE(), INTERVAL 2 YEAR)
  FROM patient_data pd
 WHERE pd.pid BETWEEN 100 AND 129;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- VERIFICATION SUMMARY
-- =============================================================================
SELECT 'Seed complete.' AS status;

SELECT CONCAT(fname, ' ', lname) AS provider, id, abook_type
FROM users WHERE id IN (10,11,12,13,20,21,30,31) ORDER BY id;

SELECT c.pc_catname AS appt_category, COUNT(*) AS count
FROM openemr_postcalendar_events e
JOIN openemr_postcalendar_categories c ON e.pc_catid = c.pc_catid
WHERE e.pc_aid IN ('10','11','12','13')
GROUP BY c.pc_catname ORDER BY c.pc_catname;

SELECT COUNT(*) AS total_appointments FROM openemr_postcalendar_events WHERE pc_aid IN ('10','11','12','13');
SELECT COUNT(*) AS patient_count FROM patient_data WHERE pid BETWEEN 100 AND 129;
SELECT name, id FROM facility WHERE id = 1;
SELECT name AS insurance_company FROM insurance_companies WHERE id BETWEEN 200 AND 207 ORDER BY id;
