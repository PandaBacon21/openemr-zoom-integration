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
