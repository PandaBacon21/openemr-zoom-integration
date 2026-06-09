-- =============================================================================
-- 05 — PATIENTS (51 = 30 original + 21 new, distributed across 4 facilities)
-- =============================================================================

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
(105, UNHEX(REPLACE(UUID(), '-', '')), 'Linda', 'Whitaker', '', 'Mrs.',
 '1958-06-30', 'Female', 'married', '1020 Birch Court', 'Denver', 'CO', '80206', 'USA',
 '303-555-0106', 'linda.whitaker@example.org', 11, '105', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(106, UNHEX(REPLACE(UUID(), '-', '')), 'Ethan', 'Brooks', 'J', 'Mr.',
 '1995-04-11', 'Male', 'single', '348 Walnut Street', 'Denver', 'CO', '80207', 'USA',
 '303-555-0107', 'ethan.brooks@example.org', 12, '106', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(107, UNHEX(REPLACE(UUID(), '-', '')), 'Maria', 'Wong', 'L', 'Ms.',
 '1982-12-03', 'Female', 'divorced', '675 Spruce Way', 'Denver', 'CO', '80208', 'USA',
 '303-555-0108', 'maria.wong@example.org', 13, '107', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(108, UNHEX(REPLACE(UUID(), '-', '')), 'Thomas', 'Walsh', 'P', 'Mr.',
 '1969-08-19', 'Male', 'married', '512 Hickory Drive', 'Denver', 'CO', '80209', 'USA',
 '303-555-0109', 'thomas.walsh@example.org', 10, '108', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(109, UNHEX(REPLACE(UUID(), '-', '')), 'Aisha', 'Carter', 'K', 'Ms.',
 '1993-01-25', 'Female', 'single', '890 Willow Lane', 'Denver', 'CO', '80210', 'USA',
 '303-555-0110', 'aisha.carter@example.org', 11, '109', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(110, UNHEX(REPLACE(UUID(), '-', '')), 'Brian', 'Foster', 'E', 'Mr.',
 '1980-05-12', 'Male', 'married', '23 Aspen Court', 'Denver', 'CO', '80211', 'USA',
 '303-555-0111', 'brian.foster@example.org', 12, '110', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(111, UNHEX(REPLACE(UUID(), '-', '')), 'Yuki', 'Sato', '', 'Ms.',
 '1997-08-03', 'Female', 'single', '67 Larimer Street', 'Denver', 'CO', '80212', 'USA',
 '303-555-0112', 'yuki.sato@example.org', 13, '111', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
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
(125, UNHEX(REPLACE(UUID(), '-', '')), 'Isabelle', 'Vasquez', 'A', 'Ms.',
 '1998-11-03', 'Female', 'single', '342 Clarkson Street', 'Denver', 'CO', '80226', 'USA',
 '303-555-0126', 'isabelle.vasquez@example.org', 11, '125', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
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
 '303-555-0130', 'amara.diallo@example.org', 11, '129', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
-- =============================================================================
-- NEW PATIENTS (Sprint 12 / S12-28) — PIDs 130-150
-- 21 new patients to bring totals to 3 patients per provider × 17 providers = 51.
-- Each row already carries the patient's destination facility region in
-- (street, city, state, postal_code, phone_cell) and target providerID.
-- =============================================================================
-- East (13 new patients)
(130, UNHEX(REPLACE(UUID(), '-', '')), 'Tom',        'Bell',     '',  'Mr.',
 '1985-05-12', 'Male',   'married',  '220 Madison Avenue',     'New York',     'NY', '10016', 'USA',
 '212-555-0130', 'tom.bell@example.org',           17, '130', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(132, UNHEX(REPLACE(UUID(), '-', '')), 'Bryan',      'Roberts',  'D', 'Mr.',
 '1978-03-22', 'Male',   'divorced', '220 Peachtree Street',   'Atlanta',      'GA', '30303', 'USA',
 '404-555-0132', 'bryan.roberts@example.org',      22, '132', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(133, UNHEX(REPLACE(UUID(), '-', '')), 'Ashley',     'Cohen',    'M', 'Ms.',
 '1982-11-04', 'Female', 'single',   '200 Spring Garden Street','Philadelphia', 'PA', '19130', 'USA',
 '215-555-0133', 'ashley.cohen@example.org',       22, '133', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(134, UNHEX(REPLACE(UUID(), '-', '')), 'Marcus',     'Hill',     'J', 'Mr.',
 '1971-07-15', 'Male',   'married',  '250 N Tryon Street',     'Charlotte',    'NC', '28202', 'USA',
 '704-555-0134', 'marcus.hill@example.org',        16, '134', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(135, UNHEX(REPLACE(UUID(), '-', '')), 'Linda',      'Kapoor',   'A', 'Mrs.',
 '1968-09-28', 'Female', 'married',  '412 Commonwealth Avenue','Boston',       'MA', '02215', 'USA',
 '617-555-0135', 'linda.kapoor@example.org',       16, '135', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(136, UNHEX(REPLACE(UUID(), '-', '')), 'Roberto',    'Cruz',     'A', 'Mr.',
 '1965-04-10', 'Male',   'married',  '175 Biscayne Boulevard', 'Miami',        'FL', '33132', 'USA',
 '305-555-0136', 'roberto.cruz@example.org',       19, '136', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(137, UNHEX(REPLACE(UUID(), '-', '')), 'Sasha',      'Yang',     'L', 'Ms.',
 '1996-12-03', 'Female', 'single',   '89 Lexington Avenue',    'New York',     'NY', '10010', 'USA',
 '212-555-0137', 'sasha.yang@example.org',         19, '137', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(138, UNHEX(REPLACE(UUID(), '-', '')), 'Tyler',      'Murphy',   'B', 'Mr.',
 '1992-06-25', 'Male',   'single',   '500 N Florida Avenue',   'Tampa',        'FL', '33602', 'USA',
 '813-555-0138', 'tyler.murphy@example.org',       21, '138', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(139, UNHEX(REPLACE(UUID(), '-', '')), 'Christina',  'Knight',   'R', 'Ms.',
 '1988-02-14', 'Female', 'married',  '1200 K Street NW',       'Washington',   'DC', '20005', 'USA',
 '202-555-0139', 'christina.knight@example.org',   21, '139', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(140, UNHEX(REPLACE(UUID(), '-', '')), 'Hannah',     'Kelly',    'M', 'Ms.',
 '1994-10-18', 'Female', 'single',   '510 Boylston Street',    'Boston',       'MA', '02116', 'USA',
 '617-555-0140', 'hannah.kelly@example.org',       21, '140', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(141, UNHEX(REPLACE(UUID(), '-', '')), 'Frank',      'Burke',    'P', 'Mr.',
 '1972-01-08', 'Male',   'married',  '56 Broadway',            'New York',     'NY', '10004', 'USA',
 '212-555-0141', 'frank.burke@example.org',        25, '141', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(142, UNHEX(REPLACE(UUID(), '-', '')), 'Margaret',   'Sullivan', 'E', 'Mrs.',
 '1955-11-30', 'Female', 'widowed',  '1500 Market Street',     'Philadelphia', 'PA', '19102', 'USA',
 '215-555-0142', 'margaret.sullivan@example.org',  25, '142', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(143, UNHEX(REPLACE(UUID(), '-', '')), 'Devon',      'Banks',    'T', 'Mr.',
 '1993-07-22', 'Male',   'single',   '875 Spring Street',      'Atlanta',      'GA', '30308', 'USA',
 '404-555-0143', 'devon.banks@example.org',        25, '143', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
-- Mountain (4 new patients)
(131, UNHEX(REPLACE(UUID(), '-', '')), 'Janelle',    'Cho',      'S', 'Ms.',
 '1990-08-19', 'Female', 'single',   '1200 Pearl Street',      'Boulder',      'CO', '80302', 'USA',
 '720-555-0131', 'janelle.cho@example.org',        15, '131', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(144, UNHEX(REPLACE(UUID(), '-', '')), 'Mia',        'Davies',   'K', 'Ms.',
 '1991-05-09', 'Female', 'married',  '88 Walnut Street',       'Boulder',      'CO', '80302', 'USA',
 '720-555-0144', 'mia.davies@example.org',         14, '144', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(145, UNHEX(REPLACE(UUID(), '-', '')), 'Jordan',     'Hayes',    'L', 'Mr.',
 '1995-09-14', 'Male',   'single',   '350 N Tejon Street',     'Colorado Springs','CO','80903','USA',
 '719-555-0145', 'jordan.hayes@example.org',       26, '145', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(146, UNHEX(REPLACE(UUID(), '-', '')), 'Beatrice',   'Reed',     'M', 'Mrs.',
 '1957-03-26', 'Female', 'widowed',  '250 W South Temple',     'Salt Lake City','UT','84111','USA',
 '801-555-0146', 'beatrice.reed@example.org',      26, '146', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
-- West (1 new patient)
(147, UNHEX(REPLACE(UUID(), '-', '')), 'Caleb',      'Cole',     'A', 'Mr.',
 '1980-08-05', 'Male',   'married',  '450 N Vermont Avenue',   'Los Angeles',  'CA', '90027', 'USA',
 '213-555-0147', 'caleb.cole@example.org',         23, '147', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
-- Central (3 new patients)
(148, UNHEX(REPLACE(UUID(), '-', '')), 'Olivia',     'Davis',    'R', 'Ms.',
 '1985-12-21', 'Female', 'married',  '600 Broadway Street',    'Kansas City',  'MO', '64105', 'USA',
 '816-555-0148', 'olivia.davis@example.org',       24, '148', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(149, UNHEX(REPLACE(UUID(), '-', '')), 'Marcus',     'Curtis',   'J', 'Mr.',
 '1997-04-17', 'Male',   'single',   '1500 Main Street',       'Dallas',       'TX', '75201', 'USA',
 '214-555-0149', 'marcus.curtis@example.org',      24, '149', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW()),
(150, UNHEX(REPLACE(UUID(), '-', '')), 'Patricia',   'Diaz',     'L', 'Mrs.',
 '1970-10-11', 'Female', 'married',  '220 N State Street',     'Chicago',      'IL', '60601', 'USA',
 '312-555-0150', 'patricia.diaz@example.org',      24, '150', 'YES', 'YES', 'YES', 'portal', 'YES', 'YES', 'English', '', NOW());

-- =============================================================================
-- S12-28 — Patient address/phone/providerID redistribution for existing 30
-- Each patient moves from Denver to their assigned facility's region. Phone
-- area code matches new city; providerID points to the patient's new provider.
-- =============================================================================

-- East — Boston / NYC / Philadelphia / DC / Atlanta / Miami / Tampa / Charlotte
UPDATE patient_data SET street='250 Beacon Street',       city='Boston',       state='MA', postal_code='02116', phone_cell='617-555-0100', providerID=10 WHERE pid=100;
UPDATE patient_data SET street='175 5th Avenue',          city='New York',     state='NY', postal_code='10010', phone_cell='212-555-0101', providerID=18 WHERE pid=101;
UPDATE patient_data SET street='412 East 14th Street',    city='New York',     state='NY', postal_code='10009', phone_cell='212-555-0103', providerID=12 WHERE pid=103;
UPDATE patient_data SET street='320 Chestnut Street',     city='Philadelphia', state='PA', postal_code='19106', phone_cell='215-555-0106', providerID=12 WHERE pid=106;
UPDATE patient_data SET street='88 Newbury Street',       city='Boston',       state='MA', postal_code='02116', phone_cell='617-555-0108', providerID=10 WHERE pid=108;
UPDATE patient_data SET street='850 Walnut Street',       city='Philadelphia', state='PA', postal_code='19107', phone_cell='215-555-0109', providerID=18 WHERE pid=109;
UPDATE patient_data SET street='450 Pennsylvania Avenue', city='Washington',   state='DC', postal_code='20004', phone_cell='202-555-0110', providerID=12 WHERE pid=110;
UPDATE patient_data SET street='333 Constitution Avenue', city='Washington',   state='DC', postal_code='20001', phone_cell='202-555-0112', providerID=10 WHERE pid=112;
UPDATE patient_data SET street='100 Edgewood Avenue',     city='Atlanta',      state='GA', postal_code='30303', phone_cell='404-555-0114', providerID=17 WHERE pid=114;
UPDATE patient_data SET street='555 Marietta Street',     city='Atlanta',      state='GA', postal_code='30313', phone_cell='404-555-0117', providerID=11 WHERE pid=117;
UPDATE patient_data SET street='200 Brickell Avenue',     city='Miami',        state='FL', postal_code='33131', phone_cell='305-555-0118', providerID=17 WHERE pid=118;
UPDATE patient_data SET street='1500 NW 7th Street',      city='Miami',        state='FL', postal_code='33125', phone_cell='305-555-0119', providerID=16 WHERE pid=119;
UPDATE patient_data SET street='920 Bayshore Boulevard',  city='Tampa',        state='FL', postal_code='33606', phone_cell='813-555-0120', providerID=22 WHERE pid=120;
UPDATE patient_data SET street='1200 W Kennedy Boulevard',city='Tampa',        state='FL', postal_code='33606', phone_cell='813-555-0121', providerID=11 WHERE pid=121;
UPDATE patient_data SET street='410 S Brevard Street',    city='Charlotte',    state='NC', postal_code='28202', phone_cell='704-555-0123', providerID=19 WHERE pid=123;
UPDATE patient_data SET street='75 W Trade Street',       city='Charlotte',    state='NC', postal_code='28202', phone_cell='704-555-0125', providerID=11 WHERE pid=125;
UPDATE patient_data SET street='600 N Davidson Street',   city='Charlotte',    state='NC', postal_code='28206', phone_cell='704-555-0129', providerID=18 WHERE pid=129;

-- Mountain — Denver / Boulder / Colorado Springs / Salt Lake City
UPDATE patient_data SET street='412 Elm Street',          city='Denver',       state='CO', postal_code='80201', phone_cell='303-555-0104', providerID=14 WHERE pid=104;
UPDATE patient_data SET street='1020 Birch Court',        city='Denver',       state='CO', postal_code='80206', phone_cell='303-555-0105', providerID=27 WHERE pid=105;
UPDATE patient_data SET street='555 Broadway',            city='Denver',       state='CO', postal_code='80214', phone_cell='303-555-0113', providerID=27 WHERE pid=113;
UPDATE patient_data SET street='510 Spruce Street',       city='Boulder',      state='CO', postal_code='80302', phone_cell='720-555-0116', providerID=27 WHERE pid=116;
UPDATE patient_data SET street='350 University Avenue',   city='Boulder',      state='CO', postal_code='80309', phone_cell='720-555-0122', providerID=15 WHERE pid=122;
UPDATE patient_data SET street='1500 N Nevada Avenue',    city='Colorado Springs', state='CO', postal_code='80903', phone_cell='719-555-0124', providerID=26 WHERE pid=124;
UPDATE patient_data SET street='220 E Pikes Peak Avenue', city='Colorado Springs', state='CO', postal_code='80903', phone_cell='719-555-0126', providerID=15 WHERE pid=126;
UPDATE patient_data SET street='88 Main Street',          city='Salt Lake City', state='UT', postal_code='84101', phone_cell='801-555-0128', providerID=14 WHERE pid=128;

-- West — San Francisco / Los Angeles / San Diego / Seattle / Portland
UPDATE patient_data SET street='100 Sutter Street',       city='San Francisco', state='CA', postal_code='94104', phone_cell='415-555-0102', providerID=13 WHERE pid=102;
UPDATE patient_data SET street='1200 Wilshire Boulevard', city='Los Angeles',  state='CA', postal_code='90017', phone_cell='213-555-0107', providerID=23 WHERE pid=107;
UPDATE patient_data SET street='700 K Street',            city='San Diego',    state='CA', postal_code='92101', phone_cell='619-555-0111', providerID=13 WHERE pid=111;
UPDATE patient_data SET street='1500 4th Avenue',         city='Seattle',      state='WA', postal_code='98101', phone_cell='206-555-0115', providerID=23 WHERE pid=115;
UPDATE patient_data SET street='200 SW Salmon Street',    city='Portland',     state='OR', postal_code='97204', phone_cell='503-555-0127', providerID=13 WHERE pid=127;

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
UPDATE patient_data SET allow_patient_portal = 'YES', cmsportal_login = 'linda.whitaker'    WHERE pid = 105;

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
    (105, 'linda.whitaker',    '$2y$12$8JnLYbEzToMoMYIQ1Lsm8ulVHXye46./se7QyURqhkS2MAswPxrAO', 1, 'linda.whitaker');


-- =============================================================================
-- DEMO PAST-ENCOUNTER PATIENTS (Sprint 13 / S13-05)
--
-- 17 dedicated patients (PIDs 151-167) — one per mapped provider — sized to
-- the diabetes profile referenced in PAST_ENCOUNTER_NOTE
-- (services/openemr/encounter/sample_notes.py). Each is female, married, age
-- ~52-56 (DOB 1970-1974), regionally placed by the assigned provider's
-- facility, and tagged with referrer='Zoomly Demo Past Encounter' so
-- past_encounter._seed_one_provider can pick them deterministically (rather
-- than falling through to patients[0] which would pick a generic CHR/HYA/etc
-- chart that doesn't match today's locked telehealth follow-up narrative).
--
-- Companion clinical data (problems / meds / 3-months-ago in-person encounter
-- + vitals + HbA1c lab) lives in 07_clinical_data.sql.
-- =============================================================================

INSERT INTO `patient_data` (
    `pid`, `uuid`, `fname`, `lname`, `mname`, `title`,
    `DOB`, `sex`, `status`,
    `street`, `city`, `state`, `postal_code`, `country_code`,
    `phone_cell`, `email`,
    `providerID`, `pubpid`,
    `hipaa_mail`, `hipaa_voice`, `hipaa_notice`, `hipaa_message`,
    `hipaa_allowsms`, `hipaa_allowemail`,
    `language`, `financial`, `date`, `referrer`
) VALUES
-- East (facility 2) — 10 patients across MA/NY/PA/FL/NC/DC/GA matching each provider's facility region
-- Renamed from "Sarah Chen" → "Linda Chen" to avoid name collision with the
-- staff user Sarah Chen (Charge Nurse, id=37, added in S13 follow-up).
(151, UNHEX(REPLACE(UUID(), '-', '')), 'Linda',     'Chen',      'L', 'Mrs.',
 '1972-04-15', 'Female', 'married', '210 Newbury Street',     'Boston',       'MA', '02116', 'USA',
 '617-555-0151', 'linda.chen@example.org',                10, '151', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(152, UNHEX(REPLACE(UUID(), '-', '')), 'Maria',     'Lopez',     'A', 'Mrs.',
 '1971-08-22', 'Female', 'married', '420 Lexington Avenue',   'New York',     'NY', '10017', 'USA',
 '212-555-0152', 'maria.lopez@example.org',               11, '152', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(153, UNHEX(REPLACE(UUID(), '-', '')), 'Jennifer',  'Wright',    'E', 'Mrs.',
 '1973-02-10', 'Female', 'married', '88 Beacon Street',       'Boston',       'MA', '02108', 'USA',
 '617-555-0153', 'jennifer.wright@example.org',           12, '153', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(154, UNHEX(REPLACE(UUID(), '-', '')), 'Linda',     'Tran',      'M', 'Mrs.',
 '1970-11-05', 'Female', 'married', '1200 Market Street',     'San Francisco','CA', '94103', 'USA',
 '415-555-0154', 'linda.tran@example.org',                13, '154', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
-- Mountain (facility 1) — 4 patients in CO + 1 in UT
(155, UNHEX(REPLACE(UUID(), '-', '')), 'Amanda',    'Foster',    'J', 'Mrs.',
 '1972-07-19', 'Female', 'married', '650 Pearl Street',       'Boulder',      'CO', '80302', 'USA',
 '720-555-0155', 'amanda.foster@example.org',             14, '155', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(156, UNHEX(REPLACE(UUID(), '-', '')), 'Patricia',  'Reed',      'B', 'Mrs.',
 '1974-05-28', 'Female', 'married', '300 17th Street',        'Denver',       'CO', '80202', 'USA',
 '303-555-0156', 'patricia.reed@example.org',             15, '156', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(157, UNHEX(REPLACE(UUID(), '-', '')), 'Karen',     'Singh',     'N', 'Mrs.',
 '1971-09-14', 'Female', 'married', '1500 Walnut Street',     'Philadelphia', 'PA', '19102', 'USA',
 '215-555-0157', 'karen.singh@example.org',               16, '157', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(158, UNHEX(REPLACE(UUID(), '-', '')), 'Michelle',  'Park',      'H', 'Mrs.',
 '1973-12-02', 'Female', 'married', '200 5th Avenue',         'New York',     'NY', '10010', 'USA',
 '212-555-0158', 'michelle.park@example.org',             17, '158', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(159, UNHEX(REPLACE(UUID(), '-', '')), 'Rebecca',   'Santos',    'R', 'Mrs.',
 '1972-03-08', 'Female', 'married', '350 Brickell Avenue',    'Miami',        'FL', '33131', 'USA',
 '305-555-0159', 'rebecca.santos@example.org',            18, '159', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(160, UNHEX(REPLACE(UUID(), '-', '')), 'Cynthia',   'Hayes',     'P', 'Mrs.',
 '1970-06-21', 'Female', 'married', '525 N Tryon Street',     'Charlotte',    'NC', '28202', 'USA',
 '704-555-0160', 'cynthia.hayes@example.org',             19, '160', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(161, UNHEX(REPLACE(UUID(), '-', '')), 'Donna',     'Patel',     'C', 'Mrs.',
 '1973-10-30', 'Female', 'married', '1200 K Street NW',       'Washington',   'DC', '20005', 'USA',
 '202-555-0161', 'donna.patel@example.org',               21, '161', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(162, UNHEX(REPLACE(UUID(), '-', '')), 'Susan',     'Mitchell',  'G', 'Mrs.',
 '1971-01-17', 'Female', 'married', '300 Park Avenue',        'New York',     'NY', '10022', 'USA',
 '212-555-0162', 'susan.mitchell@example.org',            22, '162', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
-- West (facility 3) — 2 patients in CA
(163, UNHEX(REPLACE(UUID(), '-', '')), 'Lisa',      'Nakamura',  'K', 'Mrs.',
 '1972-08-09', 'Female', 'married', '1100 Wilshire Boulevard','Los Angeles',  'CA', '90017', 'USA',
 '213-555-0163', 'lisa.nakamura@example.org',             23, '163', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
-- Central (facility 4) — 1 patient in MO
(164, UNHEX(REPLACE(UUID(), '-', '')), 'Carol',     'Brennan',   'F', 'Mrs.',
 '1974-04-26', 'Female', 'married', '900 Walnut Street',      'Kansas City',  'MO', '64106', 'USA',
 '816-555-0164', 'carol.brennan@example.org',             24, '164', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
-- East (continued) — provider 25
(165, UNHEX(REPLACE(UUID(), '-', '')), 'Diana',     'Roberts',   'T', 'Mrs.',
 '1971-11-12', 'Female', 'married', '275 Peachtree Street',   'Atlanta',      'GA', '30303', 'USA',
 '404-555-0165', 'diana.roberts@example.org',             25, '165', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
-- Mountain (continued) — providers 26, 27
(166, UNHEX(REPLACE(UUID(), '-', '')), 'Wendy',     'Cho',       'S', 'Mrs.',
 '1973-06-05', 'Female', 'married', '410 N Tejon Street',     'Colorado Springs','CO','80903','USA',
 '719-555-0166', 'wendy.cho@example.org',                 26, '166', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
(167, UNHEX(REPLACE(UUID(), '-', '')), 'Pamela',    'Stewart',   'D', 'Mrs.',
 '1970-02-23', 'Female', 'married', '180 W South Temple',     'Salt Lake City','UT','84101','USA',
 '801-555-0167', 'pamela.stewart@example.org',            27, '167', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter'),
-- ---------------------------------------------------------------------------
-- Sarah Chen's panel (Boston, MA / facility 2 / provider 37, Charge Nurse)
-- 168-170: 3 regular patients (CHR / BH / HYA persona mix)
-- 171: dedicated diabetes demo target — referrer flag puts the diabetes-themed
--      chart bulk-inserts (in 07_clinical_data.sql) onto this patient, and
--      past_encounter.py picks her up at hydrate time to seed today's locked
--      Zoom telehealth encounter.
-- ---------------------------------------------------------------------------
(168, UNHEX(REPLACE(UUID(), '-', '')), 'Janet',     'Hill',      'M', 'Mrs.',
 '1971-09-30', 'Female', 'married', '155 Tremont Street',     'Boston',       'MA', '02111', 'USA',
 '617-555-0168', 'janet.hill@example.org',                37, '168', 'YES','YES','YES','portal','YES','YES','English','', NOW(), ''),
(169, UNHEX(REPLACE(UUID(), '-', '')), 'Tasha',     'Brooks',    'R', 'Ms.',
 '1988-04-12', 'Female', 'single',  '92 Charles Street',      'Boston',       'MA', '02114', 'USA',
 '617-555-0169', 'tasha.brooks@example.org',              37, '169', 'YES','YES','YES','portal','YES','YES','English','', NOW(), ''),
(170, UNHEX(REPLACE(UUID(), '-', '')), 'Erik',      'Nguyen',    'T', 'Mr.',
 '1997-11-08', 'Male',   'single',  '301 Boylston Street',    'Boston',       'MA', '02116', 'USA',
 '617-555-0170', 'erik.nguyen@example.org',               37, '170', 'YES','YES','YES','portal','YES','YES','English','', NOW(), ''),
(171, UNHEX(REPLACE(UUID(), '-', '')), 'Margaret',  'Walsh',     'K', 'Mrs.',
 '1969-07-19', 'Female', 'married', '88 Atlantic Avenue',     'Boston',       'MA', '02110', 'USA',
 '617-555-0171', 'margaret.walsh@example.org',            37, '171', 'YES','YES','YES','portal','YES','YES','English','', NOW(), 'Zoomly Demo Past Encounter');

-- Synthetic SSNs for all seeded demo patients. The 900 prefix keeps these out
-- of the issued SSN range while still giving each seeded patient a unique value.
UPDATE patient_data SET ss = CONCAT('90010', LPAD(pid, 4, '0')) WHERE pid BETWEEN 100 AND 171;
