import unittest

from blog import post_url, reading_minutes
from textutil import slugify_title


class SlugTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify_title("Hello, World!"), "hello-world")

    def test_accents(self):
        self.assertEqual(slugify_title("Café Déjà Vu"), "cafe-deja-vu")

    def test_empty(self):
        self.assertEqual(slugify_title("!!!"), "untitled")

    def test_post_url(self):
        self.assertEqual(post_url("Hello World", 2026), "/2026/hello-world/")

    def test_reading_minutes(self):
        self.assertEqual(reading_minutes("word " * 400), 2)


if __name__ == "__main__":
    unittest.main()
