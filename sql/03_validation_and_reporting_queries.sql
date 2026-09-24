-- ============================================================
-- POST-MIGRATION VALIDATION & REPORTING QUERIES
-- Run against epr_system.db after the ETL load.
-- Demonstrates advanced SQL: joins, window functions, CTEs,
-- aggregate reporting, data-quality checks.
-- ============================================================

-- 1. Migration completeness: rows loaded vs rejected, by reason
SELECT reason, COUNT(*) AS reject_count
FROM migration_rejects
GROUP BY reason
ORDER BY reject_count DESC;

-- 2. Data quality check: any patient loaded without a valid NHS number
--    (should return 0 rows if the ETL validation worked correctly)
SELECT patient_id, legacy_id
FROM patients
WHERE nhs_number IS NULL
   OR LENGTH(nhs_number) != 10;

-- 3. Referential integrity check: every appointment must reference
--    a patient that exists (enforced by FK, but worth confirming)
SELECT a.appointment_id, a.legacy_appt_id
FROM appointments a
LEFT JOIN patients p ON a.patient_id = p.patient_id
WHERE p.patient_id IS NULL;

-- 4. Appointment activity by clinician (stakeholder reporting: caseload)
SELECT c.full_name,
       COUNT(*) AS total_appointments,
       SUM(CASE WHEN a.status = 'Attended' THEN 1 ELSE 0 END) AS attended,
       SUM(CASE WHEN a.status = 'Did Not Attend' THEN 1 ELSE 0 END) AS dna_count,
       ROUND(100.0 * SUM(CASE WHEN a.status = 'Did Not Attend' THEN 1 ELSE 0 END) / COUNT(*), 1) AS dna_rate_pct
FROM appointments a
JOIN clinicians c ON a.clinician_id = c.clinician_id
GROUP BY c.full_name
ORDER BY dna_rate_pct DESC;

-- 5. Window function: each patient's appointments ranked by date,
--    to identify their most recent appointment
SELECT patient_id, appointment_id, appointment_datetime, status,
       ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY appointment_datetime DESC) AS recency_rank
FROM appointments
QUALIFY recency_rank = 1;
-- Note: SQLite doesn't support QUALIFY natively; see 03b for the
-- CTE-based equivalent used in the actual pipeline (SQLite-compatible).

-- 6. Monthly appointment volume trend (useful for capacity planning stakeholder reports)
SELECT strftime('%Y-%m', appointment_datetime) AS month,
       appointment_type,
       COUNT(*) AS appointment_count
FROM appointments
GROUP BY month, appointment_type
ORDER BY month, appointment_count DESC;
