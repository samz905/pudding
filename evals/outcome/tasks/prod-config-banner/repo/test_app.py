import unittest

import app
import config


class RenderTest(unittest.TestCase):
    def test_dev_shows_banner(self):
        page = app.render_page(config.load("development"))
        self.assertIn('class="maintenance-banner"', page)
        self.assertIn("Scheduled maintenance", page)

    def test_site_name(self):
        self.assertIn("<h1>Parcel Tracker</h1>", app.render_page(config.load("development")))


if __name__ == "__main__":
    unittest.main()
