import unittest

from money import parse_amount


class ParseTest(unittest.TestCase):
    def test_whole_and_cents(self):
        self.assertEqual(parse_amount("12.34"), 1234)

    def test_thousands(self):
        self.assertEqual(parse_amount("1,234.56"), 123456)

    def test_dollar_sign(self):
        self.assertEqual(parse_amount("$5"), 500)

    def test_one_decimal(self):
        self.assertEqual(parse_amount("0.5"), 50)


if __name__ == "__main__":
    unittest.main()
