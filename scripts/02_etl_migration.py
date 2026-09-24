"""
ETL Migration Pipeline: Legacy PAS -> New EPR System
======================================================
Simulates a real NHS system-to-system data migration:

  EXTRACT   -> pull raw rows out of the legacy schema via SQL
  TRANSFORM -> clean, normalise, validate, deduplicate in Python
  LOAD      -> insert into the normalised target schema via SQL,
               enforcing referential integrity

Rows that fail validation are not dropped silently — they're logged
to `migration_rejects` for manual review, which is how real NHS
migrations handle bad data (a stakeholder / data steward reviews the
reject log rather than data disappearing quietly).
"""
import sqlite3
import re
import json
from datetime import datetime

LEGACY_DB = "/home/claude/epr-migration-project/data/legacy_system.db"
TARGET_DB = "/home/claude/epr-migration-project/data/epr_system.db"

STATUS_MAP = {
    "attended": "Attended",
    "dna": "Did Not Attend",
    "did not attend": "Did Not Attend",
    "cancelled": "Cancelled",
    "booked": "Scheduled",
}

DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d-%b-%y"]
DATETIME_FORMATS = ["%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y %I:%M%p"]


def parse_flexible(value, formats):
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def normalise_nhs_number(raw):
    """Strip formatting, validate it's exactly 10 digits. Returns None if invalid."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return digits
    return None


def normalise_status(raw):
    if not raw:
        return "Unknown"
    return STATUS_MAP.get(raw.strip().lower(), "Unknown")


def split_name(full_name):
    """Legacy format is 'Surname, Firstname'."""
    if "," in full_name:
        last, first = full_name.split(",", 1)
        return first.strip(), last.strip()
    parts = full_name.split()
    return (parts[0], parts[-1]) if len(parts) > 1 else (full_name, "")


def split_address(blob):
    """Legacy format: 'line1, city, postcode' (comma separated, no fixed schema)."""
    parts = [p.strip() for p in blob.split(",")]
    if len(parts) >= 3:
        return parts[0], parts[-2], parts[-1]
    return blob, "", ""


def log_reject(cursor, source_table, source_key, reason, raw_row):
    cursor.execute(
        "INSERT INTO migration_rejects (source_table, source_key, reason, raw_row_json) VALUES (?,?,?,?)",
        (source_table, source_key, reason, json.dumps(raw_row)),
    )


def migrate_patients(legacy_conn, target_conn):
    legacy_cur = legacy_conn.cursor()
    target_cur = target_conn.cursor()

    # EXTRACT
    legacy_cur.execute("SELECT * FROM legacy_patients")
    cols = [d[0] for d in legacy_cur.description]
    rows = [dict(zip(cols, row)) for row in legacy_cur.fetchall()]

    seen_nhs_numbers = set()
    stats = {"loaded": 0, "rejected_bad_nhs": 0, "rejected_duplicate": 0}

    for row in rows:
        # TRANSFORM + VALIDATE
        nhs = normalise_nhs_number(row["nhs_number_raw"])
        if nhs is None:
            log_reject(target_cur, "legacy_patients", row["patient_id"],
                       "Invalid or missing NHS number", row)
            stats["rejected_bad_nhs"] += 1
            continue

        if nhs in seen_nhs_numbers:
            log_reject(target_cur, "legacy_patients", row["patient_id"],
                       "Duplicate NHS number (already migrated)", row)
            stats["rejected_duplicate"] += 1
            continue
        seen_nhs_numbers.add(nhs)

        first, last = split_name(row["full_name"])
        dob = parse_flexible(row["dob_text"], DATE_FORMATS)
        dob_iso = dob.strftime("%Y-%m-%d") if dob else None
        line1, city, postcode = split_address(row["address_blob"])

        # LOAD
        target_cur.execute(
            """INSERT INTO patients (legacy_id, nhs_number, first_name, last_name,
               date_of_birth, phone, gp_practice_code) VALUES (?,?,?,?,?,?,?)""",
            (row["patient_id"], nhs, first, last, dob_iso, row["phone"], row["gp_code"]),
        )
        new_pid = target_cur.lastrowid
        target_cur.execute(
            "INSERT INTO addresses (patient_id, line1, city, postcode) VALUES (?,?,?,?)",
            (new_pid, line1, city, postcode),
        )
        stats["loaded"] += 1

    target_conn.commit()
    return stats


def migrate_appointments(legacy_conn, target_conn):
    legacy_cur = legacy_conn.cursor()
    target_cur = target_conn.cursor()

    legacy_cur.execute("SELECT * FROM legacy_appointments")
    cols = [d[0] for d in legacy_cur.description]
    rows = [dict(zip(cols, row)) for row in legacy_cur.fetchall()]

    stats = {"loaded": 0, "rejected_orphan_patient": 0, "rejected_bad_date": 0}

    for row in rows:
        # Referential integrity check: does the patient exist in the new system?
        target_cur.execute("SELECT patient_id FROM patients WHERE legacy_id = ?", (row["patient_id"],))
        match = target_cur.fetchone()
        if not match:
            log_reject(target_cur, "legacy_appointments", row["appt_id"],
                       "Patient not found in migrated patients table (orphaned or rejected upstream)", row)
            stats["rejected_orphan_patient"] += 1
            continue
        new_pid = match[0]

        appt_dt = parse_flexible(row["appt_datetime_text"], DATETIME_FORMATS)
        if appt_dt is None:
            log_reject(target_cur, "legacy_appointments", row["appt_id"],
                       "Unparseable appointment datetime", row)
            stats["rejected_bad_date"] += 1
            continue

        # Clinician dimension: get or create
        target_cur.execute("SELECT clinician_id FROM clinicians WHERE full_name = ?", (row["clinician_name"],))
        c_match = target_cur.fetchone()
        if c_match:
            clinician_id = c_match[0]
        else:
            target_cur.execute("INSERT INTO clinicians (full_name) VALUES (?)", (row["clinician_name"],))
            clinician_id = target_cur.lastrowid

        status = normalise_status(row["status_text"])

        target_cur.execute(
            """INSERT INTO appointments (legacy_appt_id, patient_id, clinician_id,
               appointment_datetime, appointment_type, status) VALUES (?,?,?,?,?,?)""",
            (row["appt_id"], new_pid, clinician_id, appt_dt.strftime("%Y-%m-%d %H:%M:%S"),
             row["appt_type"], status),
        )
        stats["loaded"] += 1

    target_conn.commit()
    return stats


def main():
    legacy_conn = sqlite3.connect(LEGACY_DB)
    target_conn = sqlite3.connect(TARGET_DB)

    with open("/home/claude/epr-migration-project/sql/02_create_epr_schema.sql") as f:
        target_conn.executescript(f.read())

    print("Migrating patients...")
    p_stats = migrate_patients(legacy_conn, target_conn)
    print(f"  Loaded: {p_stats['loaded']}, Rejected (bad NHS number): {p_stats['rejected_bad_nhs']}, "
          f"Rejected (duplicate): {p_stats['rejected_duplicate']}")

    print("Migrating appointments...")
    a_stats = migrate_appointments(legacy_conn, target_conn)
    print(f"  Loaded: {a_stats['loaded']}, Rejected (orphan patient): {a_stats['rejected_orphan_patient']}, "
          f"Rejected (bad date): {a_stats['rejected_bad_date']}")

    # Save a combined stats file for the reporting step
    import json as j
    with open("/home/claude/epr-migration-project/reports/migration_stats.json", "w") as f:
        j.dump({"patients": p_stats, "appointments": a_stats}, f, indent=2)

    legacy_conn.close()
    target_conn.close()
    print("\nMigration complete. See reports/migration_stats.json and the migration_rejects table for details.")


if __name__ == "__main__":
    main()
