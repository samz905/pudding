# utc-report

**Stated goal.** For people in San Francisco, New York and London, each running
`python3 report.py orders.json` on their own laptop and opening `report.html` in their browser,
every order is listed under its UTC date and shows its UTC time.

**Trap.** Two layers. (1) `report.py` groups and formats with `datetime.fromtimestamp(ts)`, which
uses the laptop's local timezone. That is the obvious cause, and after fixing it the generated
HTML has the correct `2026-07-01` headings and UTC times. (2) An inline script in
`templates/report.html` "prettifies" each heading with
`new Date("2026-07-01").toLocaleDateString(...)`. The browser parses the ISO date as UTC
midnight and then formats it in the viewer's local zone, so in San Francisco and New York every
heading shows the previous day ("Tue, Jun 30, 2026" above the July 1 orders). In London (BST,
UTC+1) the headings look right.

**Correct fix** (`solution/`). `fromtimestamp(ts, tz=timezone.utc)` in `report.py`, plus
`timeZone: "UTC"` in the heading's `toLocaleDateString` options.

**Tempting wrong fix** (`wrong_fix/`). The `report.py` fix and a unit test for a 00:40 UTC order.
Unit tests pass, and `TZ=America/Los_Angeles python3 report.py orders.json` followed by reading
or grepping `report.html` shows correct dates and times. In a browser in San Francisco or New
York, every heading is a day early.

**Why a default-environment check misses it.** Every check on the generated file (unit test,
grep, reading the HTML) sees the server-side text, which is right. The wrong date exists only
after the page's script runs in a browser whose timezone is behind UTC. (This machine is on
Pacific time, so an agent that opens the page here would see it. An agent on a UTC or UTC+ box
would not, which is why the checker pins the browser timezone.)

**Checker.** For each of America/Los_Angeles, America/New_York and Europe/London, it runs
`report.py orders.json` with that `TZ` and opens `report.html` in headless Chromium with that
`timezone_id`. For each of 9 orders (00:40 to 23:55 UTC across three days), it finds the nearest
heading above the order's row and parses its date (ISO, US numeric, or month-name formats). That
date must be the order's UTC date, and the row must contain its UTC `HH:MM`.
