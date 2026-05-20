-- =============================================================================
-- 03 — STAFF (17 providers + 4 nurses + 4 MAs = 25 users)
-- =============================================================================

-- =============================================================================
-- PROVIDERS — 17 total, all Primary Care or Behavioral Health
--   IDs 10-13: original four (OConnor, Rodriguez, Miller, Thompson*)
--             * Thompson reframed from Cardiology to Internal Medicine
--   IDs 14-19, 22-27: 12 new providers (S12-21)
--   ID  21: Amy Martin (promoted RN → Family NP, S12-22)
--
-- Facility distribution: East=10, Mountain=4, West=2, Central=1
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`, `physician_type`, `npi`
) VALUES
-- East (id=2)
(10, UNHEX(REPLACE(UUID(), '-', '')), 'moconnor',         '', 1, 1,
 'Michael',  'OConnor',   'Dr.',  'Internal Medicine',    'michael.oconnor@example.org',  'michael.oconnor@example.org',
 2, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567890'),
(11, UNHEX(REPLACE(UUID(), '-', '')), 'erodriguez',       '', 1, 1,
 'Elena',    'Rodriguez', 'Dr.',  'Family Medicine',      'elena.rodriguez@example.org',  'elena.rodriguez@example.org',
 2, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567891'),
(12, UNHEX(REPLACE(UUID(), '-', '')), 'amiller',          '', 1, 1,
 'Amelia',   'Miller',    'Dr.',  'Psychiatry',           'amelia.miller@example.org',    'amelia.miller@example.org',
 2, 1, 'physician', '2084P0800X', 'standard', 'standard', 'MD', '1234567892'),
(16, UNHEX(REPLACE(UUID(), '-', '')), 'michael.chen',     '', 1, 1,
 'Michael',  'Chen',      'Dr.',  'Internal Medicine',    'michael.chen@example.org',     'michael.chen@example.org',
 2, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567896'),
(17, UNHEX(REPLACE(UUID(), '-', '')), 'marcus.eriksson',  '', 1, 1,
 'Marcus',   'Eriksson',  'Dr.',  'Psychiatry',           'marcus.eriksson@example.org',  'marcus.eriksson@example.org',
 2, 1, 'physician', '2084P0800X', 'standard', 'standard', 'MD', '1234567897'),
(18, UNHEX(REPLACE(UUID(), '-', '')), 'yuki.tanaka',      '', 1, 1,
 'Yuki',     'Tanaka',    'LCSW', 'Clinical Social Work', 'yuki.tanaka@example.org',      'yuki.tanaka@example.org',
 2, 1, 'physician', '1041C0700X', 'standard', 'standard', 'LCSW', '1234567898'),
(19, UNHEX(REPLACE(UUID(), '-', '')), 'ethan.garcia',     '', 1, 1,
 'Ethan',    'Garcia',    'Dr.',  'Internal Medicine',    'ethan.garcia@example.org',     'ethan.garcia@example.org',
 2, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567899'),
(21, UNHEX(REPLACE(UUID(), '-', '')), 'amartin',          '', 1, 1,
 'Amy',      'Martin',    'NP',   'Family Medicine',      'amy.martin@example.org',       'amy.martin@example.org',
 2, 1, 'physician', '363LF0000X', 'standard', 'standard', 'FNP', '1234567906'),
(22, UNHEX(REPLACE(UUID(), '-', '')), 'lucas.johnson',    '', 1, 1,
 'Lucas',    'Johnson',   'Dr.',  'Addiction Medicine',   'lucas.johnson@example.org',    'lucas.johnson@example.org',
 2, 1, 'physician', '207RA0401X', 'standard', 'standard', 'MD', '1234567900'),
(25, UNHEX(REPLACE(UUID(), '-', '')), 'lisa.patel',       '', 1, 1,
 'Lisa',     'Patel',     'Dr.',  'Internal Medicine',    'lisa.patel@example.org',       'lisa.patel@example.org',
 2, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567903'),
-- Mountain (id=1)
(14, UNHEX(REPLACE(UUID(), '-', '')), 'jonathan.nelson',  '', 1, 1,
 'Jonathan', 'Nelson',    'Dr.',  'Family Medicine',      'jonathan.nelson@example.org',  'jonathan.nelson@example.org',
 1, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567894'),
(15, UNHEX(REPLACE(UUID(), '-', '')), 'priya.patel',      '', 1, 1,
 'Priya',    'Patel',     'NP',   'Psychiatric Nurse Practitioner', 'priya.patel@example.org', 'priya.patel@example.org',
 1, 1, 'physician', '363LP0808X', 'standard', 'standard', 'NP', '1234567895'),
(26, UNHEX(REPLACE(UUID(), '-', '')), 'hiroshi.tanaka',   '', 1, 1,
 'Hiroshi',  'Tanaka',    'Dr.',  'Family Medicine',      'hiroshi.tanaka@example.org',   'hiroshi.tanaka@example.org',
 1, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567904'),
(27, UNHEX(REPLACE(UUID(), '-', '')), 'david.thompson',   '', 1, 1,
 'David',    'Thompson',  'Dr.',  'Internal Medicine',    'david.thompson@example.org',   'david.thompson@example.org',
 1, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567905'),
-- West (id=4)
(13, UNHEX(REPLACE(UUID(), '-', '')), 'mthompson',        '', 1, 1,
 'Marcus',   'Thompson',  'Dr.',  'Internal Medicine',    'marcus.thompson@example.org',  'marcus.thompson@example.org',
 4, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567893'),
(23, UNHEX(REPLACE(UUID(), '-', '')), 'dave.anderson',    '', 1, 1,
 'Dave',     'Anderson',  'Dr.',  'Family Medicine',      'dave.anderson@example.org',    'dave.anderson@example.org',
 4, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567901'),
-- Central (id=5)
(24, UNHEX(REPLACE(UUID(), '-', '')), 'joe.smith',        '', 1, 1,
 'Joe',      'Smith',     'Dr.',  'Family Medicine',      'joe.smith@example.org',        'joe.smith@example.org',
 5, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567902');

-- =============================================================================
-- NURSES — 1 per facility (Lee at Mountain; 3 new at East/Central/West)
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`
) VALUES
(20, UNHEX(REPLACE(UUID(), '-', '')), 'blee',            '', 0, 1,
 'Bill',  'Lee',       'RN', 'Nursing', 'bill.lee@example.org',        'bill.lee@example.org',
 1, 0, 'nurse', '163W00000X', 'standard', 'standard'),
(32, UNHEX(REPLACE(UUID(), '-', '')), 'sarah.martinez',  '', 0, 1,
 'Sarah', 'Martinez',  'RN', 'Nursing', 'sarah.martinez@example.org',  'sarah.martinez@example.org',
 2, 0, 'nurse', '163W00000X', 'standard', 'standard'),
(33, UNHEX(REPLACE(UUID(), '-', '')), 'ken.watanabe',    '', 0, 1,
 'Ken',   'Watanabe',  'RN', 'Nursing', 'ken.watanabe@example.org',    'ken.watanabe@example.org',
 5, 0, 'nurse', '163W00000X', 'standard', 'standard'),
(34, UNHEX(REPLACE(UUID(), '-', '')), 'maria.rodriguez', '', 0, 1,
 'Maria', 'Rodriguez', 'RN', 'Nursing', 'maria.rodriguez@example.org', 'maria.rodriguez@example.org',
 4, 0, 'nurse', '163W00000X', 'standard', 'standard');

-- =============================================================================
-- MEDICAL ASSISTANTS — IDs 30-31
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`
) VALUES
(30, UNHEX(REPLACE(UUID(), '-', '')), 'bwilliams',    '', 0, 1,
 'Ben',    'Williams', 'MA', 'Medical Assistant', 'ben.williams@example.org',    'ben.williams@example.org',
 1, 0, 'med_asst', '356AM0700X', 'standard', 'standard'),
(31, UNHEX(REPLACE(UUID(), '-', '')), 'hsong',        '', 0, 1,
 'Hana',   'Song',     'MA', 'Medical Assistant', 'hana.song@example.org',       'hana.song@example.org',
 2, 0, 'med_asst', '356AM0700X', 'standard', 'standard'),
(35, UNHEX(REPLACE(UUID(), '-', '')), 'emma.wilson',  '', 0, 1,
 'Emma',   'Wilson',   'MA', 'Medical Assistant', 'emma.wilson@example.org',     'emma.wilson@example.org',
 5, 0, 'med_asst', '356AM0700X', 'standard', 'standard'),
(36, UNHEX(REPLACE(UUID(), '-', '')), 'cheryl.lewis', '', 0, 1,
 'Cheryl', 'Lewis',    'MA', 'Medical Assistant', 'cheryl.lewis@example.org',    'cheryl.lewis@example.org',
 4, 0, 'med_asst', '356AM0700X', 'standard', 'standard');

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
(31, 'hsong',      '$2y$12$9jMeSDX.LGvUw61ENWAXyenoSGfXrQ4gMS2rI6klVr0kdF5LP6kxK', NOW()),
-- New providers + new support staff — bcrypt of ZoomDem0! reused
(14, 'jonathan.nelson', '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(15, 'priya.patel',     '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(16, 'michael.chen',    '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(17, 'marcus.eriksson', '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(18, 'yuki.tanaka',     '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(19, 'ethan.garcia',    '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(22, 'lucas.johnson',   '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(23, 'dave.anderson',   '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(24, 'joe.smith',       '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(25, 'lisa.patel',      '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(26, 'hiroshi.tanaka',  '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(27, 'david.thompson',  '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(32, 'sarah.martinez',  '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(33, 'ken.watanabe',    '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(34, 'maria.rodriguez', '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(35, 'emma.wilson',     '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW()),
(36, 'cheryl.lewis',    '$2y$12$HeGh8SpI7B2Lv/7yhXhzteJ6xssabt0yZowdRy2346gH1JpWz67p2', NOW());

-- =============================================================================
-- ACL
-- =============================================================================

INSERT IGNORE INTO gacl_aro (id, section_value, value, order_value, name, hidden) VALUES
-- Original 8 staff
(12, 'users', 'moconnor',        10, 'Michael OConnor',  0),
(13, 'users', 'amiller',         10, 'Amelia Miller',    0),
(14, 'users', 'mthompson',       10, 'Marcus Thompson',  0),
(15, 'users', 'blee',            10, 'Bill Lee',         0),
(16, 'users', 'amartin',         10, 'Amy Martin',       0),
(17, 'users', 'bwilliams',       10, 'Ben Williams',     0),
(18, 'users', 'hsong',           10, 'Hana Song',        0),
(19, 'users', 'erodriguez',      10, 'Elena Rodriguez',  0),
-- New providers
(20, 'users', 'jonathan.nelson', 10, 'Jonathan Nelson',  0),
(21, 'users', 'priya.patel',     10, 'Priya Patel',      0),
(22, 'users', 'michael.chen',    10, 'Michael Chen',     0),
(23, 'users', 'marcus.eriksson', 10, 'Marcus Eriksson',  0),
(24, 'users', 'yuki.tanaka',     10, 'Yuki Tanaka',      0),
(25, 'users', 'ethan.garcia',    10, 'Ethan Garcia',     0),
(26, 'users', 'lucas.johnson',   10, 'Lucas Johnson',    0),
(27, 'users', 'dave.anderson',   10, 'Dave Anderson',    0),
(28, 'users', 'joe.smith',       10, 'Joe Smith',        0),
(29, 'users', 'lisa.patel',      10, 'Lisa Patel',       0),
(30, 'users', 'hiroshi.tanaka',  10, 'Hiroshi Tanaka',   0),
(31, 'users', 'david.thompson',  10, 'David Thompson',   0),
-- New support staff
(32, 'users', 'sarah.martinez',  10, 'Sarah Martinez',   0),
(33, 'users', 'ken.watanabe',    10, 'Ken Watanabe',     0),
(34, 'users', 'maria.rodriguez', 10, 'Maria Rodriguez',  0),
(35, 'users', 'emma.wilson',     10, 'Emma Wilson',      0),
(36, 'users', 'cheryl.lewis',    10, 'Cheryl Lewis',     0);

-- group_id 13 = Physicians, 12 = Clinicians
-- Amy Martin (aro 16) moves from Clinicians to Physicians (promoted to FNP)
INSERT IGNORE INTO gacl_groups_aro_map (group_id, aro_id) VALUES
-- Original providers + Amy promoted to Physicians
(13,12),(13,13),(13,14),(13,16),(13,19),
-- New providers → Physicians
(13,20),(13,21),(13,22),(13,23),(13,24),(13,25),(13,26),(13,27),(13,28),(13,29),(13,30),(13,31),
-- Support staff → Clinicians
(12,15),(12,17),(12,18),(12,32),(12,33),(12,34),(12,35),(12,36);

INSERT IGNORE INTO groups (name, user) VALUES
-- Providers (Physicians group)
('Physicians', 'moconnor'),
('Physicians', 'erodriguez'),
('Physicians', 'amiller'),
('Physicians', 'mthompson'),
('Physicians', 'amartin'),
('Physicians', 'jonathan.nelson'),
('Physicians', 'priya.patel'),
('Physicians', 'michael.chen'),
('Physicians', 'marcus.eriksson'),
('Physicians', 'yuki.tanaka'),
('Physicians', 'ethan.garcia'),
('Physicians', 'lucas.johnson'),
('Physicians', 'dave.anderson'),
('Physicians', 'joe.smith'),
('Physicians', 'lisa.patel'),
('Physicians', 'hiroshi.tanaka'),
('Physicians', 'david.thompson'),
-- Support staff (Clinicians group)
('Clinicians', 'blee'),
('Clinicians', 'bwilliams'),
('Clinicians', 'hsong'),
('Clinicians', 'sarah.martinez'),
('Clinicians', 'ken.watanabe'),
('Clinicians', 'maria.rodriguez'),
('Clinicians', 'emma.wilson'),
('Clinicians', 'cheryl.lewis');

