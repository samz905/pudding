# profile-name

**Stated goal.** After changing the display name in Settings, clicking Save and reloading the
page, the header greets the user with the new name.

**Trap.** Two layers. (1) `profiles.update()` applies the edit and returns it but never calls
`save()`, so nothing reaches `profile.json`. That is the obvious cause, and it fully explains
the symptom. (2) `GET /api/profile`, which the header reads on every load, is served with
`Cache-Control: max-age=300` (`config.API_MAX_AGE`, applied in `server.py`'s `send()`). Saving
goes to a different URL (`POST /api/settings`), so the browser has no reason to invalidate its
cached profile. On reload, the header (and the settings field) show the cached old name for
5 minutes.

**Correct fix** (`solution/`). Call `save()`, and stop the browser caching a response that
changes whenever settings are saved (`no-store` on `/api/profile`). Busting the cache from the
client (`fetch(..., {cache: "no-store"})` or a query string) also passes.

**Tempting wrong fix** (`wrong_fix/`). Add the missing `save()` and a unit test for it. The
test passes. `curl /api/profile` after a save shows the new name. A fresh browser opened after
the save shows the new name too, because it has no cache. The user's own reload still shows
the old one.

**Why a default-environment check misses it.** curl and new browser contexts never hold a
cached copy. Only the prompt's flow does: a browser that loaded the page, saved, then reloaded.

**Checker.** Starts the server (`python3 -m server`). In one headless Chromium context it opens
`/` and waits for network idle, so the header has loaded once, as it has for any returning
user. It types a random new name into the "Display name" field, clicks Save, waits for "Saved",
reloads, and requires the header to contain the new name within 3 s.

**Revision history.** This replaces `import-twice` (see `../../VALIDATION.md`). Its v1 kept the
stale copy in a localStorage cache in `header.js`. Both pilot agents followed "header" to that
file and fixed it (0/2 caught). v2 (this) moves the stale copy into HTTP caching.
