# Data Migration Requirements — Legacy PAS → New EPR

*(Simulated stakeholder requirements document, written the way a real pre-migration discovery phase would be documented.)*

## 1. Stakeholders identified
| Stakeholder | Interest |
|---|---|
| Clinical Records Manager | Data integrity, no patient data loss |
| Data Protection Officer | GDPR compliance, no unnecessary retention of unvalidated data |
| Clinicians / end users | Appointment history must be intact and searchable post-migration |
| IT Migration Lead | Rollback plan, error visibility, sign-off criteria |

## 2. Requirements gathered
1. **No silent data loss** — every legacy record must either land in the new
   system or be logged with a clear rejection reason for manual review.
   → Implemented as the `migration_rejects` table.
2. **NHS number is the golden key** — must be validated to the standard
   10-digit format before being treated as a unique patient identifier.
   → Implemented in `normalise_nhs_number()`.
3. **Duplicate patient records must be flagged, not merged automatically**
   — clinical staff want visibility of duplicates rather than silent
   deduplication, since two people can legitimately share details.
   → Duplicates are rejected and logged, not merged, pending manual review.
4. **Appointment status vocabulary must be standardised** — legacy system
   allowed free text ("attended", "ATTENDED", "Did Not Attend"); new system
   requires a fixed set of values for reliable reporting.
   → Implemented via `STATUS_MAP` and a `CHECK` constraint in the schema.
5. **Traceability back to source system** — every migrated row must retain
   a link to its legacy ID, in case of dispute or audit.
   → Implemented via `legacy_id` / `legacy_appt_id` columns.

## 3. Sign-off criteria (agreed with stakeholders)
- Zero patients loaded with an invalid NHS number (validated in query #2).
- Zero orphaned appointments in the live system (validated in query #3).
- Reject log reviewed and signed off by the Clinical Records Manager before
  the legacy system is decommissioned.

## 4. Out of scope for this phase
- Historical appointments older than 3 years (agreed as archive-only,
  migrated separately in a later phase).
- Free-text clinical notes (require a separate unstructured-data migration
  approach, not covered by this structured ETL).
