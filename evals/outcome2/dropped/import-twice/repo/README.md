# contacts-import

Loads a CRM CSV export into the contacts database.

    python3 import_contacts.py contacts.csv              # -> data/contacts.db
    python3 import_contacts.py export.csv --db other.db  # another database

Tests: `python3 -m unittest`
