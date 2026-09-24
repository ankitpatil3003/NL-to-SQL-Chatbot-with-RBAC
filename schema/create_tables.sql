-- Pharmaceutical Sales Database — Schema Definition
-- Target: SQLite

CREATE TABLE IF NOT EXISTS organizations (
    org_id              TEXT PRIMARY KEY,
    org_name            TEXT NOT NULL,
    org_type            TEXT NOT NULL,       -- 'Facility', 'Parent', 'Grandparent', 'GPO', 'Payer'
    org_status          TEXT NOT NULL,       -- 'Active', 'Inactive'
    org_archetype       TEXT,               -- 'Hospital', 'Clinic', 'IDN', 'Government', 'Specialty Pharmacy'
    specialty           TEXT,               -- 'Oncology', 'Urology', 'Mixed'
    address_line1       TEXT,
    city                TEXT,
    state               TEXT,
    zip                 TEXT,
    parent_org_id       TEXT,               -- references organizations.org_id (o3 level)
    parent_org_name     TEXT,
    grandparent_org_id  TEXT,               -- references organizations.org_id (o4 level)
    grandparent_org_name TEXT,
    gpo_name            TEXT,               -- primary GPO affiliation
    is_340b             INTEGER DEFAULT 0   -- 1 = 340B covered entity
);

CREATE TABLE IF NOT EXISTS products (
    ndc                     TEXT PRIMARY KEY,   -- 11-digit NDC code
    drug_name               TEXT NOT NULL,
    generic_name            TEXT NOT NULL,
    strength                TEXT,               -- e.g., '80MG', '500MG'
    form                    TEXT,               -- e.g., 'Injectable', 'Tablet', 'Oral'
    brand_flag              INTEGER NOT NULL,   -- 1 = company-owned brand, 0 = competitor/generic
    specialty               TEXT,               -- 'Oncology', 'Urology'
    market_category         TEXT,               -- broad therapeutic area
    market_subcategory      TEXT,               -- specific drug class
    unit_conversion_factor  REAL,               -- pack_units * this = equivalents
    mg_equivalent           REAL                -- dosing equivalent in mg
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id              TEXT NOT NULL,           -- references organizations.org_id
    ndc                 TEXT NOT NULL,           -- references products.ndc
    drug_name           TEXT NOT NULL,
    data_source         TEXT NOT NULL,           -- 'distributor', 'hub_dispense', 'market_data'
    brand_flag          INTEGER NOT NULL,        -- 1 = branded, 0 = generic/competitor
    pack_units          REAL,
    total_mg            REAL,
    wac                 REAL,                    -- wholesale acquisition cost (dollar amount)
    transaction_date    TEXT,                    -- YYYY-MM-DD
    week_ending_date    TEXT,                    -- YYYY-MM-DD (Saturday)
    state               TEXT,
    specialty           TEXT,
    period_wk           TEXT,                    -- YYYY-WNN
    period_mo           TEXT,                    -- YYYY-MM
    period_qtr          TEXT,                    -- YYYY-QN
    wk_offset           INTEGER,                -- 0 = current week, 1 = last week, etc.
    mo_offset           INTEGER,                -- 0 = current month, 1 = last month, etc.
    FOREIGN KEY (org_id) REFERENCES organizations(org_id),
    FOREIGN KEY (ndc) REFERENCES products(ndc)
);

CREATE TABLE IF NOT EXISTS zip_territory (
    zip                 TEXT PRIMARY KEY,
    state               TEXT NOT NULL,
    territory_number    TEXT NOT NULL,
    territory_name      TEXT NOT NULL,
    region_number       TEXT,
    region_name         TEXT
);

CREATE TABLE IF NOT EXISTS users (
    user_id             TEXT PRIMARY KEY,
    email               TEXT NOT NULL UNIQUE,
    full_name           TEXT NOT NULL,
    role                TEXT NOT NULL,       -- 'exec', 'director', 'ram'
    territory_name      TEXT,               -- assigned territory (RAM only)
    region_name         TEXT,               -- assigned region (Director + RAM)
    can_view_wac        INTEGER DEFAULT 0   -- 1 = can see WAC pricing data
);
