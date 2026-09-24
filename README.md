
# Legacy-to-EPR Patient Data Migration & ETL Pipeline

A portfolio project simulating a real-world NHS system migration: moving
patient and appointment records from a messy legacy Patient Administration
System (PAS) into a normalised, constrained Electronic Patient Record (EPR)
schema.

Built to demonstrate the core skills required for NHS data migration /
SQL analyst roles: **advanced SQL, ETL pipeline design, data migration and
conversion, data quality validation, and stakeholder requirements
gathering.**

> All data is synthetic and randomly generated — no real patient data is used.

## Why this project

Legacy healthcare systems rarely hand over clean data. This project
deliberately recreates realistic problems — inconsistent date formats,
unformatted NHS numbers, duplicate patients, free-text status fields, and
orphaned records — and solves them the way a production migration would:
with SQL-based extraction, a validated transformation layer, referential
integrity enforcement on load, and a full audit trail of anything that
couldn't be migrated automatically.

## Architecture

```
legacy_system.db (SQLite)          epr_system.db (SQLite)
┌─────────────────────┐            ┌──────────────────────┐
│ legacy_patients      │            │ patients              │
│ legacy_appointments   │  ──ETL──▶  │ addresses             │
│ (messy, denormalised)│            │ clinicians            │
└─────────────────────┘            │ appointments          │
                                    │ migration_rejects     │
                                    └──────────────────────┘
```

**Extract** — raw rows pulled via SQL from the legacy schema
**Transform** — Python layer: name/address splitting, date parsing across
3 formats, NHS number normalisation + validation, status vocabulary mapping,
duplicate detection
**Load** — inserted into the normalised target schema with enforced foreign
keys; anything invalid is logged to `migration_rejects`, never silently
dropped

## Repository structure

```
sql/
  01_create_legacy_schema.sql          -- source system schema
  02_create_epr_schema.sql             -- normalised target schema
  03_validation_and_reporting_queries.sql   -- advanced SQL: joins, window functions, CTEs
  03b_most_recent_appointment_sqlite.sql
scripts/
  01_generate_legacy_data.py           -- synthetic messy source data
  02_etl_migration.py                  -- the ETL pipeline itself
docs/
  requirements_gathering.md            -- stakeholder requirements & sign-off criteria
reports/
  migration_stats.json                 -- load/reject counts from the last run
  query_results.json                   -- output of the validation queries
```

## Results from the last migration run

| Metric | Value |
|---|---|
| Legacy patient records | 408 |
| Successfully migrated | 382 |
| Rejected — invalid NHS number | 18 |
| Rejected — duplicate NHS number | 8 |
| Legacy appointment records | 904 |
| Successfully migrated | 844 |
| Rejected — orphaned patient reference | 60 |
| Post-migration validation | 0 invalid NHS numbers, 0 orphaned appointments in live system |

## How to run it

```bash
pip install pandas
python3 scripts/01_generate_legacy_data.py   # builds the messy legacy DB
python3 scripts/02_etl_migration.py          # runs the migration
sqlite3 data/epr_system.db < sql/03_validation_and_reporting_queries.sql
```

## Skills demonstrated

- Advanced SQL (joins, CTEs, window functions, CHECK constraints, aggregation)
- ETL pipeline design (extract/transform/load separation, idempotent loads)
- Data migration & conversion (schema mapping, format normalisation)
- Data quality validation (rejection logging, referential integrity checks)
- Stakeholder requirements gathering & sign-off documentation


