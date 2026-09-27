import json
import tempfile
import unittest
from pathlib import Path

import server


class PrefsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        server.PREFS_FILE = self.tmp / "prefs.json"

    def test_defaults(self):
        self.assertEqual(server.load_prefs()["density"], "comfortable")

    def test_save_merges(self):
        server.save_prefs({"density": "compact", "bogus": 1})
        self.assertEqual(json.loads(server.PREFS_FILE.read_text()), {**server.DEFAULT_PREFS, "density": "compact"})

    def test_index_embeds_prefs(self):
        self.assertIn('"currency": "USD"', server.render_index())


if __name__ == "__main__":
    unittest.main()
