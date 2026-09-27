import unittest

import discounts


class DiscountTest(unittest.TestCase):
    def test_known_code(self):
        self.assertEqual(discounts.apply("SAVE10", 8000)["total"], 7200)

    def test_unknown_code(self):
        self.assertIsNone(discounts.apply("NOPE", 8000))

    def test_whitespace(self):
        self.assertEqual(discounts.lookup(" WELCOME5 "), 5)


if __name__ == "__main__":
    unittest.main()
