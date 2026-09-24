-- Pharmaceutical Sales Database — Seed Data
-- Fictional pharma company "NovaPharma" with oncology and urology portfolio

-- ============================================================
-- PRODUCTS (40 products: 7 NovaPharma branded + 33 competitors)
-- ============================================================

INSERT INTO products (ndc, drug_name, generic_name, strength, form, brand_flag, specialty, market_category, market_subcategory, unit_conversion_factor, mg_equivalent) VALUES
-- NovaPharma branded products
('11111-0101-01', 'ZENOVAX', 'docetaxel', '80MG/4ML', 'Injectable', 1, 'Oncology', 'Taxanes', 'Docetaxel', 1.0, 80.0),
('11111-0101-02', 'ZENOVAX', 'docetaxel', '20MG/1ML', 'Injectable', 1, 'Oncology', 'Taxanes', 'Docetaxel', 0.25, 20.0),
('11111-0201-01', 'CARBOTREL', 'carboplatin', '450MG/45ML', 'Injectable', 1, 'Oncology', 'Platinum Compounds', 'Carboplatin', 1.0, 450.0),
('11111-0201-02', 'CARBOTREL', 'carboplatin', '150MG/15ML', 'Injectable', 1, 'Oncology', 'Platinum Compounds', 'Carboplatin', 0.333, 150.0),
('11111-0301-01', 'GEMTARA', 'gemcitabine', '1000MG', 'Injectable', 1, 'Oncology', 'Antimetabolites', 'Gemcitabine', 1.0, 1000.0),
('11111-0301-02', 'GEMTARA', 'gemcitabine', '200MG', 'Injectable', 1, 'Oncology', 'Antimetabolites', 'Gemcitabine', 0.2, 200.0),
('11111-0401-01', 'PAXELIUM', 'pemetrexed', '500MG', 'Injectable', 1, 'Oncology', 'Antimetabolites', 'Pemetrexed', 1.0, 500.0),
('11111-0401-02', 'PAXELIUM', 'pemetrexed', '100MG', 'Injectable', 1, 'Oncology', 'Antimetabolites', 'Pemetrexed', 0.2, 100.0),
('11111-0501-01', 'ONCOSETRON', 'palonosetron', '0.25MG/5ML', 'Injectable', 1, 'Oncology', 'Antiemetics', 'Palonosetron', 1.0, 0.25),
('11111-0601-01', 'CYCLONOVA', 'cyclophosphamide', '1G', 'Injectable', 1, 'Oncology', 'Alkylating Agents', 'Cyclophosphamide', 1.0, 1000.0),
('11111-0601-02', 'CYCLONOVA', 'cyclophosphamide', '500MG', 'Injectable', 1, 'Oncology', 'Alkylating Agents', 'Cyclophosphamide', 0.5, 500.0),
('11111-0701-01', 'LUPREX DEPOT', 'leuprolide', '22.5MG', 'Injectable', 1, 'Urology', 'GnRH Agonists', 'Leuprolide', 1.0, 22.5),
('11111-0701-02', 'LUPREX DEPOT', 'leuprolide', '7.5MG', 'Injectable', 1, 'Urology', 'GnRH Agonists', 'Leuprolide', 0.333, 7.5),

-- Competitor products — Oncology
('22222-0101-01', 'TAXOTERE', 'docetaxel', '80MG/4ML', 'Injectable', 0, 'Oncology', 'Taxanes', 'Docetaxel', 1.0, 80.0),
('22222-0101-02', 'DOCETAXEL GENERIC', 'docetaxel', '80MG/4ML', 'Injectable', 0, 'Oncology', 'Taxanes', 'Docetaxel', 1.0, 80.0),
('22222-0201-01', 'PARAPLATIN', 'carboplatin', '450MG/45ML', 'Injectable', 0, 'Oncology', 'Platinum Compounds', 'Carboplatin', 1.0, 450.0),
('22222-0201-02', 'CARBOPLATIN GENERIC', 'carboplatin', '150MG/15ML', 'Injectable', 0, 'Oncology', 'Platinum Compounds', 'Carboplatin', 0.333, 150.0),
('22222-0301-01', 'GEMZAR', 'gemcitabine', '1000MG', 'Injectable', 0, 'Oncology', 'Antimetabolites', 'Gemcitabine', 1.0, 1000.0),
('22222-0301-02', 'GEMCITABINE GENERIC', 'gemcitabine', '200MG', 'Injectable', 0, 'Oncology', 'Antimetabolites', 'Gemcitabine', 0.2, 200.0),
('22222-0401-01', 'ALIMTA', 'pemetrexed', '500MG', 'Injectable', 0, 'Oncology', 'Antimetabolites', 'Pemetrexed', 1.0, 500.0),
('22222-0401-02', 'PEMETREXED GENERIC', 'pemetrexed', '100MG', 'Injectable', 0, 'Oncology', 'Antimetabolites', 'Pemetrexed', 0.2, 100.0),
('22222-0501-01', 'ALOXI', 'palonosetron', '0.25MG/5ML', 'Injectable', 0, 'Oncology', 'Antiemetics', 'Palonosetron', 1.0, 0.25),
('22222-0501-02', 'PALONOSETRON GENERIC', 'palonosetron', '0.25MG/5ML', 'Injectable', 0, 'Oncology', 'Antiemetics', 'Palonosetron', 1.0, 0.25),
('22222-0601-01', 'CYTOXAN', 'cyclophosphamide', '1G', 'Injectable', 0, 'Oncology', 'Alkylating Agents', 'Cyclophosphamide', 1.0, 1000.0),
('22222-0601-02', 'CYCLOPHOSPHAMIDE GENERIC', 'cyclophosphamide', '500MG', 'Injectable', 0, 'Oncology', 'Alkylating Agents', 'Cyclophosphamide', 0.5, 500.0),

-- Competitor products — Urology
('22222-0701-01', 'LUPRON DEPOT', 'leuprolide', '22.5MG', 'Injectable', 0, 'Urology', 'GnRH Agonists', 'Leuprolide', 1.0, 22.5),
('22222-0701-02', 'ELIGARD', 'leuprolide', '22.5MG', 'Injectable', 0, 'Urology', 'GnRH Agonists', 'Leuprolide', 1.0, 22.5),
('22222-0801-01', 'FIRMAGON', 'degarelix', '240MG', 'Injectable', 0, 'Urology', 'GnRH Antagonists', 'Degarelix', 1.0, 240.0),
('22222-0901-01', 'XTANDI', 'enzalutamide', '40MG', 'Oral', 0, 'Urology', 'Antiandrogens', 'Enzalutamide', 1.0, 40.0),
('22222-1001-01', 'ZYTIGA', 'abiraterone', '250MG', 'Oral', 0, 'Urology', 'CYP17 Inhibitors', 'Abiraterone', 1.0, 250.0),

-- Additional oncology competitors
('22222-1101-01', 'KEYTRUDA', 'pembrolizumab', '100MG/4ML', 'Injectable', 0, 'Oncology', 'Immunotherapy', 'PD-1 Inhibitors', 1.0, 100.0),
('22222-1201-01', 'OPDIVO', 'nivolumab', '240MG/24ML', 'Injectable', 0, 'Oncology', 'Immunotherapy', 'PD-1 Inhibitors', 1.0, 240.0),
('22222-1301-01', 'AVASTIN', 'bevacizumab', '400MG/16ML', 'Injectable', 0, 'Oncology', 'Angiogenesis Inhibitors', 'VEGF Inhibitors', 1.0, 400.0),
('22222-1301-02', 'BEVACIZUMAB BIOSIMILAR', 'bevacizumab', '400MG/16ML', 'Injectable', 0, 'Oncology', 'Angiogenesis Inhibitors', 'VEGF Inhibitors', 1.0, 400.0),
('22222-1401-01', 'ABRAXANE', 'paclitaxel albumin', '100MG', 'Injectable', 0, 'Oncology', 'Taxanes', 'Paclitaxel', 1.0, 100.0),
('22222-1501-01', 'CISPLATIN GENERIC', 'cisplatin', '50MG/50ML', 'Injectable', 0, 'Oncology', 'Platinum Compounds', 'Cisplatin', 1.0, 50.0),
('22222-1601-01', 'OXALIPLATIN GENERIC', 'oxaliplatin', '100MG/20ML', 'Injectable', 0, 'Oncology', 'Platinum Compounds', 'Oxaliplatin', 1.0, 100.0),
('22222-1701-01', 'DOXORUBICIN GENERIC', 'doxorubicin', '50MG/25ML', 'Injectable', 0, 'Oncology', 'Anthracyclines', 'Doxorubicin', 1.0, 50.0),
('22222-1801-01', 'IRINOTECAN GENERIC', 'irinotecan', '100MG/5ML', 'Injectable', 0, 'Oncology', 'Topoisomerase Inhibitors', 'Irinotecan', 1.0, 100.0),
('22222-1901-01', 'ERBITUX', 'cetuximab', '200MG/100ML', 'Injectable', 0, 'Oncology', 'EGFR Inhibitors', 'Cetuximab', 1.0, 200.0);


-- ============================================================
-- ZIP TERRITORY MAPPING (200 entries across 8 territories)
-- ============================================================

INSERT INTO zip_territory (zip, state, territory_number, territory_name, region_number, region_name) VALUES
-- Northeast Region
('10001', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10002', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10003', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10010', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10016', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10019', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10021', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10029', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10032', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('10065', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('11201', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('11215', 'NY', 'T001', 'New York Metro', 'R01', 'Northeast'),
('02101', 'MA', 'T002', 'New England', 'R01', 'Northeast'),
('02114', 'MA', 'T002', 'New England', 'R01', 'Northeast'),
('02115', 'MA', 'T002', 'New England', 'R01', 'Northeast'),
('02118', 'MA', 'T002', 'New England', 'R01', 'Northeast'),
('02120', 'MA', 'T002', 'New England', 'R01', 'Northeast'),
('02215', 'MA', 'T002', 'New England', 'R01', 'Northeast'),
('06510', 'CT', 'T002', 'New England', 'R01', 'Northeast'),
('06511', 'CT', 'T002', 'New England', 'R01', 'Northeast'),
('06520', 'CT', 'T002', 'New England', 'R01', 'Northeast'),
('07101', 'NJ', 'T001', 'New York Metro', 'R01', 'Northeast'),
('07102', 'NJ', 'T001', 'New York Metro', 'R01', 'Northeast'),
('07103', 'NJ', 'T001', 'New York Metro', 'R01', 'Northeast'),
('08901', 'NJ', 'T001', 'New York Metro', 'R01', 'Northeast'),

-- Mid-Atlantic Region
('19104', 'PA', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('19107', 'PA', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('19111', 'PA', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('19140', 'PA', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('15213', 'PA', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('15232', 'PA', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('15260', 'PA', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('20001', 'DC', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('20007', 'DC', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('20010', 'DC', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('20037', 'DC', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('21201', 'MD', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('21205', 'MD', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('21218', 'MD', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),
('21231', 'MD', 'T003', 'Mid-Atlantic', 'R02', 'Mid-Atlantic'),

-- Southeast Region
('30301', 'GA', 'T004', 'Southeast', 'R03', 'Southeast'),
('30303', 'GA', 'T004', 'Southeast', 'R03', 'Southeast'),
('30308', 'GA', 'T004', 'Southeast', 'R03', 'Southeast'),
('30322', 'GA', 'T004', 'Southeast', 'R03', 'Southeast'),
('30332', 'GA', 'T004', 'Southeast', 'R03', 'Southeast'),
('33101', 'FL', 'T004', 'Southeast', 'R03', 'Southeast'),
('33125', 'FL', 'T004', 'Southeast', 'R03', 'Southeast'),
('33130', 'FL', 'T004', 'Southeast', 'R03', 'Southeast'),
('33136', 'FL', 'T004', 'Southeast', 'R03', 'Southeast'),
('33140', 'FL', 'T004', 'Southeast', 'R03', 'Southeast'),
('33155', 'FL', 'T004', 'Southeast', 'R03', 'Southeast'),
('33160', 'FL', 'T004', 'Southeast', 'R03', 'Southeast'),
('27599', 'NC', 'T004', 'Southeast', 'R03', 'Southeast'),
('27601', 'NC', 'T004', 'Southeast', 'R03', 'Southeast'),
('27607', 'NC', 'T004', 'Southeast', 'R03', 'Southeast'),
('27710', 'NC', 'T004', 'Southeast', 'R03', 'Southeast'),

-- Midwest Region
('60601', 'IL', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('60602', 'IL', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('60611', 'IL', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('60614', 'IL', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('60637', 'IL', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('60640', 'IL', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('48109', 'MI', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('48201', 'MI', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('48202', 'MI', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('44106', 'OH', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('44195', 'OH', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('43210', 'OH', 'T005', 'Great Lakes', 'R04', 'Midwest'),
('55401', 'MN', 'T006', 'Upper Midwest', 'R04', 'Midwest'),
('55402', 'MN', 'T006', 'Upper Midwest', 'R04', 'Midwest'),
('55414', 'MN', 'T006', 'Upper Midwest', 'R04', 'Midwest'),
('55455', 'MN', 'T006', 'Upper Midwest', 'R04', 'Midwest'),
('53705', 'WI', 'T006', 'Upper Midwest', 'R04', 'Midwest'),
('53706', 'WI', 'T006', 'Upper Midwest', 'R04', 'Midwest'),
('53792', 'WI', 'T006', 'Upper Midwest', 'R04', 'Midwest'),

-- South Central Region
('77001', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('77002', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('77004', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('77021', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('77025', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('77030', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('77054', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('75201', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('75235', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('75246', 'TX', 'T007', 'South Central', 'R05', 'South Central'),
('73104', 'OK', 'T007', 'South Central', 'R05', 'South Central'),
('70112', 'LA', 'T007', 'South Central', 'R05', 'South Central'),
('70115', 'LA', 'T007', 'South Central', 'R05', 'South Central'),

-- West Region
('90024', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('90033', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('90048', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('90095', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('91101', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('92093', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('92103', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('92121', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('94102', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('94110', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('94115', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('94143', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('94305', 'CA', 'T008', 'Pacific', 'R06', 'West'),
('97201', 'OR', 'T008', 'Pacific', 'R06', 'West'),
('97239', 'OR', 'T008', 'Pacific', 'R06', 'West'),
('98101', 'WA', 'T008', 'Pacific', 'R06', 'West'),
('98104', 'WA', 'T008', 'Pacific', 'R06', 'West'),
('98195', 'WA', 'T008', 'Pacific', 'R06', 'West'),

-- Mountain Region
('80045', 'CO', 'T009', 'Mountain', 'R06', 'West'),
('80202', 'CO', 'T009', 'Mountain', 'R06', 'West'),
('80218', 'CO', 'T009', 'Mountain', 'R06', 'West'),
('85004', 'AZ', 'T009', 'Mountain', 'R06', 'West'),
('85006', 'AZ', 'T009', 'Mountain', 'R06', 'West'),
('85259', 'AZ', 'T009', 'Mountain', 'R06', 'West'),
('84112', 'UT', 'T009', 'Mountain', 'R06', 'West'),
('84132', 'UT', 'T009', 'Mountain', 'R06', 'West'),
('89109', 'NV', 'T009', 'Mountain', 'R06', 'West'),
('87102', 'NM', 'T009', 'Mountain', 'R06', 'West');


-- ============================================================
-- ORGANIZATIONS (100 organizations with hierarchy)
-- ============================================================

-- Grandparent-level organizations (IDNs / Health Systems)
INSERT INTO organizations VALUES ('GP001', 'Memorial Health System', 'Grandparent', 'Active', 'IDN', 'Oncology', '10001 Park Ave', 'New York', 'NY', '10001', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('GP002', 'Atlantic Care Network', 'Grandparent', 'Active', 'IDN', 'Mixed', '200 Atlantic Blvd', 'Boston', 'MA', '02101', NULL, NULL, NULL, NULL, 'Unity', 0);
INSERT INTO organizations VALUES ('GP003', 'Keystone Health Partners', 'Grandparent', 'Active', 'IDN', 'Oncology', '500 Market St', 'Philadelphia', 'PA', '19104', NULL, NULL, NULL, NULL, 'VitalSource', 0);
INSERT INTO organizations VALUES ('GP004', 'Peachtree Medical Group', 'Grandparent', 'Active', 'IDN', 'Mixed', '100 Peachtree St', 'Atlanta', 'GA', '30301', NULL, NULL, NULL, NULL, 'ION', 0);
INSERT INTO organizations VALUES ('GP005', 'Great Lakes Health Alliance', 'Grandparent', 'Active', 'IDN', 'Oncology', '300 Michigan Ave', 'Chicago', 'IL', '60601', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('GP006', 'Lone Star Cancer Centers', 'Grandparent', 'Active', 'IDN', 'Oncology', '800 Texas Medical Dr', 'Houston', 'TX', '77001', NULL, NULL, NULL, NULL, 'ION', 0);
INSERT INTO organizations VALUES ('GP007', 'Pacific Oncology Network', 'Grandparent', 'Active', 'IDN', 'Oncology', '1000 Sunset Blvd', 'Los Angeles', 'CA', '90024', NULL, NULL, NULL, NULL, 'Unity', 0);
INSERT INTO organizations VALUES ('GP008', 'Mountain West Medical', 'Grandparent', 'Active', 'IDN', 'Urology', '600 Mountain View Dr', 'Denver', 'CO', '80202', NULL, NULL, NULL, NULL, 'VitalSource', 0);
INSERT INTO organizations VALUES ('GP009', 'Sunshine Health Network', 'Grandparent', 'Active', 'IDN', 'Mixed', '400 Biscayne Blvd', 'Miami', 'FL', '33101', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('GP010', 'Heartland Medical Group', 'Grandparent', 'Active', 'IDN', 'Urology', '200 Lake St', 'Minneapolis', 'MN', '55401', NULL, NULL, NULL, NULL, 'Unity', 0);
INSERT INTO organizations VALUES ('GP011', 'Northwest Health System', 'Grandparent', 'Active', 'IDN', 'Mixed', '700 Pine St', 'Seattle', 'WA', '98101', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('GP012', 'Capital Region Medical', 'Grandparent', 'Active', 'IDN', 'Oncology', '150 Constitution Ave', 'Washington', 'DC', '20001', NULL, NULL, NULL, NULL, 'ION', 0);
INSERT INTO organizations VALUES ('GP013', 'Valley Health System', 'Grandparent', 'Inactive', 'IDN', 'Oncology', '900 Valley Rd', 'Phoenix', 'AZ', '85004', NULL, NULL, NULL, NULL, NULL, 0);
INSERT INTO organizations VALUES ('GP014', 'Tri-State Urology Group', 'Grandparent', 'Active', 'IDN', 'Urology', '55 Park Ave', 'Newark', 'NJ', '07101', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('GP015', 'Southern Oncology Associates', 'Grandparent', 'Active', 'IDN', 'Oncology', '250 Magnolia Dr', 'Raleigh', 'NC', '27601', NULL, NULL, NULL, NULL, 'VitalSource', 0);

-- Parent-level organizations
INSERT INTO organizations VALUES ('PA001', 'Memorial Cancer Center', 'Parent', 'Active', 'Hospital', 'Oncology', '10001 Park Ave', 'New York', 'NY', '10001', NULL, NULL, 'GP001', 'Memorial Health System', 'Onmark', 0);
INSERT INTO organizations VALUES ('PA002', 'Memorial Urology Associates', 'Parent', 'Active', 'Clinic', 'Urology', '10002 Park Ave', 'New York', 'NY', '10002', NULL, NULL, 'GP001', 'Memorial Health System', 'Onmark', 0);
INSERT INTO organizations VALUES ('PA003', 'Atlantic Oncology Clinic', 'Parent', 'Active', 'Clinic', 'Oncology', '201 Atlantic Blvd', 'Boston', 'MA', '02114', NULL, NULL, 'GP002', 'Atlantic Care Network', 'Unity', 0);
INSERT INTO organizations VALUES ('PA004', 'Atlantic General Hospital', 'Parent', 'Active', 'Hospital', 'Mixed', '202 Atlantic Blvd', 'Boston', 'MA', '02115', NULL, NULL, 'GP002', 'Atlantic Care Network', 'Unity', 0);
INSERT INTO organizations VALUES ('PA005', 'Keystone Cancer Institute', 'Parent', 'Active', 'Hospital', 'Oncology', '501 Market St', 'Philadelphia', 'PA', '19104', NULL, NULL, 'GP003', 'Keystone Health Partners', 'VitalSource', 0);
INSERT INTO organizations VALUES ('PA006', 'Peachtree Oncology Center', 'Parent', 'Active', 'Clinic', 'Oncology', '101 Peachtree St', 'Atlanta', 'GA', '30303', NULL, NULL, 'GP004', 'Peachtree Medical Group', 'ION', 0);
INSERT INTO organizations VALUES ('PA007', 'Peachtree Infusion Services', 'Parent', 'Active', 'Specialty Pharmacy', 'Oncology', '102 Peachtree St', 'Atlanta', 'GA', '30308', NULL, NULL, 'GP004', 'Peachtree Medical Group', 'ION', 1);
INSERT INTO organizations VALUES ('PA008', 'Great Lakes Cancer Center', 'Parent', 'Active', 'Hospital', 'Oncology', '301 Michigan Ave', 'Chicago', 'IL', '60602', NULL, NULL, 'GP005', 'Great Lakes Health Alliance', 'Onmark', 0);
INSERT INTO organizations VALUES ('PA009', 'Great Lakes Community Oncology', 'Parent', 'Active', 'Clinic', 'Oncology', '302 Michigan Ave', 'Chicago', 'IL', '60611', NULL, NULL, 'GP005', 'Great Lakes Health Alliance', 'Onmark', 0);
INSERT INTO organizations VALUES ('PA010', 'Lone Star MD Anderson Affiliate', 'Parent', 'Active', 'Hospital', 'Oncology', '801 Texas Medical Dr', 'Houston', 'TX', '77030', NULL, NULL, 'GP006', 'Lone Star Cancer Centers', 'ION', 0);
INSERT INTO organizations VALUES ('PA011', 'Pacific UCLA Oncology', 'Parent', 'Active', 'Hospital', 'Oncology', '1001 Sunset Blvd', 'Los Angeles', 'CA', '90095', NULL, NULL, 'GP007', 'Pacific Oncology Network', 'Unity', 0);
INSERT INTO organizations VALUES ('PA012', 'Pacific Community Cancer', 'Parent', 'Active', 'Clinic', 'Oncology', '1002 Sunset Blvd', 'San Diego', 'CA', '92103', NULL, NULL, 'GP007', 'Pacific Oncology Network', 'Unity', 0);
INSERT INTO organizations VALUES ('PA013', 'Mountain Urology Specialists', 'Parent', 'Active', 'Clinic', 'Urology', '601 Mountain View Dr', 'Denver', 'CO', '80045', NULL, NULL, 'GP008', 'Mountain West Medical', 'VitalSource', 0);
INSERT INTO organizations VALUES ('PA014', 'Sunshine Cancer Institute', 'Parent', 'Active', 'Hospital', 'Oncology', '401 Biscayne Blvd', 'Miami', 'FL', '33136', NULL, NULL, 'GP009', 'Sunshine Health Network', 'Onmark', 0);
INSERT INTO organizations VALUES ('PA015', 'Heartland Urology Center', 'Parent', 'Active', 'Clinic', 'Urology', '201 Lake St', 'Minneapolis', 'MN', '55401', NULL, NULL, 'GP010', 'Heartland Medical Group', 'Unity', 0);
INSERT INTO organizations VALUES ('PA016', 'Northwest Cancer Specialists', 'Parent', 'Active', 'Clinic', 'Oncology', '701 Pine St', 'Seattle', 'WA', '98104', NULL, NULL, 'GP011', 'Northwest Health System', 'Onmark', 0);
INSERT INTO organizations VALUES ('PA017', 'Capital Oncology Group', 'Parent', 'Active', 'Hospital', 'Oncology', '151 Constitution Ave', 'Washington', 'DC', '20007', NULL, NULL, 'GP012', 'Capital Region Medical', 'ION', 0);
INSERT INTO organizations VALUES ('PA018', 'Tri-State Urology Clinic', 'Parent', 'Active', 'Clinic', 'Urology', '56 Park Ave', 'Newark', 'NJ', '07102', NULL, NULL, 'GP014', 'Tri-State Urology Group', 'Onmark', 0);
INSERT INTO organizations VALUES ('PA019', 'Southern Oncology Durham', 'Parent', 'Active', 'Clinic', 'Oncology', '251 Magnolia Dr', 'Durham', 'NC', '27710', NULL, NULL, 'GP015', 'Southern Oncology Associates', 'VitalSource', 0);
INSERT INTO organizations VALUES ('PA020', 'Lone Star Community Oncology', 'Parent', 'Active', 'Clinic', 'Oncology', '802 Texas Medical Dr', 'Dallas', 'TX', '75201', NULL, NULL, 'GP006', 'Lone Star Cancer Centers', 'ION', 0);

-- Facility-level organizations
INSERT INTO organizations VALUES ('FA001', 'Memorial Sloan East Infusion', 'Facility', 'Active', 'Hospital', 'Oncology', '10003 Park Ave', 'New York', 'NY', '10003', 'PA001', 'Memorial Cancer Center', 'GP001', 'Memorial Health System', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA002', 'Memorial Sloan West Clinic', 'Facility', 'Active', 'Clinic', 'Oncology', '10010 Broadway', 'New York', 'NY', '10010', 'PA001', 'Memorial Cancer Center', 'GP001', 'Memorial Health System', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA003', 'Memorial Urology - Midtown', 'Facility', 'Active', 'Clinic', 'Urology', '10016 Lexington Ave', 'New York', 'NY', '10016', 'PA002', 'Memorial Urology Associates', 'GP001', 'Memorial Health System', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA004', 'Atlantic Dana-Farber Clinic', 'Facility', 'Active', 'Hospital', 'Oncology', '300 Longwood Ave', 'Boston', 'MA', '02115', 'PA003', 'Atlantic Oncology Clinic', 'GP002', 'Atlantic Care Network', 'Unity', 0);
INSERT INTO organizations VALUES ('FA005', 'Atlantic MGH Infusion Center', 'Facility', 'Active', 'Hospital', 'Oncology', '55 Fruit St', 'Boston', 'MA', '02114', 'PA003', 'Atlantic Oncology Clinic', 'GP002', 'Atlantic Care Network', 'Unity', 0);
INSERT INTO organizations VALUES ('FA006', 'Atlantic General - Surgery', 'Facility', 'Active', 'Hospital', 'Mixed', '100 General Way', 'Boston', 'MA', '02118', 'PA004', 'Atlantic General Hospital', 'GP002', 'Atlantic Care Network', 'Unity', 0);
INSERT INTO organizations VALUES ('FA007', 'Keystone Penn Oncology', 'Facility', 'Active', 'Hospital', 'Oncology', '3400 Spruce St', 'Philadelphia', 'PA', '19104', 'PA005', 'Keystone Cancer Institute', 'GP003', 'Keystone Health Partners', 'VitalSource', 0);
INSERT INTO organizations VALUES ('FA008', 'Keystone Jefferson Infusion', 'Facility', 'Active', 'Hospital', 'Oncology', '111 S 11th St', 'Philadelphia', 'PA', '19107', 'PA005', 'Keystone Cancer Institute', 'GP003', 'Keystone Health Partners', 'VitalSource', 0);
INSERT INTO organizations VALUES ('FA009', 'Peachtree Emory Clinic', 'Facility', 'Active', 'Hospital', 'Oncology', '1365 Clifton Rd', 'Atlanta', 'GA', '30322', 'PA006', 'Peachtree Oncology Center', 'GP004', 'Peachtree Medical Group', 'ION', 0);
INSERT INTO organizations VALUES ('FA010', 'Peachtree 340B Pharmacy', 'Facility', 'Active', 'Specialty Pharmacy', 'Oncology', '1366 Clifton Rd', 'Atlanta', 'GA', '30322', 'PA007', 'Peachtree Infusion Services', 'GP004', 'Peachtree Medical Group', 'ION', 1);
INSERT INTO organizations VALUES ('FA011', 'Great Lakes Rush Oncology', 'Facility', 'Active', 'Hospital', 'Oncology', '1653 W Congress', 'Chicago', 'IL', '60612', 'PA008', 'Great Lakes Cancer Center', 'GP005', 'Great Lakes Health Alliance', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA012', 'Great Lakes Northwestern Onc', 'Facility', 'Active', 'Hospital', 'Oncology', '251 E Huron', 'Chicago', 'IL', '60611', 'PA008', 'Great Lakes Cancer Center', 'GP005', 'Great Lakes Health Alliance', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA013', 'Great Lakes Community Clinic A', 'Facility', 'Active', 'Clinic', 'Oncology', '500 Lake Shore Dr', 'Chicago', 'IL', '60614', 'PA009', 'Great Lakes Community Oncology', 'GP005', 'Great Lakes Health Alliance', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA014', 'Lone Star MD Anderson Main', 'Facility', 'Active', 'Hospital', 'Oncology', '1515 Holcombe Blvd', 'Houston', 'TX', '77030', 'PA010', 'Lone Star MD Anderson Affiliate', 'GP006', 'Lone Star Cancer Centers', 'ION', 0);
INSERT INTO organizations VALUES ('FA015', 'Lone Star MD Anderson Sugar Land', 'Facility', 'Active', 'Clinic', 'Oncology', '16811 SW Fwy', 'Houston', 'TX', '77054', 'PA010', 'Lone Star MD Anderson Affiliate', 'GP006', 'Lone Star Cancer Centers', 'ION', 0);
INSERT INTO organizations VALUES ('FA016', 'Pacific UCLA Westwood', 'Facility', 'Active', 'Hospital', 'Oncology', '10833 Le Conte Ave', 'Los Angeles', 'CA', '90095', 'PA011', 'Pacific UCLA Oncology', 'GP007', 'Pacific Oncology Network', 'Unity', 0);
INSERT INTO organizations VALUES ('FA017', 'Pacific UCLA Santa Monica', 'Facility', 'Active', 'Clinic', 'Oncology', '2825 Santa Monica Blvd', 'Santa Monica', 'CA', '90048', 'PA011', 'Pacific UCLA Oncology', 'GP007', 'Pacific Oncology Network', 'Unity', 0);
INSERT INTO organizations VALUES ('FA018', 'Pacific Moores UCSD Cancer', 'Facility', 'Active', 'Hospital', 'Oncology', '3855 Health Sciences Dr', 'San Diego', 'CA', '92093', 'PA012', 'Pacific Community Cancer', 'GP007', 'Pacific Oncology Network', 'Unity', 0);
INSERT INTO organizations VALUES ('FA019', 'Mountain UCHealth Urology', 'Facility', 'Active', 'Clinic', 'Urology', '12605 E 16th Ave', 'Denver', 'CO', '80045', 'PA013', 'Mountain Urology Specialists', 'GP008', 'Mountain West Medical', 'VitalSource', 0);
INSERT INTO organizations VALUES ('FA020', 'Sunshine Sylvester Cancer', 'Facility', 'Active', 'Hospital', 'Oncology', '1475 NW 12th Ave', 'Miami', 'FL', '33136', 'PA014', 'Sunshine Cancer Institute', 'GP009', 'Sunshine Health Network', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA021', 'Sunshine Baptist Health Onc', 'Facility', 'Active', 'Hospital', 'Oncology', '8900 N Kendall Dr', 'Miami', 'FL', '33155', 'PA014', 'Sunshine Cancer Institute', 'GP009', 'Sunshine Health Network', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA022', 'Heartland Mayo Urology', 'Facility', 'Active', 'Hospital', 'Urology', '200 First St SW', 'Rochester', 'MN', '55402', 'PA015', 'Heartland Urology Center', 'GP010', 'Heartland Medical Group', 'Unity', 0);
INSERT INTO organizations VALUES ('FA023', 'Heartland Park Nicollet Uro', 'Facility', 'Active', 'Clinic', 'Urology', '6500 Excelsior Blvd', 'Minneapolis', 'MN', '55414', 'PA015', 'Heartland Urology Center', 'GP010', 'Heartland Medical Group', 'Unity', 0);
INSERT INTO organizations VALUES ('FA024', 'Northwest Fred Hutch', 'Facility', 'Active', 'Hospital', 'Oncology', '1100 Fairview Ave N', 'Seattle', 'WA', '98195', 'PA016', 'Northwest Cancer Specialists', 'GP011', 'Northwest Health System', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA025', 'Capital Georgetown Oncology', 'Facility', 'Active', 'Hospital', 'Oncology', '3800 Reservoir Rd', 'Washington', 'DC', '20007', 'PA017', 'Capital Oncology Group', 'GP012', 'Capital Region Medical', 'ION', 0);
INSERT INTO organizations VALUES ('FA026', 'Capital Johns Hopkins Onc', 'Facility', 'Active', 'Hospital', 'Oncology', '600 N Wolfe St', 'Baltimore', 'MD', '21205', 'PA017', 'Capital Oncology Group', 'GP012', 'Capital Region Medical', 'ION', 0);
INSERT INTO organizations VALUES ('FA027', 'Tri-State Urology Newark', 'Facility', 'Active', 'Clinic', 'Urology', '57 Park Ave', 'Newark', 'NJ', '07103', 'PA018', 'Tri-State Urology Clinic', 'GP014', 'Tri-State Urology Group', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA028', 'Tri-State Urology Brunswick', 'Facility', 'Active', 'Clinic', 'Urology', '100 Hospital Dr', 'New Brunswick', 'NJ', '08901', 'PA018', 'Tri-State Urology Clinic', 'GP014', 'Tri-State Urology Group', 'Onmark', 0);
INSERT INTO organizations VALUES ('FA029', 'Southern Duke Oncology', 'Facility', 'Active', 'Hospital', 'Oncology', '10 Bryan Searle Dr', 'Durham', 'NC', '27710', 'PA019', 'Southern Oncology Durham', 'GP015', 'Southern Oncology Associates', 'VitalSource', 0);
INSERT INTO organizations VALUES ('FA030', 'Lone Star Baylor Oncology', 'Facility', 'Active', 'Clinic', 'Oncology', '3500 Gaston Ave', 'Dallas', 'TX', '75246', 'PA020', 'Lone Star Community Oncology', 'GP006', 'Lone Star Cancer Centers', 'ION', 0);

-- Standalone facilities (no parent hierarchy)
INSERT INTO organizations VALUES ('SA001', 'Cleveland Clinic Oncology', 'Facility', 'Active', 'Hospital', 'Oncology', '9500 Euclid Ave', 'Cleveland', 'OH', '44195', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('SA002', 'OHSU Knight Cancer', 'Facility', 'Active', 'Hospital', 'Oncology', '3181 SW Sam Jackson', 'Portland', 'OR', '97239', NULL, NULL, NULL, NULL, 'Unity', 0);
INSERT INTO organizations VALUES ('SA003', 'Yale Cancer Center', 'Facility', 'Active', 'Hospital', 'Oncology', '333 Cedar St', 'New Haven', 'CT', '06510', NULL, NULL, NULL, NULL, 'VitalSource', 0);
INSERT INTO organizations VALUES ('SA004', 'UPMC Hillman Cancer', 'Facility', 'Active', 'Hospital', 'Oncology', '5115 Centre Ave', 'Pittsburgh', 'PA', '15232', NULL, NULL, NULL, NULL, 'ION', 0);
INSERT INTO organizations VALUES ('SA005', 'Moffitt Cancer Center', 'Facility', 'Active', 'Hospital', 'Oncology', '12902 Magnolia Dr', 'Tampa', 'FL', '33612', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('SA006', 'Michigan Medicine Urology', 'Facility', 'Active', 'Hospital', 'Urology', '1500 E Medical Center Dr', 'Ann Arbor', 'MI', '48109', NULL, NULL, NULL, NULL, 'Unity', 0);
INSERT INTO organizations VALUES ('SA007', 'Stanford Cancer Center', 'Facility', 'Active', 'Hospital', 'Oncology', '875 Blake Wilbur Dr', 'Palo Alto', 'CA', '94305', NULL, NULL, NULL, NULL, 'ION', 0);
INSERT INTO organizations VALUES ('SA008', 'UCSF Helen Diller Cancer', 'Facility', 'Active', 'Hospital', 'Oncology', '1600 Divisadero St', 'San Francisco', 'CA', '94115', NULL, NULL, NULL, NULL, 'Unity', 0);
INSERT INTO organizations VALUES ('SA009', 'Mayo Clinic Arizona Onc', 'Facility', 'Active', 'Hospital', 'Oncology', '5881 E Mayo Blvd', 'Phoenix', 'AZ', '85259', NULL, NULL, NULL, NULL, 'VitalSource', 0);
INSERT INTO organizations VALUES ('SA010', 'Ochsner Cancer Institute', 'Facility', 'Active', 'Hospital', 'Oncology', '1514 Jefferson Hwy', 'New Orleans', 'LA', '70112', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('SA011', 'UW Carbone Cancer Center', 'Facility', 'Active', 'Hospital', 'Oncology', '600 Highland Ave', 'Madison', 'WI', '53792', NULL, NULL, NULL, NULL, 'Unity', 0);
INSERT INTO organizations VALUES ('SA012', 'Government VA Medical - DC', 'Facility', 'Active', 'Government', 'Mixed', '50 Irving St NW', 'Washington', 'DC', '20010', NULL, NULL, NULL, NULL, NULL, 0);
INSERT INTO organizations VALUES ('SA013', 'Brooklyn Oncology Associates', 'Facility', 'Active', 'Clinic', 'Oncology', '450 Clarkson Ave', 'Brooklyn', 'NY', '11201', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('SA014', 'Detroit Medical Center Onc', 'Facility', 'Active', 'Hospital', 'Oncology', '4201 St Antoine', 'Detroit', 'MI', '48201', NULL, NULL, NULL, NULL, 'ION', 0);
INSERT INTO organizations VALUES ('SA015', 'Huntsman Cancer Institute', 'Facility', 'Active', 'Hospital', 'Oncology', '2000 Circle of Hope', 'Salt Lake City', 'UT', '84112', NULL, NULL, NULL, NULL, 'VitalSource', 0);
INSERT INTO organizations VALUES ('SA016', 'Desert Urology Clinic', 'Facility', 'Active', 'Clinic', 'Urology', '5601 N 19th Ave', 'Phoenix', 'AZ', '85006', NULL, NULL, NULL, NULL, NULL, 0);
INSERT INTO organizations VALUES ('SA017', 'UNM Comprehensive Cancer', 'Facility', 'Active', 'Hospital', 'Mixed', '1201 Camino de Salud', 'Albuquerque', 'NM', '87102', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('SA018', 'Harlem Hospital Oncology', 'Facility', 'Active', 'Hospital', 'Oncology', '506 Lenox Ave', 'New York', 'NY', '10029', NULL, NULL, NULL, NULL, NULL, 1);
INSERT INTO organizations VALUES ('SA019', 'OSU Comprehensive Cancer', 'Facility', 'Active', 'Hospital', 'Oncology', '460 W 10th Ave', 'Columbus', 'OH', '43210', NULL, NULL, NULL, NULL, 'Onmark', 0);
INSERT INTO organizations VALUES ('SA020', 'Las Vegas Cancer Center', 'Facility', 'Active', 'Clinic', 'Oncology', '3006 S Maryland Pkwy', 'Las Vegas', 'NV', '89109', NULL, NULL, NULL, NULL, NULL, 0);


-- ============================================================
-- SALES (5000 transactions across 52 weeks)
-- Generated using realistic distribution patterns
-- ============================================================

-- Helper: seed sales span a few recent weeks (the full generated dataset covers ~156 weeks / 3 years)
-- Data sources: 'distributor' (NovaPharma paid demand), 'hub_dispense' (free drug), 'market_data' (third-party market research)
-- Quarters: 2026-Q3 (current), 2026-Q2, 2026-Q1, 2025-Q4

-- NovaPharma branded sales via distributor channel — large accounts
-- Memorial Health System (GP001) facilities
INSERT INTO sales (org_id, ndc, drug_name, data_source, brand_flag, pack_units, total_mg, wac, transaction_date, week_ending_date, state, specialty, period_wk, period_mo, period_qtr, wk_offset, mo_offset) VALUES
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 5.0, 400.0, 2475.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 8.0, 640.0, 3960.00, '2026-09-08', '2026-09-13', 'NY', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 12.0, 5400.0, 4860.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA001', '11111-0301-01', 'GEMTARA', 'distributor', 1, 6.0, 6000.0, 3600.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA001', '11111-0401-01', 'PAXELIUM', 'distributor', 1, 4.0, 2000.0, 3160.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA001', '11111-0501-01', 'ONCOSETRON', 'distributor', 1, 15.0, 3.75, 8700.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA002', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 3.0, 240.0, 1485.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA002', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 6.0, 2700.0, 2430.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA003', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 8.0, 180.0, 6400.00, '2026-09-15', '2026-09-20', 'NY', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Hub dispense (free drug program)
('FA001', '11111-0101-01', 'ZENOVAX', 'hub_dispense', 1, 2.0, 160.0, 0.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA009', '11111-0301-01', 'GEMTARA', 'hub_dispense', 1, 1.0, 1000.0, 0.00, '2026-09-15', '2026-09-20', 'GA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Market data (competitor + total market volume from third-party research)
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 10.0, 800.0, 6500.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA001', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 20.0, 1600.0, 4000.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA001', '22222-0201-01', 'PARAPLATIN', 'market_data', 0, 8.0, 3600.0, 3200.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA001', '22222-0301-01', 'GEMZAR', 'market_data', 0, 12.0, 12000.0, 5400.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Atlantic Care Network (GP002) facilities
('FA004', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 6.0, 480.0, 2970.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA004', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 10.0, 4500.0, 4050.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA004', '11111-0301-01', 'GEMTARA', 'distributor', 1, 8.0, 8000.0, 4800.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA004', '11111-0401-01', 'PAXELIUM', 'distributor', 1, 3.0, 1500.0, 2370.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA005', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 4.0, 320.0, 1980.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA005', '11111-0601-01', 'CYCLONOVA', 'distributor', 1, 5.0, 5000.0, 8750.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Market data for Atlantic
('FA004', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 8.0, 640.0, 5200.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA004', '22222-0201-02', 'CARBOPLATIN GENERIC', 'market_data', 0, 15.0, 2250.0, 1500.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA004', '22222-0301-02', 'GEMCITABINE GENERIC', 'market_data', 0, 10.0, 2000.0, 800.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Keystone Health Partners (GP003) — Philadelphia
('FA007', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 7.0, 560.0, 3465.00, '2026-09-15', '2026-09-20', 'PA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA007', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 8.0, 3600.0, 3240.00, '2026-09-15', '2026-09-20', 'PA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA007', '11111-0301-01', 'GEMTARA', 'distributor', 1, 5.0, 5000.0, 3000.00, '2026-09-15', '2026-09-20', 'PA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA008', '11111-0401-01', 'PAXELIUM', 'distributor', 1, 6.0, 3000.0, 4740.00, '2026-09-15', '2026-09-20', 'PA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA007', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 18.0, 1440.0, 3600.00, '2026-09-15', '2026-09-20', 'PA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA007', '22222-0201-01', 'PARAPLATIN', 'market_data', 0, 10.0, 4500.0, 4000.00, '2026-09-15', '2026-09-20', 'PA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Peachtree Medical Group (GP004) — Atlanta / 340B entity
('FA009', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 4.0, 320.0, 1980.00, '2026-09-15', '2026-09-20', 'GA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA009', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 6.0, 2700.0, 2430.00, '2026-09-15', '2026-09-20', 'GA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA010', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 3.0, 240.0, 1485.00, '2026-09-15', '2026-09-20', 'GA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA009', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 6.0, 480.0, 3900.00, '2026-09-15', '2026-09-20', 'GA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA009', '22222-0601-01', 'CYTOXAN', 'market_data', 0, 8.0, 8000.0, 3200.00, '2026-09-15', '2026-09-20', 'GA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Great Lakes (GP005) — Chicago
('FA011', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 9.0, 720.0, 4455.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 14.0, 6300.0, 5670.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '11111-0301-01', 'GEMTARA', 'distributor', 1, 10.0, 10000.0, 6000.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA012', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 5.0, 400.0, 2475.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA012', '11111-0401-01', 'PAXELIUM', 'distributor', 1, 7.0, 3500.0, 5530.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA013', '11111-0601-01', 'CYCLONOVA', 'distributor', 1, 4.0, 4000.0, 7000.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 12.0, 960.0, 7800.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '22222-0301-01', 'GEMZAR', 'market_data', 0, 15.0, 15000.0, 6750.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '22222-0401-01', 'ALIMTA', 'market_data', 0, 8.0, 4000.0, 6320.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Lone Star (GP006) — Texas
('FA014', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 12.0, 960.0, 5940.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 18.0, 8100.0, 7290.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '11111-0301-01', 'GEMTARA', 'distributor', 1, 14.0, 14000.0, 8400.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '11111-0401-01', 'PAXELIUM', 'distributor', 1, 8.0, 4000.0, 6320.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '11111-0501-01', 'ONCOSETRON', 'distributor', 1, 20.0, 5.0, 11600.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA015', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 6.0, 480.0, 2970.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA030', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 5.0, 2250.0, 2026.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 15.0, 1200.0, 9750.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '22222-0201-01', 'PARAPLATIN', 'market_data', 0, 20.0, 9000.0, 8000.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '22222-0301-01', 'GEMZAR', 'market_data', 0, 18.0, 18000.0, 8100.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '22222-1101-01', 'KEYTRUDA', 'market_data', 0, 25.0, 2500.0, 37500.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Pacific (GP007) — California
('FA016', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 8.0, 640.0, 3960.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA016', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 12.0, 5400.0, 4860.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA016', '11111-0301-01', 'GEMTARA', 'distributor', 1, 9.0, 9000.0, 5400.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA017', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 4.0, 320.0, 1980.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA018', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 7.0, 3150.0, 2835.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA016', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 10.0, 800.0, 6500.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA016', '22222-0201-01', 'PARAPLATIN', 'market_data', 0, 12.0, 5400.0, 4800.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA016', '22222-1201-01', 'OPDIVO', 'market_data', 0, 8.0, 1920.0, 12000.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Mountain West / Urology (GP008)
('FA019', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 12.0, 270.0, 9600.00, '2026-09-15', '2026-09-20', 'CO', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA019', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 20.0, 450.0, 16000.00, '2026-09-15', '2026-09-20', 'CO', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA019', '22222-0701-02', 'ELIGARD', 'market_data', 0, 10.0, 225.0, 7500.00, '2026-09-15', '2026-09-20', 'CO', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Sunshine Health Network (GP009) — Miami
('FA020', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 7.0, 560.0, 3465.00, '2026-09-15', '2026-09-20', 'FL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA020', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 9.0, 4050.0, 3645.00, '2026-09-15', '2026-09-20', 'FL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA021', '11111-0301-01', 'GEMTARA', 'distributor', 1, 6.0, 6000.0, 3600.00, '2026-09-15', '2026-09-20', 'FL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA020', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 14.0, 1120.0, 2800.00, '2026-09-15', '2026-09-20', 'FL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Heartland / Urology (GP010) — Minnesota
('FA022', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 15.0, 337.5, 12000.00, '2026-09-15', '2026-09-20', 'MN', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA023', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 8.0, 180.0, 6400.00, '2026-09-15', '2026-09-20', 'MN', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 25.0, 562.5, 20000.00, '2026-09-15', '2026-09-20', 'MN', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA022', '22222-0801-01', 'FIRMAGON', 'market_data', 0, 5.0, 1200.0, 4500.00, '2026-09-15', '2026-09-20', 'MN', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Standalone facilities — current week
('SA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 10.0, 800.0, 4950.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 15.0, 6750.0, 6075.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA001', '11111-0301-01', 'GEMTARA', 'distributor', 1, 12.0, 12000.0, 7200.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 14.0, 1120.0, 9100.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA001', '22222-0301-01', 'GEMZAR', 'market_data', 0, 16.0, 16000.0, 7200.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA002', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 5.0, 400.0, 2475.00, '2026-09-15', '2026-09-20', 'OR', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA002', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 8.0, 3600.0, 3240.00, '2026-09-15', '2026-09-20', 'OR', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA003', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 6.0, 480.0, 2970.00, '2026-09-15', '2026-09-20', 'CT', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA003', '11111-0401-01', 'PAXELIUM', 'distributor', 1, 5.0, 2500.0, 3950.00, '2026-09-15', '2026-09-20', 'CT', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA004', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 10.0, 4500.0, 4050.00, '2026-09-15', '2026-09-20', 'PA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA005', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 8.0, 640.0, 3960.00, '2026-09-15', '2026-09-20', 'FL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA005', '11111-0301-01', 'GEMTARA', 'distributor', 1, 7.0, 7000.0, 4200.00, '2026-09-15', '2026-09-20', 'FL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA006', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 10.0, 225.0, 8000.00, '2026-09-15', '2026-09-20', 'MI', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA006', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 18.0, 405.0, 14400.00, '2026-09-15', '2026-09-20', 'MI', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA007', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 7.0, 560.0, 3465.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA007', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 11.0, 4950.0, 4455.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA008', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 6.0, 480.0, 2970.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA008', '11111-0301-01', 'GEMTARA', 'distributor', 1, 8.0, 8000.0, 4800.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA009', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 6.0, 2700.0, 2430.00, '2026-09-15', '2026-09-20', 'AZ', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA010', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 4.0, 320.0, 1980.00, '2026-09-15', '2026-09-20', 'LA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA010', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 7.0, 3150.0, 2835.00, '2026-09-15', '2026-09-20', 'LA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- ============================================================
-- HISTORICAL DATA — Last 4 weeks (wk_offset 1-4), same patterns scaled
-- ============================================================

-- Week -1 (wk_offset=1)
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 6.0, 480.0, 2970.00, '2026-09-08', '2026-09-13', 'NY', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 10.0, 4500.0, 4050.00, '2026-09-08', '2026-09-13', 'NY', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA001', '11111-0301-01', 'GEMTARA', 'distributor', 1, 7.0, 7000.0, 4200.00, '2026-09-08', '2026-09-13', 'NY', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA004', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 5.0, 400.0, 2475.00, '2026-09-08', '2026-09-13', 'MA', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA004', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 8.0, 3600.0, 3240.00, '2026-09-08', '2026-09-13', 'MA', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA011', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 8.0, 640.0, 3960.00, '2026-09-08', '2026-09-13', 'IL', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA011', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 12.0, 5400.0, 4860.00, '2026-09-08', '2026-09-13', 'IL', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA014', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 11.0, 880.0, 5445.00, '2026-09-08', '2026-09-13', 'TX', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA014', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 16.0, 7200.0, 6480.00, '2026-09-08', '2026-09-13', 'TX', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA016', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 7.0, 560.0, 3465.00, '2026-09-08', '2026-09-13', 'CA', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('SA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 9.0, 720.0, 4455.00, '2026-09-08', '2026-09-13', 'OH', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('SA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 13.0, 5850.0, 5265.00, '2026-09-08', '2026-09-13', 'OH', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA022', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 14.0, 315.0, 11200.00, '2026-09-08', '2026-09-13', 'MN', 'Urology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
-- Market data week -1
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 11.0, 880.0, 7150.00, '2026-09-08', '2026-09-13', 'NY', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA001', '22222-0301-01', 'GEMZAR', 'market_data', 0, 14.0, 14000.0, 6300.00, '2026-09-08', '2026-09-13', 'NY', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA011', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 13.0, 1040.0, 8450.00, '2026-09-08', '2026-09-13', 'IL', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),
('FA014', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 16.0, 1280.0, 10400.00, '2026-09-08', '2026-09-13', 'TX', 'Oncology', '2026-W37', '2026-09', '2026-Q3', 1, 0),

-- ============================================================
-- HISTORICAL DATA — Months 1-6 (mo_offset 1-6, for trend analysis)
-- Aggregated monthly data for major accounts
-- ============================================================

-- Month -1 (August 2026)
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 22.0, 1760.0, 10890.00, '2026-08-25', '2026-08-30', 'NY', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 40.0, 18000.0, 16200.00, '2026-08-25', '2026-08-30', 'NY', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA001', '11111-0301-01', 'GEMTARA', 'distributor', 1, 28.0, 28000.0, 16800.00, '2026-08-25', '2026-08-30', 'NY', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA004', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 20.0, 1600.0, 9900.00, '2026-08-25', '2026-08-30', 'MA', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA004', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 35.0, 15750.0, 14175.00, '2026-08-25', '2026-08-30', 'MA', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA011', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 35.0, 2800.0, 17325.00, '2026-08-25', '2026-08-30', 'IL', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA011', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 50.0, 22500.0, 20260.00, '2026-08-25', '2026-08-30', 'IL', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA014', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 45.0, 3600.0, 22275.00, '2026-08-25', '2026-08-30', 'TX', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA014', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 65.0, 29250.0, 26325.00, '2026-08-25', '2026-08-30', 'TX', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA014', '11111-0301-01', 'GEMTARA', 'distributor', 1, 55.0, 55000.0, 33000.00, '2026-08-25', '2026-08-30', 'TX', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA016', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 30.0, 2400.0, 14850.00, '2026-08-25', '2026-08-30', 'CA', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA016', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 45.0, 20260.0, 18225.00, '2026-08-25', '2026-08-30', 'CA', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('SA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 38.0, 3040.0, 18810.00, '2026-08-25', '2026-08-30', 'OH', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('SA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 55.0, 24750.0, 22275.00, '2026-08-25', '2026-08-30', 'OH', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA022', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 55.0, 1237.5, 44000.00, '2026-08-25', '2026-08-30', 'MN', 'Urology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA019', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 45.0, 1012.5, 36000.00, '2026-08-25', '2026-08-30', 'CO', 'Urology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
-- Market data month -1
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 45.0, 3600.0, 29250.00, '2026-08-25', '2026-08-30', 'NY', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA001', '22222-0301-01', 'GEMZAR', 'market_data', 0, 55.0, 55000.0, 24750.00, '2026-08-25', '2026-08-30', 'NY', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA011', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 50.0, 4000.0, 32500.00, '2026-08-25', '2026-08-30', 'IL', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA014', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 60.0, 4800.0, 39000.00, '2026-08-25', '2026-08-30', 'TX', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA014', '22222-0301-01', 'GEMZAR', 'market_data', 0, 70.0, 70000.0, 31500.00, '2026-08-25', '2026-08-30', 'TX', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 90.0, 2026.0, 72000.00, '2026-08-25', '2026-08-30', 'MN', 'Urology', '2026-W35', '2026-08', '2026-Q3', 4, 1),

-- Month -2 (July 2026)
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 20.0, 1600.0, 9900.00, '2026-07-28', '2026-08-02', 'NY', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 38.0, 17100.0, 15390.00, '2026-07-28', '2026-08-02', 'NY', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA001', '11111-0301-01', 'GEMTARA', 'distributor', 1, 25.0, 25000.0, 15000.00, '2026-07-28', '2026-08-02', 'NY', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA004', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 18.0, 1440.0, 8910.00, '2026-07-28', '2026-08-02', 'MA', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA011', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 32.0, 2560.0, 15840.00, '2026-07-28', '2026-08-02', 'IL', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA011', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 48.0, 21600.0, 19440.00, '2026-07-28', '2026-08-02', 'IL', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA014', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 42.0, 3360.0, 20790.00, '2026-07-28', '2026-08-02', 'TX', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA014', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 60.0, 27000.0, 24300.00, '2026-07-28', '2026-08-02', 'TX', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA016', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 28.0, 2240.0, 13860.00, '2026-07-28', '2026-08-02', 'CA', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('SA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 35.0, 2800.0, 17325.00, '2026-07-28', '2026-08-02', 'OH', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA022', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 50.0, 1125.0, 40000.00, '2026-07-28', '2026-08-02', 'MN', 'Urology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
-- Market data month -2
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 42.0, 3360.0, 27300.00, '2026-07-28', '2026-08-02', 'NY', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA011', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 48.0, 3840.0, 31200.00, '2026-07-28', '2026-08-02', 'IL', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA014', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 55.0, 4400.0, 35750.00, '2026-07-28', '2026-08-02', 'TX', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),

-- Month -3 (June 2026) — Q2
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 18.0, 1440.0, 8910.00, '2026-06-23', '2026-06-28', 'NY', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 35.0, 15750.0, 14175.00, '2026-06-23', '2026-06-28', 'NY', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA001', '11111-0301-01', 'GEMTARA', 'distributor', 1, 22.0, 22000.0, 13200.00, '2026-06-23', '2026-06-28', 'NY', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA004', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 15.0, 1200.0, 7425.00, '2026-06-23', '2026-06-28', 'MA', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA004', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 28.0, 12600.0, 11340.00, '2026-06-23', '2026-06-28', 'MA', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA011', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 28.0, 2240.0, 13860.00, '2026-06-23', '2026-06-28', 'IL', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA011', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 42.0, 18900.0, 17010.00, '2026-06-23', '2026-06-28', 'IL', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA014', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 38.0, 3040.0, 18810.00, '2026-06-23', '2026-06-28', 'TX', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA014', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 55.0, 24750.0, 22275.00, '2026-06-23', '2026-06-28', 'TX', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA014', '11111-0301-01', 'GEMTARA', 'distributor', 1, 48.0, 48000.0, 28800.00, '2026-06-23', '2026-06-28', 'TX', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA016', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 25.0, 2000.0, 12375.00, '2026-06-23', '2026-06-28', 'CA', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('SA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 32.0, 2560.0, 15840.00, '2026-06-23', '2026-06-28', 'OH', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA022', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 48.0, 1080.0, 38400.00, '2026-06-23', '2026-06-28', 'MN', 'Urology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA019', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 40.0, 900.0, 32000.00, '2026-06-23', '2026-06-28', 'CO', 'Urology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
-- Market data month -3
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 40.0, 3200.0, 26000.00, '2026-06-23', '2026-06-28', 'NY', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA001', '22222-0301-01', 'GEMZAR', 'market_data', 0, 50.0, 50000.0, 22500.00, '2026-06-23', '2026-06-28', 'NY', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA011', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 45.0, 3600.0, 29250.00, '2026-06-23', '2026-06-28', 'IL', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA014', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 52.0, 4160.0, 33800.00, '2026-06-23', '2026-06-28', 'TX', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 85.0, 1912.5, 68000.00, '2026-06-23', '2026-06-28', 'MN', 'Urology', '2026-W26', '2026-06', '2026-Q2', 12, 3),

-- Month -4 (May 2026) — Q2
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 16.0, 1280.0, 7920.00, '2026-05-26', '2026-05-31', 'NY', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 32.0, 14400.0, 12960.00, '2026-05-26', '2026-05-31', 'NY', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA004', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 14.0, 1120.0, 6930.00, '2026-05-26', '2026-05-31', 'MA', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA011', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 25.0, 2000.0, 12375.00, '2026-05-26', '2026-05-31', 'IL', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA011', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 38.0, 17100.0, 15390.00, '2026-05-26', '2026-05-31', 'IL', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA014', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 35.0, 2800.0, 17325.00, '2026-05-26', '2026-05-31', 'TX', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA014', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 50.0, 22500.0, 20260.00, '2026-05-26', '2026-05-31', 'TX', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA016', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 22.0, 1760.0, 10890.00, '2026-05-26', '2026-05-31', 'CA', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('SA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 30.0, 2400.0, 14850.00, '2026-05-26', '2026-05-31', 'OH', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA022', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 45.0, 1012.5, 36000.00, '2026-05-26', '2026-05-31', 'MN', 'Urology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
-- Market data month -4
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 38.0, 3040.0, 24700.00, '2026-05-26', '2026-05-31', 'NY', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA011', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 42.0, 3360.0, 27300.00, '2026-05-26', '2026-05-31', 'IL', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA014', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 48.0, 3840.0, 31200.00, '2026-05-26', '2026-05-31', 'TX', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),

-- Month -5 (April 2026) — Q2
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 15.0, 1200.0, 7425.00, '2026-04-28', '2026-05-03', 'NY', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 30.0, 13500.0, 12150.00, '2026-04-28', '2026-05-03', 'NY', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA011', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 22.0, 1760.0, 10890.00, '2026-04-28', '2026-05-03', 'IL', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA014', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 30.0, 2400.0, 14850.00, '2026-04-28', '2026-05-03', 'TX', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA014', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 45.0, 20260.0, 18225.00, '2026-04-28', '2026-05-03', 'TX', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA016', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 20.0, 1600.0, 9900.00, '2026-04-28', '2026-05-03', 'CA', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('SA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 28.0, 2240.0, 13860.00, '2026-04-28', '2026-05-03', 'OH', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA022', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 42.0, 945.0, 33600.00, '2026-04-28', '2026-05-03', 'MN', 'Urology', '2026-W18', '2026-04', '2026-Q2', 20, 5),

-- Month -6 (March 2026) — Q1
('FA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 12.0, 960.0, 5940.00, '2026-03-24', '2026-03-29', 'NY', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA001', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 25.0, 11250.0, 10125.00, '2026-03-24', '2026-03-29', 'NY', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA001', '11111-0301-01', 'GEMTARA', 'distributor', 1, 18.0, 18000.0, 10800.00, '2026-03-24', '2026-03-29', 'NY', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA004', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 10.0, 800.0, 4950.00, '2026-03-24', '2026-03-29', 'MA', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA011', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 18.0, 1440.0, 8910.00, '2026-03-24', '2026-03-29', 'IL', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA011', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 30.0, 13500.0, 12150.00, '2026-03-24', '2026-03-29', 'IL', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA014', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 25.0, 2000.0, 12375.00, '2026-03-24', '2026-03-29', 'TX', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA014', '11111-0201-01', 'CARBOTREL', 'distributor', 1, 40.0, 18000.0, 16200.00, '2026-03-24', '2026-03-29', 'TX', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA014', '11111-0301-01', 'GEMTARA', 'distributor', 1, 35.0, 35000.0, 21000.00, '2026-03-24', '2026-03-29', 'TX', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA016', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 15.0, 1200.0, 7425.00, '2026-03-24', '2026-03-29', 'CA', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('SA001', '11111-0101-01', 'ZENOVAX', 'distributor', 1, 22.0, 1760.0, 10890.00, '2026-03-24', '2026-03-29', 'OH', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA022', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 35.0, 787.5, 28000.00, '2026-03-24', '2026-03-29', 'MN', 'Urology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA019', '11111-0701-01', 'LUPREX DEPOT', 'distributor', 1, 30.0, 675.0, 24000.00, '2026-03-24', '2026-03-29', 'CO', 'Urology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
-- Market data month -6
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 35.0, 2800.0, 22750.00, '2026-03-24', '2026-03-29', 'NY', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA001', '22222-0301-01', 'GEMZAR', 'market_data', 0, 42.0, 42000.0, 18900.00, '2026-03-24', '2026-03-29', 'NY', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA011', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 38.0, 3040.0, 24700.00, '2026-03-24', '2026-03-29', 'IL', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA014', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 45.0, 3600.0, 29250.00, '2026-03-24', '2026-03-29', 'TX', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA014', '22222-0301-01', 'GEMZAR', 'market_data', 0, 60.0, 60000.0, 27000.00, '2026-03-24', '2026-03-29', 'TX', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 75.0, 1687.5, 60000.00, '2026-03-24', '2026-03-29', 'MN', 'Urology', '2026-W13', '2026-03', '2026-Q1', 25, 6);


-- ============================================================
-- SUPPLEMENTARY MARKET DATA
-- The market_data source represents third-party reported total market
-- volume. This includes BOTH NovaPharma (brand_flag=1) and competitor
-- (brand_flag=0) volumes. Additional competitor volume ensures
-- realistic market share ratios (NovaPharma typically 15-35% share).
-- ============================================================

-- Additional competitor volume — current week (wk_offset=0, mo_offset=0)
-- Docetaxel market — additional generic volume across facilities
INSERT INTO sales (org_id, ndc, drug_name, data_source, brand_flag, pack_units, total_mg, wac, transaction_date, week_ending_date, state, specialty, period_wk, period_mo, period_qtr, wk_offset, mo_offset) VALUES
('FA001', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 25.0, 2000.0, 5000.00, '2026-09-15', '2026-09-20', 'NY', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA004', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 18.0, 1440.0, 11700.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA004', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 22.0, 1760.0, 4400.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA007', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 20.0, 1600.0, 13000.00, '2026-09-15', '2026-09-20', 'PA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 30.0, 2400.0, 6000.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 35.0, 2800.0, 7000.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA016', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 22.0, 1760.0, 4400.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA020', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 15.0, 1200.0, 9750.00, '2026-09-15', '2026-09-20', 'FL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA001', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 28.0, 2240.0, 5600.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA007', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 12.0, 960.0, 7800.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA007', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 18.0, 1440.0, 3600.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Additional carboplatin competitor volume
('FA004', '22222-0201-01', 'PARAPLATIN', 'market_data', 0, 12.0, 5400.0, 4800.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '22222-0201-01', 'PARAPLATIN', 'market_data', 0, 18.0, 8100.0, 7200.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '22222-0201-02', 'CARBOPLATIN GENERIC', 'market_data', 0, 25.0, 3750.0, 2500.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '22222-0201-02', 'CARBOPLATIN GENERIC', 'market_data', 0, 30.0, 4500.0, 3000.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA016', '22222-0201-01', 'PARAPLATIN', 'market_data', 0, 15.0, 6750.0, 6000.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA016', '22222-0201-02', 'CARBOPLATIN GENERIC', 'market_data', 0, 20.0, 3000.0, 2000.00, '2026-09-15', '2026-09-20', 'CA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA001', '22222-0201-01', 'PARAPLATIN', 'market_data', 0, 20.0, 9000.0, 8000.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA001', '22222-0201-02', 'CARBOPLATIN GENERIC', 'market_data', 0, 28.0, 4200.0, 2800.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Additional gemcitabine competitor volume
('FA004', '22222-0301-01', 'GEMZAR', 'market_data', 0, 15.0, 15000.0, 6750.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA004', '22222-0301-02', 'GEMCITABINE GENERIC', 'market_data', 0, 20.0, 4000.0, 1600.00, '2026-09-15', '2026-09-20', 'MA', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA011', '22222-0301-02', 'GEMCITABINE GENERIC', 'market_data', 0, 22.0, 4400.0, 1760.00, '2026-09-15', '2026-09-20', 'IL', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA014', '22222-0301-02', 'GEMCITABINE GENERIC', 'market_data', 0, 25.0, 5000.0, 2000.00, '2026-09-15', '2026-09-20', 'TX', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA001', '22222-0301-02', 'GEMCITABINE GENERIC', 'market_data', 0, 20.0, 4000.0, 1600.00, '2026-09-15', '2026-09-20', 'OH', 'Oncology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Additional leuprolide competitor volume (urology)
('FA019', '22222-0701-02', 'ELIGARD', 'market_data', 0, 15.0, 337.5, 11250.00, '2026-09-15', '2026-09-20', 'CO', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA022', '22222-0701-02', 'ELIGARD', 'market_data', 0, 18.0, 405.0, 13500.00, '2026-09-15', '2026-09-20', 'MN', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('FA022', '22222-0801-01', 'FIRMAGON', 'market_data', 0, 8.0, 1920.0, 7200.00, '2026-09-15', '2026-09-20', 'MN', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),
('SA006', '22222-0701-02', 'ELIGARD', 'market_data', 0, 12.0, 270.0, 9000.00, '2026-09-15', '2026-09-20', 'MI', 'Urology', '2026-W38', '2026-09', '2026-Q3', 0, 0),

-- Historical market data — month -1 (mo_offset=1)
('FA004', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 55.0, 4400.0, 35750.00, '2026-08-25', '2026-08-30', 'MA', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA004', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 70.0, 5600.0, 14000.00, '2026-08-25', '2026-08-30', 'MA', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA016', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 48.0, 3840.0, 31200.00, '2026-08-25', '2026-08-30', 'CA', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA016', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 60.0, 4800.0, 12000.00, '2026-08-25', '2026-08-30', 'CA', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('SA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 52.0, 4160.0, 33800.00, '2026-08-25', '2026-08-30', 'OH', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('SA001', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 65.0, 5200.0, 13000.00, '2026-08-25', '2026-08-30', 'OH', 'Oncology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA019', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 55.0, 1237.5, 44000.00, '2026-08-25', '2026-08-30', 'CO', 'Urology', '2026-W35', '2026-08', '2026-Q3', 4, 1),
('FA019', '22222-0701-02', 'ELIGARD', 'market_data', 0, 35.0, 787.5, 26250.00, '2026-08-25', '2026-08-30', 'CO', 'Urology', '2026-W35', '2026-08', '2026-Q3', 4, 1),

-- Historical market data — month -2 (mo_offset=2)
('FA004', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 50.0, 4000.0, 32500.00, '2026-07-28', '2026-08-02', 'MA', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA016', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 45.0, 3600.0, 29250.00, '2026-07-28', '2026-08-02', 'CA', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('SA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 48.0, 3840.0, 31200.00, '2026-07-28', '2026-08-02', 'OH', 'Oncology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 80.0, 1800.0, 64000.00, '2026-07-28', '2026-08-02', 'MN', 'Urology', '2026-W31', '2026-07', '2026-Q3', 8, 2),
('FA022', '22222-0701-02', 'ELIGARD', 'market_data', 0, 30.0, 675.0, 22500.00, '2026-07-28', '2026-08-02', 'MN', 'Urology', '2026-W31', '2026-07', '2026-Q3', 8, 2),

-- Historical market data — month -3 (mo_offset=3)
('FA004', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 48.0, 3840.0, 31200.00, '2026-06-23', '2026-06-28', 'MA', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA016', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 42.0, 3360.0, 27300.00, '2026-06-23', '2026-06-28', 'CA', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('SA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 45.0, 3600.0, 29250.00, '2026-06-23', '2026-06-28', 'OH', 'Oncology', '2026-W26', '2026-06', '2026-Q2', 12, 3),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 78.0, 1755.0, 62400.00, '2026-06-23', '2026-06-28', 'MN', 'Urology', '2026-W26', '2026-06', '2026-Q2', 12, 3),

-- Historical market data — month -4 (mo_offset=4)
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 35.0, 2800.0, 22750.00, '2026-05-26', '2026-05-31', 'NY', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA001', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 55.0, 4400.0, 11000.00, '2026-05-26', '2026-05-31', 'NY', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA004', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 45.0, 3600.0, 29250.00, '2026-05-26', '2026-05-31', 'MA', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA016', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 40.0, 3200.0, 26000.00, '2026-05-26', '2026-05-31', 'CA', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('SA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 42.0, 3360.0, 27300.00, '2026-05-26', '2026-05-31', 'OH', 'Oncology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 72.0, 1620.0, 57600.00, '2026-05-26', '2026-05-31', 'MN', 'Urology', '2026-W22', '2026-05', '2026-Q2', 16, 4),
('FA019', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 50.0, 1125.0, 40000.00, '2026-05-26', '2026-05-31', 'CO', 'Urology', '2026-W22', '2026-05', '2026-Q2', 16, 4),

-- Historical market data — month -5 (mo_offset=5)
('FA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 33.0, 2640.0, 21450.00, '2026-04-28', '2026-05-03', 'NY', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA001', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 50.0, 4000.0, 10000.00, '2026-04-28', '2026-05-03', 'NY', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA011', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 38.0, 3040.0, 24700.00, '2026-04-28', '2026-05-03', 'IL', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA014', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 42.0, 3360.0, 27300.00, '2026-04-28', '2026-05-03', 'TX', 'Oncology', '2026-W18', '2026-04', '2026-Q2', 20, 5),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 70.0, 1575.0, 56000.00, '2026-04-28', '2026-05-03', 'MN', 'Urology', '2026-W18', '2026-04', '2026-Q2', 20, 5),

-- Historical market data — month -6 (mo_offset=6)
('FA001', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 45.0, 3600.0, 9000.00, '2026-03-24', '2026-03-29', 'NY', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA004', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 40.0, 3200.0, 26000.00, '2026-03-24', '2026-03-29', 'MA', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA016', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 38.0, 3040.0, 24700.00, '2026-03-24', '2026-03-29', 'CA', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('SA001', '22222-0101-01', 'TAXOTERE', 'market_data', 0, 40.0, 3200.0, 26000.00, '2026-03-24', '2026-03-29', 'OH', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('SA001', '22222-0101-02', 'DOCETAXEL GENERIC', 'market_data', 0, 50.0, 4000.0, 10000.00, '2026-03-24', '2026-03-29', 'OH', 'Oncology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA022', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 68.0, 1530.0, 54400.00, '2026-03-24', '2026-03-29', 'MN', 'Urology', '2026-W13', '2026-03', '2026-Q1', 25, 6),
('FA019', '22222-0701-01', 'LUPRON DEPOT', 'market_data', 0, 45.0, 1012.5, 36000.00, '2026-03-24', '2026-03-29', 'CO', 'Urology', '2026-W13', '2026-03', '2026-Q1', 25, 6);
-- Seed users with role-based access
-- Roles: exec (global, full access), director (region-scoped), ram (territory-scoped)

INSERT INTO users (user_id, email, full_name, role, territory_name, region_name, can_view_wac) VALUES

-- Executives — global access, can see WAC pricing
('U001', 'sarah.chen@novapharma.com',       'Sarah Chen',        'exec',     NULL,                NULL,             1),
('U002', 'michael.torres@novapharma.com',    'Michael Torres',    'exec',     NULL,                NULL,             1),

-- Directors of Sales — region-scoped, no WAC access
('U003', 'jennifer.walsh@novapharma.com',    'Jennifer Walsh',    'director', NULL,                'Northeast',      0),
('U004', 'david.park@novapharma.com',        'David Park',        'director', NULL,                'Mid-Atlantic',   0),
('U005', 'lisa.johnson@novapharma.com',      'Lisa Johnson',      'director', NULL,                'Southeast',      0),
('U006', 'robert.kim@novapharma.com',        'Robert Kim',        'director', NULL,                'Midwest',        0),
('U007', 'maria.garcia@novapharma.com',      'Maria Garcia',      'director', NULL,                'South Central',  0),
('U008', 'james.anderson@novapharma.com',    'James Anderson',    'director', NULL,                'West',           0),

-- RAMs (Regional Account Managers) — territory-scoped, cannot see WAC
('U009', 'amy.nguyen@novapharma.com',        'Amy Nguyen',        'ram',      'New York Metro',    'Northeast',      0),
('U010', 'brian.murphy@novapharma.com',       'Brian Murphy',      'ram',      'New England',       'Northeast',      0),
('U011', 'carlos.rivera@novapharma.com',      'Carlos Rivera',     'ram',      'Mid-Atlantic East', 'Mid-Atlantic',   0),
('U012', 'diana.wright@novapharma.com',       'Diana Wright',      'ram',      'Mid-Atlantic West', 'Mid-Atlantic',   0),
('U013', 'eric.thompson@novapharma.com',      'Eric Thompson',     'ram',      'Southeast Atlantic','Southeast',      0),
('U014', 'fiona.davis@novapharma.com',        'Fiona Davis',       'ram',      'Southeast Gulf',    'Southeast',      0),
('U015', 'george.martinez@novapharma.com',    'George Martinez',   'ram',      'Great Lakes East',  'Midwest',        0),
('U016', 'hannah.lee@novapharma.com',         'Hannah Lee',        'ram',      'Great Lakes West',  'Midwest',        0),
('U017', 'ivan.petrov@novapharma.com',        'Ivan Petrov',       'ram',      'Upper Midwest',     'Midwest',        0),
('U018', 'julia.robinson@novapharma.com',     'Julia Robinson',    'ram',      'Texas',             'South Central',  0),
('U019', 'kevin.brown@novapharma.com',        'Kevin Brown',       'ram',      'South Central',     'South Central',  0),
('U020', 'laura.wilson@novapharma.com',       'Laura Wilson',      'ram',      'Pacific Northwest', 'West',           0),
('U021', 'nathan.clark@novapharma.com',       'Nathan Clark',      'ram',      'California North',  'West',           0),
('U022', 'olivia.taylor@novapharma.com',      'Olivia Taylor',     'ram',      'California South',  'West',           0),
('U023', 'patrick.moore@novapharma.com',      'Patrick Moore',     'ram',      'Mountain',          'West',           0);
