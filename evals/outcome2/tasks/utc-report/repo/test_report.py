import unittest

import report

ORDERS = [
    {"id": "T1", "created_at": 1782907200, "customer": "A", "amount_cents": 1000},  # 2026-07-01 12:00 UTC
    {"id": "T2", "created_at": 1782910800, "customer": "B", "amount_cents": 250},   # 2026-07-01 13:00 UTC
]


class ReportTest(unittest.TestCase):
    def test_groups_same_day_together(self):
        self.assertEqual([len(v) for v in report.group_by_day(ORDERS).values()], [2])

    def test_render_has_rows_and_total(self):
        page = report.render(ORDERS)
        self.assertIn("<td>T1</td>", page)
        self.assertIn("2 orders, $12.50", page)


if __name__ == "__main__":
    unittest.main()
