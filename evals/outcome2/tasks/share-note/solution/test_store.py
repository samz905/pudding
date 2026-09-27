import tempfile
import unittest
from pathlib import Path

import store


class StoreTest(unittest.TestCase):
    def setUp(self):
        store.DATA = Path(tempfile.mkdtemp()) / "data.json"

    def test_create_and_list(self):
        store.create("bob", "groceries")
        self.assertEqual([n["title"] for n in store.notes_for("bob")], ["groceries"])
        self.assertEqual(store.notes_for("alice"), [])

    def test_share_records_recipient(self):
        n = store.create("bob", "trip plan")
        store.share(n["id"], "alice")
        self.assertEqual(store.get(n["id"])["shared_with"], ["alice"])

    def test_shared_note_in_recipient_list(self):
        n = store.create("bob", "trip plan")
        store.share(n["id"], "alice")
        self.assertEqual([x["title"] for x in store.notes_for("alice")], ["trip plan"])


if __name__ == "__main__":
    unittest.main()
