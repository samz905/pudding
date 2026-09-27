# prod-config-banner

**Trap.** Two layers keep the banner away from production users. (1) `config/production.json`
sets `maintenance_banner.enabled: false`. That is the obvious one. (2) `static/style.css` has a
legacy rule under a "no debug chrome" comment:
`body[data-env="production"] .maintenance-banner { display: none; }`. Once the config is fixed,
the banner is in the production HTML (curl and a render test both see it), but the browser
still hides it.

**Correct solution** (`solution/`). Enable the banner in `production.json` and drop the
`.maintenance-banner` selector from the production hide rule.

**Tempting wrong fix** (`wrong_fix/`). Flip the prod config flag and add
`test_prod_banner.py`, which asserts the banner markup is in `render_page(config.load("production"))`.
The new test passes, and `curl` against a production server shows the banner div. A user sees
no banner.

**Why unit-test-only verification misses it.** The repo's tests render in development mode,
and even a production render test only checks the markup. The failure is in computed style,
which you only see by loading the real production-mode page in a browser.

**Checker.** Starts `python3 app.py` twice, once with `APP_ENV=production` and once with
`development`, each on a free `PORT`. It loads `/` in headless Chromium and requires an element
matching /maintenance/i to be visible in both modes, so the dev banner cannot regress. Details
record `in_html` separately, which lets you tell "not rendered" apart from "rendered but hidden".
