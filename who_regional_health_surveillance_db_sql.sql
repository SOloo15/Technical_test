-- ==========================================
-- CREATE DATABASE
-- ==========================================

CREATE DATABASE who_regional_health_surveillance_db;

-- ==========================================
-- ENABLE PostGIS EXTENSION
-- ==========================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- ==========================================
-- CREATE TABLES
-- ==========================================

-- 1. Countries Reference Table
CREATE TABLE countries (
    iso3 CHAR(3) PRIMARY KEY,
    country_name VARCHAR(100) NOT NULL,
    afro_subregion VARCHAR(50),
    latitude NUMERIC(10, 6) CHECK (latitude >= -90 AND latitude <= 90),
    longitude NUMERIC(10, 6) CHECK (longitude >= -180 AND longitude <= 180),
    priority_country INTEGER DEFAULT 0,
    -- geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 2. Population Table
CREATE TABLE population (
    iso3 CHAR(3) REFERENCES countries(iso3),
    year INTEGER CHECK (year BETWEEN 2021 AND 2025),
    total_population BIGINT,
    under5_population BIGINT,
    urban_population_pct NUMERIC(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (iso3, year)
);

-- 3. Disease Surveillance Table
CREATE TABLE disease_surveillance (
    iso3 CHAR(3) REFERENCES countries(iso3),
    year INTEGER,
    disease VARCHAR(100),
    cases_reported INTEGER DEFAULT 0,
    deaths_reported INTEGER DEFAULT 0,
    attack_rate_per_100k NUMERIC(10, 2),
    case_fatality_ratio_pct NUMERIC(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (iso3, year, disease)
);

-- 4. Outbreaks Table
CREATE TABLE outbreaks (
    outbreak_id VARCHAR(20) PRIMARY KEY,
    iso3 CHAR(3) REFERENCES countries(iso3),
    year INTEGER,
    disease VARCHAR(100),
    start_date DATE,
    duration_days INTEGER,
    time_to_detection_days INTEGER,
    cases INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Laboratory Capacity Table
CREATE TABLE laboratory_capacity (
    iso3 CHAR(3) REFERENCES countries(iso3),
    year INTEGER,
    total_public_labs INTEGER,
    labs_iso15189_accredited INTEGER,
    iso15189_accreditation_pct NUMERIC(5, 2),
    avg_turnaround_time_days NUMERIC(5, 2),
    diagnostic_tests_per_100k NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (iso3, year)
);

-- 6. Reporting Metrics Table
CREATE TABLE reporting_metrics (
    iso3 CHAR(3) REFERENCES countries(iso3),
    year INTEGER CHECK (year BETWEEN 2021 AND 2025),
    timeliness_pct NUMERIC(5, 2),
    completeness_pct NUMERIC(5, 2),
    idsr_weekly_compliance_pct NUMERIC(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (iso3, year)
);

-- 7. Workforce Table
CREATE TABLE workforce (
    iso3 CHAR(3) REFERENCES countries(iso3),
    year INTEGER,
    epidemiologists_total INTEGER,
    epidemiologists_per_100k NUMERIC(10, 3),
    feltp_trained_total INTEGER,
    feltp_trained_pct NUMERIC(5, 2),
    lab_technicians_total INTEGER,
    lab_technicians_per_100k NUMERIC(10, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (iso3, year)
);

-- 8. Funding Table
CREATE TABLE funding (
    iso3 CHAR(3) REFERENCES countries(iso3),
    year INTEGER,
    total_funding_usd DECIMAL(15, 2),
    domestic_funding_usd DECIMAL(15, 2),
    external_funding_usd DECIMAL(15, 2),
    funding_per_capita_usd DECIMAL(10, 2),
    domestic_funding_share_pct DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (iso3, year)
);

-- ==========================================
-- CREATE INDEXES
-- ==========================================

CREATE INDEX idx_outbreaks_iso3_year ON outbreaks (iso3, year);
CREATE INDEX idx_outbreaks_disease ON outbreaks (disease);
CREATE INDEX idx_outbreaks_start_date ON outbreaks (start_date);
CREATE INDEX idx_surveillance_disease ON disease_surveillance (disease);
CREATE INDEX idx_population_iso3_year ON population (iso3, year);
CREATE INDEX idx_lab_iso3_year ON laboratory_capacity (iso3, year);
CREATE INDEX idx_reporting_iso3_year ON reporting_metrics (iso3, year);
CREATE INDEX idx_workforce_iso3_year ON workforce (iso3, year);
CREATE INDEX idx_funding_iso3_year ON funding (iso3, year);
