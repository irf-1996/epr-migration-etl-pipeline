-- ============================================================
-- LEGACY SYSTEM SCHEMA
-- Simulates an old Patient Administration System (PAS)
-- Deliberately messy/denormalised, as real legacy NHS systems
-- often are: single free-text fields, inconsistent formats,
-- no referential integrity enforcement.
-- ============================================================

DROP TABLE IF EXISTS legacy_patients;
DROP TABLE IF EXISTS legacy_appointments;

CREATE TABLE legacy_patients (
    patient_id      TEXT PRIMARY KEY,   -- e.g. 'P-00001' (legacy format)
    full_name       TEXT,               -- single field, "Surname, Firstname"
    dob_text        TEXT,               -- inconsistent formats: 'DD/MM/YYYY', 'YYYY-MM-DD', 'DD-Mon-YY'
    nhs_number_raw  TEXT,               -- inconsistent formatting: spaces, dashes, missing digits
    address_blob    TEXT,               -- single free-text field, comma separated
    phone           TEXT,
    gp_code         TEXT
);

CREATE TABLE legacy_appointments (
    appt_id         TEXT PRIMARY KEY,
    patient_id      TEXT,               -- no FK constraint in legacy system
    appt_datetime_text TEXT,            -- inconsistent formats
    appt_type       TEXT,
    clinician_name  TEXT,
    status_text     TEXT                -- free text: 'Attended','attended','DNA','Did Not Attend','CANCELLED','cancelled '
);
