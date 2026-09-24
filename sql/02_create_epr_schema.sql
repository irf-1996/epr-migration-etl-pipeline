-- ============================================================
-- TARGET SCHEMA: New EPR (Electronic Patient Record) System
-- Normalised, constrained, referential integrity enforced.
-- This is what the migration loads clean data INTO.
-- ============================================================

DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS clinicians;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS migration_rejects;

CREATE TABLE patients (
    patient_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_id       TEXT UNIQUE NOT NULL,     -- traceability back to source system
    nhs_number      CHAR(10) UNIQUE,          -- normalised, validated 10-digit NHS number
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    date_of_birth   DATE,
    phone           TEXT,
    gp_practice_code TEXT
);

CREATE TABLE addresses (
    address_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(patient_id),
    line1           TEXT,
    city            TEXT,
    postcode        TEXT
);

CREATE TABLE clinicians (
    clinician_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT UNIQUE NOT NULL
);

CREATE TABLE appointments (
    appointment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_appt_id      TEXT UNIQUE,
    patient_id          INTEGER NOT NULL REFERENCES patients(patient_id),
    clinician_id        INTEGER REFERENCES clinicians(clinician_id),
    appointment_datetime DATETIME,
    appointment_type    TEXT,
    status              TEXT CHECK (status IN ('Attended','Did Not Attend','Cancelled','Scheduled','Unknown'))
);

-- Every migration needs a quarantine table: rows that fail validation
-- are logged here for manual data-steward / stakeholder review rather
-- than silently dropped or silently loaded with bad data.
CREATE TABLE migration_rejects (
    reject_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    source_table    TEXT,
    source_key      TEXT,
    reason          TEXT,
    raw_row_json    TEXT,
    logged_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
