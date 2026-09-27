import tempfile
import unittest
from pathlib import Path

import profiles


class ProfileTest(unittest.TestCase):
    def setUp(self):
        profiles.PROFILE = Path(tempfile.mkdtemp()) / "profile.json"

    def test_defaults(self):
        self.assertEqual(profiles.get()["display_name"], "Sam")

    def test_update_returns_new_values(self):
        self.assertEqual(profiles.update({"display_name": "  Sammy "})["display_name"], "Sammy")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            profiles.update({"display_name": " "})

    def test_update_persists(self):
        profiles.update({"display_name": "Robin"})
        self.assertEqual(profiles.get()["display_name"], "Robin")


if __name__ == "__main__":
    unittest.main()
