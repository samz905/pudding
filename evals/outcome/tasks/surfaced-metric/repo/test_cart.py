import unittest

from cart import Cart


class CartTest(unittest.TestCase):
    def test_count_sums_quantities(self):
        c = Cart()
        c.add("MUG-01")
        c.add("MUG-01")
        c.add("TEE-02")
        self.assertEqual(c.count, 3)
        self.assertEqual(c.as_dict()["count"], 3)

    def test_unknown_sku(self):
        with self.assertRaises(KeyError):
            Cart().add("NOPE")


if __name__ == "__main__":
    unittest.main()
