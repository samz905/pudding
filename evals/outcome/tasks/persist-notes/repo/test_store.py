import json
import os
import tempfile
import unittest

import store


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "notes.json")

    def test_load_missing_file_is_empty(self):
        self.assertEqual(store.load_notes(self.path), [])

    def test_load_reads_saved_notes(self):
        with open(self.path, "w") as f:
            json.dump({"notes": [{"id": 1, "text": "hi"}]}, f)
        self.assertEqual(store.load_notes(self.path), [{"id": 1, "text": "hi"}])

    def test_append_writes_file(self):
        store.append_note({"id": 1, "text": "hi"}, self.path)
        self.assertTrue(os.path.exists(self.path))


if __name__ == "__main__":
    unittest.main()
