"""Daily orders report: python3 report.py orders.json  -> report.html"""
import html
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def order_time(order):
    return datetime.fromtimestamp(order["created_at"], tz=timezone.utc)


def group_by_day(orders):
    days = OrderedDict()
    for o in sorted(orders, key=lambda o: o["created_at"]):
        days.setdefault(order_time(o).strftime("%Y-%m-%d"), []).append(o)
    return days


def money(cents):
    return "$%d.%02d" % divmod(cents, 100)


def render(orders):
    sections = []
    for day, rows in group_by_day(orders).items():
        trs = "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td class=\"amt\">%s</td></tr>" % (
                html.escape(o["id"]), order_time(o).strftime("%H:%M"), html.escape(o["customer"]),
                money(o["amount_cents"]))
            for o in rows)
        total = money(sum(o["amount_cents"] for o in rows))
        sections.append(
            '<section class="day" data-day="%s"><h2 class="day-title">%s</h2>'
            "<table><thead><tr><th>Order</th><th>Time (UTC)</th><th>Customer</th><th class=\"amt\">Amount</th></tr></thead>"
            "<tbody>%s</tbody></table><p class=\"day-total\">%d orders, %s</p></section>" % (day, day, trs, len(rows), total))
    tpl = (ROOT / "templates" / "report.html").read_text()
    return tpl.replace("{{ sections }}", "\n".join(sections))


def main():
    orders = json.loads(Path(sys.argv[1]).read_text())
    out = ROOT / "report.html"
    out.write_text(render(orders))
    print("wrote %s (%d orders)" % (out, len(orders)))


if __name__ == "__main__":
    main()
