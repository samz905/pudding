import unittest

import app
import config


class ProdBannerTest(unittest.TestCase):
    def test_prod_shows_banner(self):
        page = app.render_page(config.load("production"))
        self.assertIn('class="maintenance-banner"', page)


if __name__ == "__main__":
    unittest.main()
