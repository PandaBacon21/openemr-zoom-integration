-- =============================================================================
-- 02 — FACILITIES (4 facilities, one per US time zone)
-- =============================================================================

-- =============================================================================
-- FACILITY
-- =============================================================================

-- Four facilities, one per US time zone (Mountain/Eastern/Pacific/Central).
-- Each facility hosts providers + 1 nurse + 1 MA.
--
-- OpenEMR ships with a default facility at id=3. We delete it FIRST so we can
-- claim id=3 for our CA facility. The admin user (id=1) currently sits on
-- facility_id=3 by default — facility_id has no FK constraint, so the
-- DELETE leaves admin briefly dangling, but the UPDATE below restores them.
--
-- id=5 is the Veradigm-style facility (inserted below); delete it first so the
-- insert is idempotent and to clear any stale pre-renumber row at that id.
DELETE FROM `facility` WHERE `id` IN (3, 5);

INSERT INTO `facility` (
    `id`, `uuid`, `name`, `phone`,
    `street`, `city`, `state`, `postal_code`, `country_code`,
    `facility_npi`, `color`,
    `service_location`, `billing_location`, `accepts_assignment`,
    `primary_business_entity`, `inactive`
) VALUES
(1, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Medical Center - CO', '303-555-0100',
 '100 Health Plaza',     'Denver',        'CO', '80201', 'USA',
 '1234567890', '#0b5cff', 1, 1, 1, 1, 0),
(2, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Medical Center - MA', '617-555-0100',
 '25 Cambridge Street',  'Boston',        'MA', '02114', 'USA',
 '1234567891', '#00053d', 1, 1, 1, 1, 0),
(3, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Medical Center - CA', '415-555-0100',
 '200 Parnassus Avenue', 'San Francisco', 'CA', '94143', 'USA',
 '1234567892', '#b4d0f8', 1, 1, 1, 1, 0),
(4, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Medical Center - MO', '816-555-0100',
 '456 Truman Road',      'Kansas City',   'MO', '64106', 'USA',
 '1234567893', '#f7f2e3', 1, 1, 1, 1, 0),
-- EHR-integration-style facility: appointments scheduled here represent the
-- Veradigm telehealth demo. Pickup for the external Veradigm appointment page
-- is by appointment TYPE (not facility), so this facility is the demo-context
-- marker / schedulable location for Veradigm-style visits.
(5, UNHEX(REPLACE(UUID(), '-', '')),
 'Zoomly Veradigm Clinic', '888-555-0100',
 '1 Integration Way',    'Chicago',       'IL', '60601', 'USA',
 '1234567894', '#8E24AA', 1, 1, 1, 1, 0);

UPDATE `users` SET `facility_id` = 1 WHERE `id` = 1;

-- =============================================================================
-- PHARMACIES — one preferred pharmacy per facility region
-- =============================================================================
INSERT INTO `pharmacies` (id, name, transmit_method, email, ncpdp, npi) VALUES
(1, 'CVS Pharmacy - Denver Downtown',      1, 'cvs.denver@example.org',     6001001, 1234567950),
(2, 'CVS Pharmacy - Boston Back Bay',      1, 'cvs.boston@example.org',     6002001, 1234567951),
(3, 'Walgreens - San Francisco Union Sq',  1, 'walgreens.sf@example.org',   6003001, 1234567952),
(4, 'Walmart Pharmacy - Kansas City',      1, 'walmart.kc@example.org',     6004001, 1234567953);

INSERT INTO `addresses` (id, line1, city, state, zip, country, foreign_id) VALUES
(300, '1500 California Street',  'Denver',         'CO', '80202', 'USA', 1),
(301, '587 Boylston Street',     'Boston',         'MA', '02116', 'USA', 2),
(302, '135 Powell Street',       'San Francisco',  'CA', '94102', 'USA', 3),
(303, '4500 Main Street',        'Kansas City',    'MO', '64111', 'USA', 4);

