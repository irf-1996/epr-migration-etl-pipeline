"""
Generates a synthetic 'legacy system' SQLite database with realistic
messiness: mixed date formats, inconsistent NHS number formatting,
free-text status fields, and a handful of deliberately broken rows —
so the ETL pipeline has real problems to solve, just like a real
data migration project.

All data is fictional / randomly generated. No real patient data.
"""
import sqlite3
import random
from datetime import datetime, timedelta

random.seed(42)

DB_PATH = "/home/claude/epr-migration-project/data/legacy_system.db"

FIRST_NAMES = ["John", "Mary", "Ahmed", "Priya", "David", "Fatima", "James",
               "Linda", "Mohammed", "Sarah", "Chen", "Aisha", "Robert", "Olga"]
LAST_NAMES = ["Smith", "Patel", "Khan", "Jones", "Singh", "Brown", "Ali",
              "Taylor", "Chowdhury", "Wilson", "Nkomo", "O'Brien"]
CLINICIANS = ["Dr. Emily Carter", "Dr. Rajesh Menon", "Dr. Sophie Hall",
              "Dr. Michael Osei", "Nurse Practitioner Kate Liu"]
STATUSES_MESSY = ["Attended", "attended", "ATTENDED", "DNA", "Did Not Attend",
                   "CANCELLED", "cancelled ", "Cancelled", "Booked", "booked"]
APPT_TYPES = ["Follow-up", "Initial Assessment", "Physiotherapy", "Blood Test",
              "Consultant Review", "Telephone Triage"]

def random_dob_text():
    d = datetime(1940, 1, 1) + timedelta(days=random.randint(0, 30000))
    fmt = random.choice(["%d/%m/%Y", "%Y-%m-%d", "%d-%b-%y"])
    return d.strftime(fmt)

def random_nhs_number(broken=False):
    digits = "".join(str(random.randint(0, 9)) for _ in range(10))
    if broken:
        return random.choice(["", "123", "ABCDEFGHIJ", None])
    style = random.choice(["plain", "spaced", "dashed"])
    if style == "spaced":
        return f"{digits[0:3]} {digits[3:6]} {digits[6:10]}"
    if style == "dashed":
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
    return digits

def random_address():
    num = random.randint(1, 200)
    streets = ["High Street", "Church Lane", "Station Road", "Park Avenue", "Mill Lane"]
    cities = ["Coventry", "Warwick", "Nuneaton", "Rugby", "Leamington Spa"]
    postcode = f"CV{random.randint(1,9)} {random.randint(1,9)}{random.choice('ABCDEFGH')}{random.choice('ABCDEFGH')}"
    return f"{num} {random.choice(streets)}, {random.choice(cities)}, {postcode}"

def random_appt_datetime_text():
    d = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 600), hours=random.randint(8, 17))
    fmt = random.choice(["%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y %I:%M%p"])
    return d.strftime(fmt)

def main():
    conn = sqlite3.connect(DB_PATH)
    with open("/home/claude/epr-migration-project/sql/01_create_legacy_schema.sql") as f:
        conn.executescript(f.read())

    patients = []
    n_patients = 400
    for i in range(1, n_patients + 1):
        pid = f"P-{i:05d}"
        full_name = f"{random.choice(LAST_NAMES)}, {random.choice(FIRST_NAMES)}"
        broken = random.random() < 0.05  # 5% deliberately broken NHS numbers
        nhs = random_nhs_number(broken=broken)
        dob = random_dob_text()
        phone = f"07{random.randint(100000000, 999999999)}" if random.random() > 0.1 else None
        patients.append((pid, full_name, dob, nhs, random_address(), phone, f"GP{random.randint(100,199)}"))

    # Inject a handful of duplicate patients (same person registered twice — common in legacy PAS systems)
    for _ in range(8):
        dup = random.choice(patients)
        new_id = f"P-{n_patients + random.randint(1000,9999):05d}"
        patients.append((new_id,) + dup[1:])

    conn.executemany(
        "INSERT INTO legacy_patients VALUES (?,?,?,?,?,?,?)", patients
    )

    appts = []
    for i in range(1, 900):
        pid = random.choice(patients)[0]
        appt_id = f"A-{i:05d}"
        appts.append((
            appt_id, pid, random_appt_datetime_text(),
            random.choice(APPT_TYPES), random.choice(CLINICIANS),
            random.choice(STATUSES_MESSY)
        ))
    # A few appointments reference a patient_id that doesn't exist (orphaned records)
    for i in range(5):
        appts.append((f"A-ORPHAN-{i}", "P-99999", random_appt_datetime_text(),
                       random.choice(APPT_TYPES), random.choice(CLINICIANS),
                       random.choice(STATUSES_MESSY)))

    conn.executemany(
        "INSERT INTO legacy_appointments VALUES (?,?,?,?,?,?)", appts
    )
    conn.commit()

    print(f"Legacy DB created: {len(patients)} patients, {len(appts)} appointments")
    print(f"  - Duplicates injected: 8")
    print(f"  - Broken NHS numbers: ~5%")
    print(f"  - Orphaned appointment records: 5")
    conn.close()

if __name__ == "__main__":
    main()
