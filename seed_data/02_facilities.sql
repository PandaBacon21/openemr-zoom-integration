-- =============================================================================
-- 02 — FACILITIES (4 facilities, one per US time zone)
-- =============================================================================

-- =============================================================================
-- FACILITY
-- =============================================================================

-- Four facilities, one per US time zone (Mountain/Eastern/Pacific/Central).
-- Each facility hosts providers + 1 nurse + 1 MA per the S12-17 matrix.
INSERT INTO `facility` (
    `id`, `uuid`, `name`, `phone`,
    `street`, `city`, `state`, `postal_code`, `country_code`,
    `facility_npi`, `color`,
    `service_location`, `billing_location`, `accepts_assignment`,
    `primary_business_entity`, `inactive`
) VALUES
(1, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Medical Center - CO',         '303-555-0100',
 '100 Health Plaza',     'Denver',        'CO', '80201', 'USA',
 '1234567890', '#0b5cff', 1, 1, 1, 1, 0),
(2, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Medical Center - MA',    '617-555-0100',
 '25 Cambridge Street',  'Boston',        'MA', '02114', 'USA',
 '1234567891', '#00053d', 1, 1, 1, 1, 0),
(4, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Medical Center - CA',    '415-555-0100',
 '200 Parnassus Avenue', 'San Francisco', 'CA', '94143', 'USA',
 '1234567892', '#b4d0f8', 1, 1, 1, 1, 0),
(5, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Medical Center - MO', '816-555-0100',
 '456 Truman Road',      'Kansas City',   'MO', '64106', 'USA',
 '1234567893', '#f7f2e3', 1, 1, 1, 1, 0);

UPDATE `users` SET `facility_id` = 1 WHERE `id` = 1;

-- Remove the OpenEMR default facility (id=3) entirely. Nothing references it
-- after admin moves to facility 1.
DELETE FROM `facility` WHERE `id` = 3;

