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
-- Appointment types picked up by Zoomly:
--   zoom-telehealth, new-patient-zoom
--
-- Appointment types dropped by Zoomly filter:
--   new-patient-in-person, phone-consult, in-person
--
-- Future: replace static appointments with a dynamic random generator script
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- Widen pc_website to accommodate full Zoom start URLs with zak tokens
ALTER TABLE openemr_postcalendar_events MODIFY pc_website VARCHAR(1024);

-- =============================================================================
-- FACILITY
-- Override default facility (id=3) to hide it, create Zoomly Medical Center
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

-- Move admin user to facility 1
UPDATE `users` SET `facility_id` = 1 WHERE `id` = 1;

-- =============================================================================
-- PROVIDERS (physicians)
-- IDs 10-13
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`, `physician_type`, `npi`
) VALUES
(10, UNHEX(REPLACE(UUID(), '-', '')), 'moconnor', '', 1, 1,
 'Michael', 'OConnor', 'Dr.', 'Internal Medicine', 'josh.aiken@zoomineer.com', 'josh.aiken@zoomineer.com',
 1, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567890'),

(11, UNHEX(REPLACE(UUID(), '-', '')), 'erodriguez', '', 1, 1,
 'Elena', 'Rodriguez', 'Dr.', 'Family Medicine', 'josh.aiken@zoomineer.com', 'josh.aiken@zoomineer.com',
 1, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567891'),

(12, UNHEX(REPLACE(UUID(), '-', '')), 'amiller', '', 1, 1,
 'Amelia', 'Miller', 'Dr.', 'Psychiatry', 'josh.aiken@zoomineer.com', 'josh.aiken@zoomineer.com',
 1, 1, 'physician', '2084P0800X', 'standard', 'standard', 'MD', '1234567892'),

(13, UNHEX(REPLACE(UUID(), '-', '')), 'mthompson', '', 1, 1,
 'Marcus', 'Thompson', 'Dr.', 'Cardiology', 'josh.aiken@zoomineer.com', 'josh.aiken@zoomineer.com',
 1, 1, 'physician', '207RC0000X', 'standard', 'standard', 'MD', '1234567893');

-- =============================================================================
-- NURSES
-- IDs 20-21
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`
) VALUES
(20, UNHEX(REPLACE(UUID(), '-', '')), 'blee', '', 0, 1,
 'Bill', 'Lee', 'RN', 'Nursing', 'josh.aiken@zoomineer.com', 'josh.aiken@zoomineer.com',
 1, 0, 'nurse', '163W00000X', 'standard', 'standard'),

(21, UNHEX(REPLACE(UUID(), '-', '')), 'amartin', '', 0, 1,
 'Amy', 'Martin', 'RN', 'Nursing', 'josh.aiken@zoomineer.com', 'josh.aiken@zoomineer.com',
 1, 0, 'nurse', '163W00000X', 'standard', 'standard');

-- =============================================================================
-- MEDICAL ASSISTANTS
-- IDs 30-31
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`
) VALUES
(30, UNHEX(REPLACE(UUID(), '-', '')), 'bwilliams', '', 0, 1,
 'Ben', 'Williams', 'MA', 'Medical Assistant', 'josh.aiken@zoomineer.com', 'josh.aiken@zoomineer.com',
 1, 0, 'med_asst', '356AM0700X', 'standard', 'standard'),

(31, UNHEX(REPLACE(UUID(), '-', '')), 'hsong', '', 0, 1,
 'Hana', 'Song', 'MA', 'Medical Assistant', 'josh.aiken@zoomineer.com', 'josh.aiken@zoomineer.com',
 1, 0, 'med_asst', '356AM0700X', 'standard', 'standard');


-- =============================================================================
-- STAFF SECURE PASSWORDS (ZoomDem0!)
-- OpenEMR 8.0 uses users_secure for authentication, not users.password
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


-- gacl_aro (explicit IDs required — no auto_increment)
INSERT IGNORE INTO gacl_aro (id, section_value, value, order_value, name, hidden) VALUES
(12, 'users', 'moconnor',   10, 'Michael OConnor',  0),
(13, 'users', 'amiller',    10, 'Amelia Miller',    0),
(14, 'users', 'mthompson',  10, 'Marcus Thompson',  0),
(15, 'users', 'blee',       10, 'Bill Lee',         0),
(16, 'users', 'amartin',    10, 'Amy Martin',       0),
(17, 'users', 'bwilliams',  10, 'Ben Williams',     0),
(18, 'users', 'hsong',      10, 'Hana Song',        0),
(19, 'users', 'erodriguez', 10, 'Elena Rodriguez',  0);

-- gacl_groups_aro_map
INSERT IGNORE INTO gacl_groups_aro_map (group_id, aro_id) VALUES
(13,12),(13,19),(13,13),(13,14),
(12,15),(12,16),(12,17),(12,18);

-- groups
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
-- APPOINTMENT TYPES
-- =============================================================================

INSERT INTO `openemr_postcalendar_categories` (
    `pc_catname`, `pc_catcolor`, `pc_catdesc`,
    `pc_duration`, `pc_cattype`, `pc_active`, `pc_seq`,
    `pc_recurrtype`, `pc_recurrfreq`, `pc_end_date_flag`,
    `pc_end_date_freq`, `pc_end_all_day`, `pc_dailylimit`,
    `aco_spec`, `pc_constant_id`
) VALUES
('zoom-telehealth', '#00053D', 'Zoom telehealth video appointment — established patient',
 1800, 0, 1, 10, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'zoom_telehealth'),

('new-patient-zoom', '#b4d0f8', 'New patient intake via Zoom video',
 2700, 0, 1, 20, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'new_patient_zoom'),

('new-patient-in-person', '#888888', 'New patient intake in office',
 2700, 0, 1, 30, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'new_patient_in_person'),

('phone-consult', '#F5A623', 'Phone consultation — no video',
 900, 0, 1, 40, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'phone_consult'),

('in-person', '#E07B39', 'Established patient in-office visit',
 1800, 0, 1, 50, 0, 0, 0, 0, 0, 0, 'encounters|notes', 'in_person');

SET @zoom_telehealth_catid  = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'zoom-telehealth');
SET @new_patient_zoom_catid = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'new-patient-zoom');
SET @new_patient_ip_catid   = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'new-patient-in-person');
SET @phone_consult_catid    = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'phone-consult');
SET @in_person_catid        = (SELECT pc_catid FROM openemr_postcalendar_categories WHERE pc_catname = 'in-person');

-- Serialized recurrspec and location used by OpenEMR calendar (required for display)
SET @recurrspec = 'a:6:{s:17:"event_repeat_freq";s:1:"0";s:22:"event_repeat_freq_type";s:1:"0";s:19:"event_repeat_on_num";s:1:"1";s:19:"event_repeat_on_day";s:1:"0";s:20:"event_repeat_on_freq";s:1:"0";s:6:"exdate";s:0:"";}';
SET @location   = 'a:6:{s:14:"event_location";s:0:"";s:13:"event_street1";s:0:"";s:13:"event_street2";s:0:"";s:10:"event_city";s:0:"";s:11:"event_state";s:0:"";s:12:"event_postal";s:0:"";}';


-- =============================================================================
-- PATIENTS
-- PIDs 100-129 (30 patients)
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
 '303-555-0101', 'josh.aiken@zoomineer.com', 10, '100', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(101, UNHEX(REPLACE(UUID(), '-', '')), 'Sofia', 'Reyes', 'M', 'Ms.',
 '1990-07-22', 'Female', 'single', '88 Maple Avenue', 'Denver', 'CO', '80202', 'USA',
 '303-555-0102', 'josh.aiken@zoomineer.com', 11, '101', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(102, UNHEX(REPLACE(UUID(), '-', '')), 'David', 'Kim', '', 'Mr.',
 '1965-11-05', 'Male', 'married', '209 Oak Lane', 'Denver', 'CO', '80203', 'USA',
 '303-555-0103', 'josh.aiken@zoomineer.com', 13, '102', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(103, UNHEX(REPLACE(UUID(), '-', '')), 'Rachel', 'Nguyen', 'T', 'Ms.',
 '1985-02-28', 'Female', 'single', '56 Pine Road', 'Denver', 'CO', '80204', 'USA',
 '303-555-0104', 'josh.aiken@zoomineer.com', 12, '103', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(104, UNHEX(REPLACE(UUID(), '-', '')), 'Carlos', 'Mendez', 'R', 'Mr.',
 '1972-09-17', 'Male', 'married', '731 Cedar Blvd', 'Denver', 'CO', '80205', 'USA',
 '303-555-0105', 'josh.aiken@zoomineer.com', 10, '104', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(105, UNHEX(REPLACE(UUID(), '-', '')), 'Linda', 'Patel', '', 'Mrs.',
 '1958-06-30', 'Female', 'married', '1020 Birch Court', 'Denver', 'CO', '80206', 'USA',
 '303-555-0106', 'josh.aiken@zoomineer.com', 11, '105', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(106, UNHEX(REPLACE(UUID(), '-', '')), 'Ethan', 'Brooks', 'J', 'Mr.',
 '1995-04-11', 'Male', 'single', '348 Walnut Street', 'Denver', 'CO', '80207', 'USA',
 '303-555-0107', 'josh.aiken@zoomineer.com', 12, '106', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(107, UNHEX(REPLACE(UUID(), '-', '')), 'Maria', 'Chen', 'L', 'Ms.',
 '1982-12-03', 'Female', 'divorced', '675 Spruce Way', 'Denver', 'CO', '80208', 'USA',
 '303-555-0108', 'josh.aiken@zoomineer.com', 13, '107', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(108, UNHEX(REPLACE(UUID(), '-', '')), 'Thomas', 'Walsh', 'P', 'Mr.',
 '1969-08-19', 'Male', 'married', '512 Hickory Drive', 'Denver', 'CO', '80209', 'USA',
 '303-555-0109', 'josh.aiken@zoomineer.com', 10, '108', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(109, UNHEX(REPLACE(UUID(), '-', '')), 'Aisha', 'Johnson', 'K', 'Ms.',
 '1993-01-25', 'Female', 'single', '890 Willow Lane', 'Denver', 'CO', '80210', 'USA',
 '303-555-0110', 'josh.aiken@zoomineer.com', 11, '109', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(110, UNHEX(REPLACE(UUID(), '-', '')), 'Brian', 'Foster', 'E', 'Mr.',
 '1980-05-12', 'Male', 'married', '23 Aspen Court', 'Denver', 'CO', '80211', 'USA',
 '303-555-0111', 'josh.aiken@zoomineer.com', 12, '110', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(111, UNHEX(REPLACE(UUID(), '-', '')), 'Yuki', 'Tanaka', '', 'Ms.',
 '1997-08-03', 'Female', 'single', '67 Larimer Street', 'Denver', 'CO', '80212', 'USA',
 '303-555-0112', 'josh.aiken@zoomineer.com', 13, '111', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(112, UNHEX(REPLACE(UUID(), '-', '')), 'Omar', 'Hassan', 'A', 'Mr.',
 '1975-03-29', 'Male', 'married', '140 Colfax Ave', 'Denver', 'CO', '80213', 'USA',
 '303-555-0113', 'josh.aiken@zoomineer.com', 10, '112', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(113, UNHEX(REPLACE(UUID(), '-', '')), 'Patricia', 'Monroe', 'J', 'Mrs.',
 '1962-11-17', 'Female', 'married', '555 Broadway', 'Denver', 'CO', '80214', 'USA',
 '303-555-0114', 'josh.aiken@zoomineer.com', 11, '113', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(114, UNHEX(REPLACE(UUID(), '-', '')), 'Kevin', 'Park', '', 'Mr.',
 '1988-06-22', 'Male', 'single', '789 Speer Blvd', 'Denver', 'CO', '80215', 'USA',
 '303-555-0115', 'josh.aiken@zoomineer.com', 12, '114', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(115, UNHEX(REPLACE(UUID(), '-', '')), 'Fatima', 'Ali', 'Z', 'Ms.',
 '1991-09-14', 'Female', 'single', '321 Downing Street', 'Denver', 'CO', '80216', 'USA',
 '303-555-0116', 'josh.aiken@zoomineer.com', 13, '115', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(116, UNHEX(REPLACE(UUID(), '-', '')), 'Gregory', 'Stone', 'B', 'Mr.',
 '1955-02-08', 'Male', 'widowed', '44 Monaco Pkwy', 'Denver', 'CO', '80217', 'USA',
 '303-555-0117', 'josh.aiken@zoomineer.com', 10, '116', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(117, UNHEX(REPLACE(UUID(), '-', '')), 'Nadia', 'Okafor', 'C', 'Ms.',
 '1986-04-30', 'Female', 'single', '888 York Street', 'Denver', 'CO', '80218', 'USA',
 '303-555-0118', 'josh.aiken@zoomineer.com', 11, '117', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(118, UNHEX(REPLACE(UUID(), '-', '')), 'Samuel', 'Wright', 'D', 'Mr.',
 '1970-07-16', 'Male', 'married', '202 Pearl Street', 'Denver', 'CO', '80219', 'USA',
 '303-555-0119', 'josh.aiken@zoomineer.com', 12, '118', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(119, UNHEX(REPLACE(UUID(), '-', '')), 'Claire', 'Bennett', 'F', 'Ms.',
 '1994-12-01', 'Female', 'single', '1100 Grant Street', 'Denver', 'CO', '80220', 'USA',
 '303-555-0120', 'josh.aiken@zoomineer.com', 13, '119', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(120, UNHEX(REPLACE(UUID(), '-', '')), 'Andre', 'Dubois', '', 'Mr.',
 '1983-10-25', 'Male', 'married', '77 Logan Street', 'Denver', 'CO', '80221', 'USA',
 '303-555-0121', 'josh.aiken@zoomineer.com', 10, '120', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(121, UNHEX(REPLACE(UUID(), '-', '')), 'Priya', 'Sharma', 'N', 'Ms.',
 '1992-03-18', 'Female', 'single', '456 Humboldt Street', 'Denver', 'CO', '80222', 'USA',
 '303-555-0122', 'josh.aiken@zoomineer.com', 11, '121', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(122, UNHEX(REPLACE(UUID(), '-', '')), 'Robert', 'Castillo', 'M', 'Mr.',
 '1967-08-09', 'Male', 'married', '933 Josephine Street', 'Denver', 'CO', '80223', 'USA',
 '303-555-0123', 'josh.aiken@zoomineer.com', 12, '122', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(123, UNHEX(REPLACE(UUID(), '-', '')), 'Hannah', 'Scott', 'R', 'Ms.',
 '1989-05-27', 'Female', 'single', '215 Fillmore Street', 'Denver', 'CO', '80224', 'USA',
 '303-555-0124', 'josh.aiken@zoomineer.com', 13, '123', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(124, UNHEX(REPLACE(UUID(), '-', '')), 'Derek', 'Nguyen', 'T', 'Mr.',
 '1976-01-14', 'Male', 'divorced', '678 Gilpin Street', 'Denver', 'CO', '80225', 'USA',
 '303-555-0125', 'josh.aiken@zoomineer.com', 10, '124', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(125, UNHEX(REPLACE(UUID(), '-', '')), 'Isabelle', 'Martin', 'A', 'Ms.',
 '1998-11-03', 'Female', 'single', '342 Clarkson Street', 'Denver', 'CO', '80226', 'USA',
 '303-555-0126', 'josh.aiken@zoomineer.com', 11, '125', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(126, UNHEX(REPLACE(UUID(), '-', '')), 'Jerome', 'Washington', 'L', 'Mr.',
 '1960-06-20', 'Male', 'married', '119 Corona Street', 'Denver', 'CO', '80227', 'USA',
 '303-555-0127', 'josh.aiken@zoomineer.com', 12, '126', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(127, UNHEX(REPLACE(UUID(), '-', '')), 'Mei', 'Liu', '', 'Ms.',
 '1987-09-11', 'Female', 'married', '87 Emerson Street', 'Denver', 'CO', '80228', 'USA',
 '303-555-0128', 'josh.aiken@zoomineer.com', 13, '127', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(128, UNHEX(REPLACE(UUID(), '-', '')), 'Tyler', 'Hughes', 'W', 'Mr.',
 '1996-02-28', 'Male', 'single', '504 Vine Street', 'Denver', 'CO', '80229', 'USA',
 '303-555-0129', 'josh.aiken@zoomineer.com', 10, '128', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),

(129, UNHEX(REPLACE(UUID(), '-', '')), 'Amara', 'Diallo', 'S', 'Ms.',
 '1984-07-07', 'Female', 'single', '261 Humboldt Street', 'Denver', 'CO', '80230', 'USA',
 '303-555-0130', 'josh.aiken@zoomineer.com', 11, '129', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW());


-- =============================================================================
-- PATIENT PORTAL ACCESS
-- Enable portal access for demo patients 100-105
-- Username: firstname.lastname, Password: pass
-- =============================================================================

-- Enable Patient Portal
UPDATE globals SET gl_value = '1' WHERE gl_name = 'portal_onsite_two_enable';
-- Disable email-as-username so we can use firstname.lastname format
UPDATE globals SET gl_value = '0' WHERE gl_name = 'use_email_for_portal_username';
-- Set patient portal URL
UPDATE globals SET gl_value = 'https://openemr-dev.theloosemoose.us/portal' WHERE gl_name = 'portal_onsite_two_address';

-- Enable portal access on patient_data rows
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'james.harrison' WHERE pid = 100;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'sofia.reyes'    WHERE pid = 101;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'david.kim'      WHERE pid = 102;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'rachel.nguyen'  WHERE pid = 103;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'carlos.mendez'  WHERE pid = 104;
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'linda.patel'    WHERE pid = 105;

-- Create portal credentials (password: 'ZoomDem0!', bcrypt hashed)
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
-- 1 appointment per provider per day for 14 days
-- 4 providers x 14 days = 56 appointments
-- Mix of zoom-telehealth, new-patient-zoom (picked up) and
-- in-person, phone-consult, new-patient-in-person (dropped)
-- spread naturally through the schedule
--
-- Provider IDs:  10=OConnor, 11=Rodriguez, 12=Miller, 13=Thompson
-- Patient pool:  PIDs 100-129 (30 patients), cycling through
--
-- Required fields for calendar display (learned from UI inspection):
--   pc_eventstatus = 1
--   pc_apptstatus  = '-'  (none/unset)
--   pc_endDate     = '0000-00-00'
--   pc_informant   = 1
--   pc_recurrspec  = serialized PHP array
--   pc_location    = serialized PHP array
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
(@zoom_telehealth_catid, 0, '10', '100', 'Zoom Telehealth', NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_zoom_catid, 0, '11', '101', 'New Patient Zoom', NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '09:00:00', '09:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '12', '102', 'In-Person Visit', NOW(), 'Established patient in office',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '13', '103', 'Zoom Telehealth', NOW(), 'Cardiac follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 1 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 2
-- =============================================================================
(@in_person_catid, 0, '10', '104', 'In-Person Visit', NOW(), 'Routine in-office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '11', '105', 'Zoom Telehealth', NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@phone_consult_catid, 0, '12', '106', 'Phone Consult', NOW(), 'Brief phone consultation',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '09:00:00', '09:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_zoom_catid, 0, '13', '107', 'New Patient Zoom', NOW(), 'New cardiology patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 2 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 3
-- =============================================================================
(@zoom_telehealth_catid, 0, '10', '108', 'Zoom Telehealth', NOW(), 'Medication review via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:30:00', '10:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_ip_catid, 0, '11', '109', 'New Patient In-Person', NOW(), 'New patient in-office intake',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '08:00:00', '08:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '12', '110', 'Zoom Telehealth', NOW(), 'Mental health check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '13', '111', 'In-Person Visit', NOW(), 'Follow-up in office',
 DATE(DATE_ADD(NOW(), INTERVAL 3 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 4
-- =============================================================================
(@new_patient_zoom_catid, 0, '10', '112', 'New Patient Zoom', NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '10:00:00', '10:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '11', '113', 'In-Person Visit', NOW(), 'Routine in-office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '12', '114', 'Zoom Telehealth', NOW(), 'Therapy session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@phone_consult_catid, 0, '13', '115', 'Phone Consult', NOW(), 'Brief phone consultation',
 DATE(DATE_ADD(NOW(), INTERVAL 4 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '11:00:00', '11:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 5
-- =============================================================================
(@zoom_telehealth_catid, 0, '10', '116', 'Zoom Telehealth', NOW(), 'Annual wellness via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '11', '117', 'Zoom Telehealth', NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_ip_catid, 0, '12', '118', 'New Patient In-Person', NOW(), 'New patient in-office intake',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '08:00:00', '08:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '13', '119', 'Zoom Telehealth', NOW(), 'Post-procedure follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 5 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 6
-- =============================================================================
(@in_person_catid, 0, '10', '120', 'In-Person Visit', NOW(), 'Established patient in office',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:30:00', '11:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_zoom_catid, 0, '11', '121', 'New Patient Zoom', NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '09:00:00', '09:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '12', '122', 'Zoom Telehealth', NOW(), 'Psychiatric evaluation via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '13:00:00', '13:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '13', '123', 'In-Person Visit', NOW(), 'Cardiology in-office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 6 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:30:00', '10:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 7
-- =============================================================================
(@zoom_telehealth_catid, 0, '10', '124', 'Zoom Telehealth', NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@phone_consult_catid, 0, '11', '125', 'Phone Consult', NOW(), 'Brief phone consultation',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '12:00:00', '12:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_zoom_catid, 0, '12', '126', 'New Patient Zoom', NOW(), 'New patient psychiatric intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '10:00:00', '10:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '13', '127', 'Zoom Telehealth', NOW(), 'Cardiac check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 7 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:30:00', '15:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 8
-- =============================================================================
(@new_patient_ip_catid, 0, '10', '128', 'New Patient In-Person', NOW(), 'New patient in-office intake',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '08:00:00', '08:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '11', '129', 'Zoom Telehealth', NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '12', '100', 'In-Person Visit', NOW(), 'Established patient in office',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '13', '101', 'Zoom Telehealth', NOW(), 'Cardiology consultation via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 8 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '15:00:00', '15:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 9
-- =============================================================================
(@zoom_telehealth_catid, 0, '10', '102', 'Zoom Telehealth', NOW(), 'Annual wellness via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '11', '103', 'In-Person Visit', NOW(), 'Routine in-office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '12', '104', 'Zoom Telehealth', NOW(), 'Therapy session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_zoom_catid, 0, '13', '105', 'New Patient Zoom', NOW(), 'New cardiology patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 9 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '14:00:00', '14:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 10
-- =============================================================================
(@phone_consult_catid, 0, '10', '106', 'Phone Consult', NOW(), 'Brief phone consultation',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '08:30:00', '08:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '11', '107', 'Zoom Telehealth', NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:30:00', '10:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_zoom_catid, 0, '12', '108', 'New Patient Zoom', NOW(), 'New patient psychiatric intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '13:00:00', '13:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '13', '109', 'Zoom Telehealth', NOW(), 'Post-procedure follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 10 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 11
-- =============================================================================
(@zoom_telehealth_catid, 0, '10', '110', 'Zoom Telehealth', NOW(), 'Medication review via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_ip_catid, 0, '11', '111', 'New Patient In-Person', NOW(), 'New patient in-office intake',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '08:00:00', '08:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '12', '112', 'In-Person Visit', NOW(), 'Established patient in office',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '13', '113', 'Zoom Telehealth', NOW(), 'Cardiac check-in via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 11 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 12
-- =============================================================================
(@in_person_catid, 0, '10', '114', 'In-Person Visit', NOW(), 'Routine in-office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '11', '115', 'Zoom Telehealth', NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:30:00', '12:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '12', '116', 'Zoom Telehealth', NOW(), 'Psychiatric evaluation via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:30:00', '11:00:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@new_patient_zoom_catid, 0, '13', '117', 'New Patient Zoom', NOW(), 'New cardiology patient via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 12 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '15:00:00', '15:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 13
-- =============================================================================
(@zoom_telehealth_catid, 0, '10', '118', 'Zoom Telehealth', NOW(), 'Annual wellness via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '11', '119', 'In-Person Visit', NOW(), 'Established patient in office',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '10:00:00', '10:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@phone_consult_catid, 0, '12', '120', 'Phone Consult', NOW(), 'Brief phone consultation',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 900, 0, 0, @recurrspec, @location,
 '12:00:00', '12:15:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '13', '121', 'Zoom Telehealth', NOW(), 'Cardiac follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 13 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

-- =============================================================================
-- DAY 14
-- =============================================================================
(@new_patient_zoom_catid, 0, '10', '122', 'New Patient Zoom', NOW(), 'New patient intake via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 2700, 0, 0, @recurrspec, @location,
 '10:00:00', '10:45:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '11', '123', 'Zoom Telehealth', NOW(), 'Follow-up via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '09:00:00', '09:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@zoom_telehealth_catid, 0, '12', '124', 'Zoom Telehealth', NOW(), 'Therapy session via Zoom',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '14:00:00', '14:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', ''))),

(@in_person_catid, 0, '13', '125', 'In-Person Visit', NOW(), 'Cardiology in-office visit',
 DATE(DATE_ADD(NOW(), INTERVAL 14 DAY)), '0000-00-00', 1800, 0, 0, @recurrspec, @location,
 '11:00:00', '11:30:00', 0, '-', 1, 1, 1, 1, 1, 'NO', 'NO', UNHEX(REPLACE(UUID(), '-', '')));

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- VERIFICATION SUMMARY
-- =============================================================================
SELECT 'Seed complete.' AS status;

SELECT CONCAT(fname, ' ', lname) AS provider, id, abook_type
FROM users WHERE id IN (10,11,12,13,20,21,30,31) ORDER BY id;

SELECT pc_catname, pc_catid, pc_duration,
       CASE WHEN pc_catname IN ('zoom-telehealth','new-patient-zoom')
            THEN 'PICKED UP' ELSE 'DROPPED' END AS zoomly_filter
FROM openemr_postcalendar_categories
WHERE pc_catname IN ('zoom-telehealth','new-patient-zoom','new-patient-in-person','phone-consult','in-person')
ORDER BY pc_seq;

SELECT c.pc_catname AS appt_type, COUNT(*) AS count,
       CASE WHEN c.pc_catname IN ('zoom-telehealth','new-patient-zoom')
            THEN 'PICKED UP' ELSE 'DROPPED' END AS zoomly_filter
FROM openemr_postcalendar_events e
JOIN openemr_postcalendar_categories c ON e.pc_catid = c.pc_catid
WHERE c.pc_catname IN ('zoom-telehealth','new-patient-zoom','new-patient-in-person','phone-consult','in-person')
GROUP BY c.pc_catname ORDER BY c.pc_seq;

SELECT COUNT(*) AS patient_count FROM patient_data WHERE pid BETWEEN 100 AND 129;
SELECT name, id FROM facility WHERE id = 1;