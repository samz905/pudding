"""Hidden checker: for each place the prompt names, generate the report the way a person
there does (TZ set for report.py) and open report.html in a browser set to that timezone.
Every order must sit under a heading showing its UTC date, and its row must show its UTC time."""
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402

ZONES = {"san_francisco": "America/Los_Angeles", "new_york": "America/New_York", "london": "Europe/London"}
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

# For each order id, the text of the closest heading above it and the text of its row.
LAYOUT = """ids => { const out = {}; let heading = null;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  for (let n = walker.currentNode; n; n = walker.nextNode()) {
    if (/^H[1-6]$/.test(n.tagName) && n.innerText.trim()) heading = n.innerText.trim();
    if (n.tagName === 'TR' || n.tagName === 'LI') {
      for (const id of ids) if (n.innerText.includes(id) && !(id in out)) out[id] = [heading, n.innerText];
    }
  }
  return out; }"""


def parse_day(text):
    """A date written as 2026-07-01, 7/1/2026, 'Jul 1, 2026', 'July 1 2026' or '1 July 2026'."""
    if not text:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text)
    if m:
        return date(int(m[3]), int(m[1]), int(m[2]))
    m = re.search(r"\b([A-Za-z]{3})[a-z]*\.? (\d{1,2}),? (\d{4})", text)
    if m and m[1].lower() in MONTHS:
        return date(int(m[3]), MONTHS[m[1].lower()], int(m[2]))
    m = re.search(r"\b(\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})", text)
    if m and m[2].lower() in MONTHS:
        return date(int(m[3]), MONTHS[m[2].lower()], int(m[1]))
    return None


def main():
    repo = c.worked_dir()
    orders = json.loads((repo / "orders.json").read_text())
    utc = {o["id"]: datetime.fromtimestamp(o["created_at"], timezone.utc) for o in orders}
    sub, notes = {}, []
    for place, zone in ZONES.items():
        p = subprocess.run([sys.executable, "report.py", "orders.json"], cwd=str(repo), capture_output=True,
                           text=True, timeout=60, env=dict(__import__("os").environ, TZ=zone))
        if p.returncode != 0 or not (repo / "report.html").exists():
            sub["%s_dates" % place] = sub["%s_times" % place] = False
            notes.append("%s: report.py failed: %s" % (place, (p.stdout + p.stderr)[-200:]))
            continue
        with c.static_server(repo) as base:
            with c.browser_page(timezone_id=zone) as (page, errors):
                page.goto(base + "/report.html")
                page.wait_for_load_state("load")
                layout = page.evaluate(LAYOUT, list(utc))
        wrong_day, wrong_time = [], []
        for oid, when in utc.items():
            heading, row = layout.get(oid, [None, ""])
            if parse_day(heading) != when.date():
                wrong_day.append("%s@%s under %r" % (oid, when.strftime("%m-%d %H:%M"), heading))
            if when.strftime("%H:%M") not in row and when.strftime("%-H:%M") not in row:
                wrong_time.append("%s row %r" % (oid, row.replace("\t", " ")[:60]))
        sub["%s_dates" % place] = not wrong_day
        sub["%s_times" % place] = not wrong_time
        sub["%s_no_page_errors" % place] = not errors
        notes.append("%s: wrong day %s; wrong time %s" % (place, wrong_day or "none", wrong_time or "none"))
    c.emit(sub, " || ".join(notes))


if __name__ == "__main__":
    main()
