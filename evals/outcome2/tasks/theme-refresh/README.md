# theme-refresh

**Stated goal.** The theme the user picks (dark or light) is still showing after a page refresh.

**Trap.** Two layers. (1) The toggle's click handler in `static/app.js` calls `applyTheme()` but
never `saveTheme()`, so nothing is stored. That is the obvious cause, and `app.js` already reads
`savedTheme()` at startup, so adding the save call looks complete. (2) The server renders the
account display prefs into the page (`window.__PREFS__`, defaults in `server.py` include
`"theme": "light"`), and `static/prefs.js` runs after `app.js` on DOMContentLoaded and copies
every pref onto `<html data-*>`. It overwrites the restored theme with the account value. The
word "theme" never appears in `prefs.js`.

**Correct fix** (`solution/`). Save the choice where the page actually reads it on load: the
toggle also `PUT`s `/api/prefs` with `{theme}` (and updates `window.__PREFS__`). Dropping
`theme` from what `prefs.js` applies, or making it lose to the local choice, also passes.

**Tempting wrong fix** (`wrong_fix/`). Call `saveTheme(next)` in the click handler. Reading the
code, the loop looks closed (save on click, restore on load), and `localStorage` does hold
`"dark"` afterwards. After a refresh the page is light again.

**Why a default-environment check misses it.** No unit test covers the page. Code reading and
inspecting `localStorage` both say it works. You only see it by refreshing the real page and
looking at it after the page has finished loading.

**Checker.** Starts the server (`python3 -m server`), opens `/` in headless Chromium, and judges the theme by
the body's computed background luminance (what the user sees, independent of how the agent
implements it). It picks the other theme, refreshes, and checks. Then it picks the first theme
again, refreshes, and checks again. It waits for network idle plus 0.4 s after each load.
