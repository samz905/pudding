# prod-discount-code

**Stated goal.** Lowercase and mixed-case discount codes work at checkout on the live site,
which runs `APP_ENV=production python3 server.py`.

**Trap.** Two layers. (1) `discounts.lookup()` is case-sensitive (`CODES.get(code.strip())`).
That is the obvious cause and it fully explains the symptom. (2) In production, `assets.py`
serves `static/dist/checkout.js`, a bundle built by `build.py` that is stale: it still carries
an old client-side pre-check, `/^[A-Z0-9]{4,12}$/`, which rejects `save10` before any request
is sent. The source in `static/src/checkout.js` no longer has that check, so dev mode is fine
once (1) is fixed.

**Correct fix** (`solution/`). Make the lookup case-insensitive and rebuild the bundle
(`python3 build.py`), which drops the stale regex from `static/dist/checkout.js`.

**Tempting wrong fix** (`wrong_fix/`). Upper-case the code in `discounts.py` and add a unit
test for `save10`. The tests pass, and `curl -X POST /api/discount -d '{"code":"save10",...}'`
returns the 10% discount even against a production-mode server. The dev page works in a
browser too. The production page still says "Invalid code".

**Why a default-environment check misses it.** Every non-browser check (unit test, curl in
either mode) exercises the server only, and the server is fixed. A browser check in dev mode
loads `static/src`, which is fine. Only the page in the environment the prompt names loads
the stale bundle.

**Checker.** Starts the server (`python3 -m server`, so an agent's `pkill -f server.py` in a parallel run cannot hit it) with `APP_ENV=production` on a free port. In headless
Chromium it types `save10`, `Save10` and `SAVE10` (each on a fresh page load) into the code box,
clicks Apply, and requires the visible total to read $72.00 ($80.00 less 10%).
