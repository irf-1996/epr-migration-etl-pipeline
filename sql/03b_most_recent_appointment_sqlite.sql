-- SQLite-compatible equivalent of query #5 in 03_validation_and_reporting_queries.sql
-- (SQLite doesn't support QUALIFY, so the window function result is
-- filtered via a CTE instead)

WITH ranked AS (
    SELECT patient_id, appointment_id, appointment_datetime, status,
           ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY appointment_datetime DESC) AS recency_rank
    FROM appointments
)
SELECT patient_id, appointment_id, appointment_datetime, status
FROM ranked
WHERE recency_rank = 1;
