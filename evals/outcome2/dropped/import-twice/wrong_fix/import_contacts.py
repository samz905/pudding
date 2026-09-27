"""Import a CRM CSV export (crm_id,name,email,company) into the contacts database."""
import argparse
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / "data" / "contacts.db"

SCHEMA = """CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    crm_id TEXT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    imported_at TEXT NOT NULL
)"""


def connect(path):
    conn = sqlite3.connect(str(path))
    conn.execute(SCHEMA)
    return conn


def clean(row):
    return {
        "crm_id": (row.get("crm_id") or "").strip() or None,
        "name": " ".join(row["name"].split()),
        "email": row["email"].strip().lower(),
        "company": (row.get("company") or "").strip() or None,
    }


def insert_contact(conn, row, now):
    """Insert unless a contact with this email is already in the database. True if inserted."""
    c = clean(row)
    if conn.execute("SELECT 1 FROM contacts WHERE lower(trim(email)) = ? LIMIT 1", (c["email"],)).fetchone():
        return False
    conn.execute("INSERT INTO contacts (crm_id, name, email, company, imported_at) VALUES (?, ?, ?, ?, ?)",
                 (c["crm_id"], c["name"], c["email"], c["company"], now))
    return True


def import_file(csv_path, db_path=DEFAULT_DB):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = connect(db_path)
    count = 0
    with open(csv_path, newline="") as fh, conn:
        for row in csv.DictReader(fh):
            if not row.get("email", "").strip():
                continue
            count += insert_contact(conn, row, now)
    conn.close()
    return count


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    a = ap.parse_args()
    n = import_file(a.csv, a.db)
    print("imported %d contacts into %s" % (n, a.db))


if __name__ == "__main__":
    main()
