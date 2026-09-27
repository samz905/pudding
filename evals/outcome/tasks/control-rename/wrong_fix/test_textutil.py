import unittest

from blog import post_url, reading_minutes
from textutil import make_slug


class SlugTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(make_slug("Hello, World!"), "hello-world")

    def test_accents(self):
        self.assertEqual(make_slug("Café Déjà Vu"), "cafe-deja-vu")

    def test_empty(self):
        self.assertEqual(make_slug("!!!"), "untitled")

    def test_post_url(self):
        self.assertEqual(post_url("Hello World", 2026), "/2026/hello-world/")

    def test_reading_minutes(self):
        self.assertEqual(reading_minutes("word " * 400), 2)


if __name__ == "__main__":
    unittest.main()
