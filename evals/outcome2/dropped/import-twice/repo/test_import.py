import sqlite3
import tempfile
import unittest
from pathlib import Path

import import_contacts

CSV = "crm_id,name,email,company\nC-1,A One,a@x.com,X\nC-2,B Two, B@X.com ,\n,,,\n"


class ImportTest(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.csv, self.db = d / "in.csv", d / "t.db"
        self.csv.write_text(CSV)

    def rows(self):
        return sqlite3.connect(str(self.db)).execute("SELECT crm_id, name, email, company FROM contacts ORDER BY id").fetchall()

    def test_imports_and_cleans(self):
        self.assertEqual(import_contacts.import_file(self.csv, self.db), 2)
        self.assertEqual(self.rows(), [("C-1", "A One", "a@x.com", "X"), ("C-2", "B Two", "b@x.com", None)])


if __name__ == "__main__":
    unittest.main()
