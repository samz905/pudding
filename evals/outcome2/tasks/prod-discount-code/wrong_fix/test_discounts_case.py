import unittest

import discounts


class CaseTest(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(discounts.apply("save10", 8000)["total"], 7200)

    def test_mixed_case(self):
        self.assertEqual(discounts.apply("Save10", 8000)["total"], 7200)


if __name__ == "__main__":
    unittest.main()
