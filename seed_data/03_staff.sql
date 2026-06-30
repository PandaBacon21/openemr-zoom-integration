-- =============================================================================
-- 03 — STAFF (18 patient-panel providers + 4 nurses + 4 MAs = 26 users)
-- =============================================================================

-- =============================================================================
-- PROVIDERS — 18 total, all Primary Care, Behavioral Health, or provider-level RN
--   IDs 10-13: original four (OConnor, Rodriguez, Miller, Thompson*)
--             * Thompson reframed from Cardiology to Internal Medicine
--   IDs 14-19, 22-27: 12 new providers (S12-21)
--   ID  21: Amy Martin (promoted RN → Family NP, S12-22)
--   ID  37: Sarah Chen (provider-level RN panel owner)
--
-- Facility distribution by current facility_id: CO=4, MA=11, CA=1, MO=2.
-- The facility_id value on each row is the source of truth for region/panel mapping.
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`, `physician_type`, `npi`
) VALUES
-- Provider rows
(10, UNHEX(REPLACE(UUID(), '-', '')), 'moconnor',         '', 1, 1,
 'Michael',  'OConnor',   'Dr.',  'Internal Medicine',    'michael.oconnor@example.org',  'michael.oconnor@example.org',
 2, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567890'),
(11, UNHEX(REPLACE(UUID(), '-', '')), 'erodriguez',       '', 1, 1,
 'Elena',    'Rodriguez', 'Dr.',  'Family Medicine',      'elena.rodriguez@example.org',  'elena.rodriguez@example.org',
 2, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567891'),
(12, UNHEX(REPLACE(UUID(), '-', '')), 'amiller',          '', 1, 1,
 'Amelia',   'Miller',    'Dr.',  'Psychiatry',           'amelia.miller@example.org',    'amelia.miller@example.org',
 2, 1, 'physician', '2084P0800X', 'standard', 'standard', 'MD', '1234567892'),
(16, UNHEX(REPLACE(UUID(), '-', '')), 'mchen',     '', 1, 1,
 'Michael',  'Chen',      'Dr.',  'Internal Medicine',    'michael.chen@example.org',     'michael.chen@example.org',
 1, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567896'),
(17, UNHEX(REPLACE(UUID(), '-', '')), 'meriksson',  '', 1, 1,
 'Marcus',   'Eriksson',  'Dr.',  'Psychiatry',           'marcus.eriksson@example.org',  'marcus.eriksson@example.org',
 2, 1, 'physician', '2084P0800X', 'standard', 'standard', 'MD', '1234567897'),
(18, UNHEX(REPLACE(UUID(), '-', '')), 'ytanaka',      '', 1, 1,
 'Yuki',     'Tanaka',    'LCSW', 'Clinical Social Work', 'yuki.tanaka@example.org',      'yuki.tanaka@example.org',
 2, 1, 'physician', '1041C0700X', 'standard', 'standard', 'LCSW', '1234567898'),
(19, UNHEX(REPLACE(UUID(), '-', '')), 'egarcia',     '', 1, 1,
 'Ethan',    'Garcia',    'Dr.',  'Internal Medicine',    'ethan.garcia@example.org',     'ethan.garcia@example.org',
 2, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567899'),
(21, UNHEX(REPLACE(UUID(), '-', '')), 'amartin',          '', 1, 1,
 'Amy',      'Martin',    'NP',   'Family Medicine',      'amy.martin@example.org',       'amy.martin@example.org',
 2, 1, 'physician', '363LF0000X', 'standard', 'standard', 'FNP', '1234567906'),
(22, UNHEX(REPLACE(UUID(), '-', '')), 'ljohnson',    '', 1, 1,
 'Lucas',    'Johnson',   'Dr.',  'Addiction Medicine',   'lucas.johnson@example.org',    'lucas.johnson@example.org',
 2, 1, 'physician', '207RA0401X', 'standard', 'standard', 'MD', '1234567900'),
(25, UNHEX(REPLACE(UUID(), '-', '')), 'bwilliams',    '', 1, 1,
 'Ben',      'Williams',  'Dr.',  'Internal Medicine',    'ben.williams@example.org',     'ben.williams@example.org',
 4, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567903'),
(37, UNHEX(REPLACE(UUID(), '-', '')), 'schen',      '', 1, 1,
 'Sarah',    'Chen',      'RN',   'Charge Nursing',       'sarah.chen@example.org',       'sarah.chen@example.org',
 2, 1, 'physician', '163WC1500X', 'standard', 'standard', 'RN', '1234567907'),
-- Additional providers
(14, UNHEX(REPLACE(UUID(), '-', '')), 'jnelson',  '', 1, 1,
 'Jonathan', 'Nelson',    'Dr.',  'Family Medicine',      'jonathan.nelson@example.org',  'jonathan.nelson@example.org',
 1, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567894'),
(15, UNHEX(REPLACE(UUID(), '-', '')), 'ppatel',      '', 1, 1,
 'Priya',    'Patel',     'NP',   'Psychiatric Nurse Practitioner', 'priya.patel@example.org', 'priya.patel@example.org',
 2, 1, 'physician', '363LP0808X', 'standard', 'standard', 'NP', '1234567895'),
(26, UNHEX(REPLACE(UUID(), '-', '')), 'htanaka',   '', 1, 1,
 'Hiroshi',  'Tanaka',    'Dr.',  'Family Medicine',      'hiroshi.tanaka@example.org',   'hiroshi.tanaka@example.org',
 1, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567904'),
(27, UNHEX(REPLACE(UUID(), '-', '')), 'dthompson',   '', 1, 1,
 'David',    'Thompson',  'Dr.',  'Internal Medicine',    'david.thompson@example.org',   'david.thompson@example.org',
 1, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567905'),
-- Additional providers
(13, UNHEX(REPLACE(UUID(), '-', '')), 'mthompson',        '', 1, 1,
 'Marcus',   'Thompson',  'Dr.',  'Internal Medicine',    'marcus.thompson@example.org',  'marcus.thompson@example.org',
 3, 1, 'physician', '207R00000X', 'standard', 'standard', 'MD', '1234567893'),
(23, UNHEX(REPLACE(UUID(), '-', '')), 'danderson',    '', 1, 1,
 'Dave',     'Anderson',  'Dr.',  'Family Medicine',      'dave.anderson@example.org',    'dave.anderson@example.org',
 2, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567901'),
-- Central (id=4)
(24, UNHEX(REPLACE(UUID(), '-', '')), 'jsmith',        '', 1, 1,
 'Joe',      'Smith',     'Dr.',  'Family Medicine',      'joe.smith@example.org',        'joe.smith@example.org',
 4, 1, 'physician', '207Q00000X', 'standard', 'standard', 'MD', '1234567902');

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
(32, UNHEX(REPLACE(UUID(), '-', '')), 'smartinez',  '', 0, 1,
 'Sarah', 'Martinez',  'RN', 'Nursing', 'sarah.martinez@example.org',  'sarah.martinez@example.org',
 2, 0, 'nurse', '163W00000X', 'standard', 'standard'),
(33, UNHEX(REPLACE(UUID(), '-', '')), 'kwatanabe',    '', 0, 1,
 'Ken',   'Watanabe',  'RN', 'Nursing', 'ken.watanabe@example.org',    'ken.watanabe@example.org',
 4, 0, 'nurse', '163W00000X', 'standard', 'standard'),
(34, UNHEX(REPLACE(UUID(), '-', '')), 'mrodriguez', '', 0, 1,
 'Maria', 'Rodriguez', 'RN', 'Nursing', 'maria.rodriguez@example.org', 'maria.rodriguez@example.org',
 3, 0, 'nurse', '163W00000X', 'standard', 'standard');

-- =============================================================================
-- MEDICAL ASSISTANTS — IDs 30-31
-- =============================================================================

INSERT INTO `users` (
    `id`, `uuid`, `username`, `password`, `authorized`, `active`,
    `fname`, `lname`, `title`, `specialty`, `email`, `email_direct`,
    `facility_id`, `calendar`, `abook_type`, `taxonomy`,
    `main_menu_role`, `patient_menu_role`
) VALUES
(30, UNHEX(REPLACE(UUID(), '-', '')), 'lpatel',       '', 0, 1,
 'Lisa',   'Patel',    'MA', 'Medical Assistant', 'lisa.patel@example.org',      'lisa.patel@example.org',
 1, 0, 'med_asst', '356AM0700X', 'standard', 'standard'),
(31, UNHEX(REPLACE(UUID(), '-', '')), 'hsong',        '', 0, 1,
 'Hana',   'Song',     'MA', 'Medical Assistant', 'hana.song@example.org',       'hana.song@example.org',
 2, 0, 'med_asst', '356AM0700X', 'standard', 'standard'),
(35, UNHEX(REPLACE(UUID(), '-', '')), 'ewilson',  '', 0, 1,
 'Emma',   'Wilson',   'MA', 'Medical Assistant', 'emma.wilson@example.org',     'emma.wilson@example.org',
 4, 0, 'med_asst', '356AM0700X', 'standard', 'standard'),
(36, UNHEX(REPLACE(UUID(), '-', '')), 'clewis', '', 0, 1,
 'Cheryl', 'Lewis',    'MA', 'Medical Assistant', 'cheryl.lewis@example.org',    'cheryl.lewis@example.org',
 3, 0, 'med_asst', '356AM0700X', 'standard', 'standard');

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
(30, 'lpatel',     '$2y$12$CBV47dDP/2CvTxaO7bER4.XTm0z6zTJSrfKLcz6gOk5ViFJWGTFHi', NOW()),
(31, 'hsong',      '$2y$12$9jMeSDX.LGvUw61ENWAXyenoSGfXrQ4gMS2rI6klVr0kdF5LP6kxK', NOW()),
(14, 'jnelson', '$2y$12$52dNJeE6mVy6/ldpvgd0LevYze/lUYUst3KrbfkdJpp3x2DXDNd3S', NOW()),
(15, 'ppatel',     '$2y$12$76qMLLY/H6Do9yalJatWxesKaVJyBAiAGv0mF3mBfccIQ.fqMejEO', NOW()),
(16, 'mchen',    '$2y$12$ePXFgy39T4/fL/k/3XlBNeQcT48WXcsIdwzEpplRqsYgNq3AeCtB6', NOW()),
(17, 'meriksson', '$2y$12$waV7k5AtmrDHjzerAAFpqu85XhhjF8S9sg4aZFOx6zPg3rWZCwvx2', NOW()),
(18, 'ytanaka',     '$2y$12$e3BBDBFBN.qz4.efJiMyPO5RcmCtiMkd8jL7sQUJkkebiG7ZCEdSu', NOW()),
(19, 'egarcia',    '$2y$12$/GrDkpLl.vnlRtyeTWg3oeVZ2lu2RtDrkNWStMSlpAh./6vIPp8eG', NOW()),
(22, 'ljohnson',   '$2y$12$dj4OxewFHZY2m4jp/BEEG.jHMb6vTJ65rzdIKkM1FUaw0KX5Vx09y', NOW()),
(23, 'danderson',   '$2y$12$IvYsCD6Ph5VMegroGZ6wEOQQ.2ABhUm5x9M87uGKtUxZ1wM4J6O12', NOW()),
(24, 'jsmith',       '$2y$12$uIfo6s2Kvaket.0uKkLefeJLqa9R3HulrDa9XTcanBFyWL8BWCtJu', NOW()),
(25, 'bwilliams',   '$2y$12$9QnCTFw2yXb6/KvOY4muAuDVDYKVmT/hEDkx.aqQPg/fE3sSa376S', NOW()),
(26, 'htanaka',  '$2y$12$J1I9hwTR77kJyO0EF1xPU.bkpOwpGfcxWFKJu1GZZvaUPukUV8n.K', NOW()),
(27, 'dthompson',  '$2y$12$GXr1quBEM2LyXqDsrotI2Oyj53ihkg6263/SzKl8eui4Wd3SmrhJW', NOW()),
(32, 'smartinez',  '$2y$12$tREJimaI7taQ2ccv6wELkO9iTwNpr2PzT02ipQrfvIzxIztoJurWm', NOW()),
(33, 'kwatanabe',    '$2y$12$RfgtuTNYjutkCCwWtFAnXeVe1LageEPaji8mwWtWQi9X2pYIkArqS', NOW()),
(34, 'mrodriguez', '$2y$12$/.51R5g.cGDfGFfYl/tyB.KTSSUvra1CM1TUIECdK7LjQ76X.Bei6', NOW()),
(35, 'ewilson',     '$2y$12$TqKEUDf5oWyUduqqemryzeXlMWtHzK4LQw5u6pDAQkN6KJ1w5JD/e', NOW()),
(36, 'clewis',    '$2y$12$CaoT3Gz0uzk97gvSZte7feT7wRW5NP3CebOck1ot9Imc/EKKDbK1S', NOW()),
-- schen reuses the dthompson hash: every demo password is ZoomDem0!, and
-- the hashes are interchangeable per-user-id. Cheaper than generating a new
-- bcrypt and the demo never inspects raw hashes.
(37, 'schen',     '$2y$12$GXr1quBEM2LyXqDsrotI2Oyj53ihkg6263/SzKl8eui4Wd3SmrhJW', NOW());

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
(17, 'users', 'lpatel',          10, 'Lisa Patel',       0),
(18, 'users', 'hsong',           10, 'Hana Song',        0),
(19, 'users', 'erodriguez',      10, 'Elena Rodriguez',  0),
-- New providers
(20, 'users', 'jnelson', 10, 'Jonathan Nelson',  0),
(21, 'users', 'ppatel',     10, 'Priya Patel',      0),
(22, 'users', 'mchen',    10, 'Michael Chen',     0),
(23, 'users', 'meriksson', 10, 'Marcus Eriksson',  0),
(24, 'users', 'ytanaka',     10, 'Yuki Tanaka',      0),
(25, 'users', 'egarcia',    10, 'Ethan Garcia',     0),
(26, 'users', 'ljohnson',   10, 'Lucas Johnson',    0),
(27, 'users', 'danderson',   10, 'Dave Anderson',    0),
(28, 'users', 'jsmith',       10, 'Joe Smith',        0),
(29, 'users', 'bwilliams',   10, 'Ben Williams',     0),
(30, 'users', 'htanaka',  10, 'Hiroshi Tanaka',   0),
(31, 'users', 'dthompson',  10, 'David Thompson',   0),
-- New support staff
(32, 'users', 'smartinez',  10, 'Sarah Martinez',   0),
(33, 'users', 'kwatanabe',    10, 'Ken Watanabe',     0),
(34, 'users', 'mrodriguez', 10, 'Maria Rodriguez',  0),
(35, 'users', 'ewilson',     10, 'Emma Wilson',      0),
(36, 'users', 'clewis',    10, 'Cheryl Lewis',     0),
(37, 'users', 'schen',     10, 'Sarah Chen',       0);

-- group_id 13 = Physicians, 12 = Clinicians
INSERT IGNORE INTO gacl_groups_aro_map (group_id, aro_id) VALUES
-- Original providers + Amy promoted to Physicians
(13,12),(13,13),(13,14),(13,16),(13,19),
-- New providers → Physicians
(13,20),(13,21),(13,22),(13,23),(13,24),(13,25),(13,26),(13,27),(13,28),(13,29),(13,30),(13,31),(13,37),
-- Support staff → Clinicians
(12,15),(12,17),(12,18),(12,32),(12,33),(12,34),(12,35),(12,36);

INSERT IGNORE INTO groups (name, user) VALUES
-- Providers (Physicians group)
('Physicians', 'moconnor'),
('Physicians', 'erodriguez'),
('Physicians', 'amiller'),
('Physicians', 'mthompson'),
('Physicians', 'amartin'),
('Physicians', 'jnelson'),
('Physicians', 'ppatel'),
('Physicians', 'mchen'),
('Physicians', 'meriksson'),
('Physicians', 'ytanaka'),
('Physicians', 'egarcia'),
('Physicians', 'ljohnson'),
('Physicians', 'danderson'),
('Physicians', 'jsmith'),
('Physicians', 'bwilliams'),
('Physicians', 'htanaka'),
('Physicians', 'dthompson'),
('Physicians', 'schen'),
-- Support staff (Clinicians group)
('Clinicians', 'blee'),
('Clinicians', 'lpatel'),
('Clinicians', 'hsong'),
('Clinicians', 'smartinez'),
('Clinicians', 'kwatanabe'),
('Clinicians', 'mrodriguez'),
('Clinicians', 'ewilson'),
('Clinicians', 'clewis');

-- =============================================================================
-- STAFF DETAILS — populate Edit User screen fields
--   federaltaxid  = EIN (XX-XXXXXXX)
--   federaldrugid = DEA Number (2 letters + 7 digits; prescribers only)
--   upin          = legacy provider ID
--   state_license_number = state-specific license string
--   weno_prov_id  = Weno eRx provider ID
--   supervisor_id = MD supervisor (NPs/FNPs/MAs/Nurses)
--   billing_facility_id = same as facility_id
--   info          = additional info / short bio
--   valedictory   = signature closing
-- =============================================================================

-- Providers (MDs first, then NP/FNP/LCSW with supervisors)
UPDATE users SET federaltaxid='84-1000010', federaldrugid='AO1234567', upin='A10001', state_license_number='MA-15101', weno_prov_id='W10001', billing_facility_id=2, valedictory='MD',        info='Board-certified Internal Medicine. Practicing telehealth since 2020.' WHERE id=10;
UPDATE users SET federaltaxid='84-1000011', federaldrugid='AR1234567', upin='A10002', state_license_number='MA-15211', weno_prov_id='W10002', billing_facility_id=2, valedictory='MD',        info='Board-certified Family Medicine. Focuses on behavioral health in primary care.' WHERE id=11;
UPDATE users SET federaltaxid='84-1000012', federaldrugid='AM1234567', upin='A10003', state_license_number='MA-15301', weno_prov_id='W10003', billing_facility_id=2, valedictory='MD',        info='Board-certified Psychiatry. Telehealth med management since 2019.' WHERE id=12;
UPDATE users SET federaltaxid='84-1000013', federaldrugid='AT1234567', upin='A10004', state_license_number='CA-44101', weno_prov_id='W10004', billing_facility_id=3, valedictory='MD',        info='Board-certified Internal Medicine. Former cardiology subspecialty interest.' WHERE id=13;
UPDATE users SET federaltaxid='84-1000014', federaldrugid='AN1234567', upin='A10014', state_license_number='CO-DR-22041', weno_prov_id='W10014', billing_facility_id=1, valedictory='MD',     info='Board-certified Family Medicine. Diverse panel, all ages.' WHERE id=14;
UPDATE users SET federaltaxid='84-1000015', federaldrugid='MP1234567', upin='A10015', state_license_number='MA-NP-22042', weno_prov_id='W10015', billing_facility_id=2, supervisor_id=12, valedictory='PMHNP-BC', info='Board-certified Psychiatric Nurse Practitioner. Med management for adults.' WHERE id=15;
UPDATE users SET federaltaxid='84-1000016', federaldrugid='AC1234567', upin='A10016', state_license_number='CO-DR-22616', weno_prov_id='W10016', billing_facility_id=1, valedictory='MD',     info='Board-certified Internal Medicine. Chronic disease focus.' WHERE id=16;
UPDATE users SET federaltaxid='84-1000017', federaldrugid='AE1234567', upin='A10017', state_license_number='MA-15717', weno_prov_id='W10017', billing_facility_id=2, valedictory='MD',        info='Board-certified Psychiatry. Anxiety/mood disorders.' WHERE id=17;
UPDATE users SET federaltaxid='84-1000018', federaldrugid=NULL,        upin='A10018', state_license_number='MA-LCSW-2031', weno_prov_id=NULL, billing_facility_id=2, supervisor_id=12, valedictory='LCSW',     info='LCSW with 12 years experience. CBT and behavioral activation.' WHERE id=18;
UPDATE users SET federaltaxid='84-1000019', federaldrugid='AG1234567', upin='A10019', state_license_number='MA-15919', weno_prov_id='W10019', billing_facility_id=2, valedictory='MD',        info='Board-certified Internal Medicine. Bilingual English/Spanish.' WHERE id=19;
UPDATE users SET federaltaxid='84-1000021', federaldrugid='MM1234567', upin='A10021', state_license_number='MA-FNP-3001', weno_prov_id='W10021', billing_facility_id=2, supervisor_id=10, valedictory='FNP-C',   info='Family NP, promoted from RN. Diabetes, hypertension, women''s health.' WHERE id=21;
UPDATE users SET federaltaxid='84-1000022', federaldrugid='FJ1234567', upin='A10022', state_license_number='MA-15822', weno_prov_id='W10022', billing_facility_id=2, valedictory='MD',        info='Board-certified Addiction Medicine. X-DEA waiver for buprenorphine.' WHERE id=22;
UPDATE users SET federaltaxid='84-1000023', federaldrugid='AA1234567', upin='A10023', state_license_number='MA-15623', weno_prov_id='W10023', billing_facility_id=2, valedictory='MD',        info='Board-certified Family Medicine. Rural telehealth focus.' WHERE id=23;
UPDATE users SET federaltaxid='84-1000024', federaldrugid='AS1234567', upin='A10024', state_license_number='MO-29001', weno_prov_id='W10024', billing_facility_id=4, valedictory='MD',        info='Board-certified Family Medicine. Sole provider at Central facility.' WHERE id=24;
UPDATE users SET federaltaxid='84-1000025', federaldrugid='AP1234567', upin='A10025', state_license_number='MO-29025', weno_prov_id='W10025', billing_facility_id=4, valedictory='MD',        info='Board-certified Internal Medicine. Geriatrics and complex care for Central region.' WHERE id=25;
UPDATE users SET federaltaxid='84-1000026', federaldrugid='AT2234567', upin='A10026', state_license_number='CO-DR-22126', weno_prov_id='W10026', billing_facility_id=1, valedictory='MD',     info='Board-certified Family Medicine. Adolescent and adult care.' WHERE id=26;
UPDATE users SET federaltaxid='84-1000027', federaldrugid='AT3234567', upin='A10027', state_license_number='CO-DR-22227', weno_prov_id='W10027', billing_facility_id=1, valedictory='MD',     info='Board-certified Internal Medicine. Cardiometabolic disease.' WHERE id=27;
UPDATE users SET federaltaxid='84-1000037',                            upin='A10037', state_license_number='MA-RN-44237', weno_prov_id='W10037', billing_facility_id=2, supervisor_id=10, valedictory='RN',      info='Charge Nurse — Boston facility lead. RN with med management + care coordination focus.' WHERE id=37;

-- Support staff (nurses + MAs) — no DEA; have supervisors; lighter detail set
UPDATE users SET federaltaxid='84-1000020', upin='A10020', state_license_number='CO-RN-44120', billing_facility_id=1, supervisor_id=14, valedictory='RN',  info='RN with chronic care management experience.' WHERE id=20;
UPDATE users SET federaltaxid='84-1000030', upin='A10030', state_license_number='CO-MA-55030', billing_facility_id=1, supervisor_id=14, valedictory='CMA', info='Certified Medical Assistant.' WHERE id=30;
UPDATE users SET federaltaxid='84-1000031', upin='A10031', state_license_number='MA-MA-55131', billing_facility_id=2, supervisor_id=10, valedictory='CMA', info='Certified Medical Assistant.' WHERE id=31;
UPDATE users SET federaltaxid='84-1000032', upin='A10032', state_license_number='MA-RN-44232', billing_facility_id=2, supervisor_id=11, valedictory='RN',  info='RN with behavioral health experience.' WHERE id=32;
UPDATE users SET federaltaxid='84-1000033', upin='A10033', state_license_number='MO-RN-44333', billing_facility_id=4, supervisor_id=24, valedictory='RN',  info='RN with primary care experience.' WHERE id=33;
UPDATE users SET federaltaxid='84-1000034', upin='A10034', state_license_number='CA-RN-44434', billing_facility_id=3, supervisor_id=13, valedictory='RN',  info='RN with chronic disease management experience.' WHERE id=34;
UPDATE users SET federaltaxid='84-1000035', upin='A10035', state_license_number='MO-MA-55235', billing_facility_id=4, supervisor_id=24, valedictory='CMA', info='Certified Medical Assistant.' WHERE id=35;
UPDATE users SET federaltaxid='84-1000036', upin='A10036', state_license_number='CA-MA-55336', billing_facility_id=3, supervisor_id=13, valedictory='CMA', info='Certified Medical Assistant.' WHERE id=36;

-- =============================================================================
-- FACILITY PERMISSIONS (users_facility)
--   Each staff member gets a single row pointing at their home facility.
--   OpenEMR uses users_facility to filter both record access AND calendar
--   appearance, so a single-row mapping keeps providers off other facilities'
--   calendars while still giving them full access to their own facility.
--   Admin user (id=1) is intentionally NOT in users_facility — that gives the
--   admin the implicit all-facility view used for cross-facility tasks.
-- =============================================================================

INSERT INTO `users_facility` (tablename, table_id, facility_id, warehouse_id)
SELECT 'users', u.id, u.facility_id, ''
  FROM users u
 WHERE u.id BETWEEN 10 AND 37
   AND u.facility_id > 0;

-- =============================================================================
-- ACL — providers stay in Physicians only; nurses + MAs in Clinicians only.
-- Earlier iteration added Front Office to both for "lenient" demo access, but
-- that exposed admin-flavored UI controls (hide-appointment toggles, status
-- editors) that weren't needed for provider-side demos. Admin user (id=1)
-- retains its own Administrators group membership for cross-cutting tasks.
-- =============================================================================
