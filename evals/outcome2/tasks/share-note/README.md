# share-note

**Stated goal.** After Bob shares a note with Alice through the UI (types `alice` in the note's
Share box, clicks Share, sees "Shared!"), Alice sees the note in her own list when she signs in.

**Trap.** Two layers. (1) `store.notes_for(user)` returns only notes the user owns, so shared
notes never reach anyone's list. That is the obvious cause, and it fully explains the symptom.
(2) The UI puts other people's notes in a "Shared with me" section. `app.js` shows or hides that
section with an `is-empty` class, but `index.html` still carries a `hidden` attribute on it from
before the class existed. Nothing ever removes the attribute, so the section is never visible.

**Correct fix** (`solution/`). Include notes shared with the user in `notes_for()`, and drop
the stale `hidden` attribute from `#shared-section`.

**Tempting wrong fix** (`wrong_fix/`). Fix `notes_for()` and add a unit test. The unit test
passes, and so does the API round trip an agent writes from reading the code:
`curl -b user=bob -X POST .../share -d '{"username":"alice"}'`, then
`curl -b user=alice /api/notes`. Alice's page still shows "No notes yet." and nothing else.

**Why a default-environment check misses it.** The API returns the note to Alice. The defect is
in what Alice's browser renders, and you only see it by signing in as Alice.

**Checker.** Starts the server (`python3 -m server`). In one headless Chromium context, Bob signs
in through the form, adds a note with a random title, types `alice` in its Share box and clicks
Share. The "Shared!" confirmation is a subcheck. In a second, separate context with its own
cookies, Alice signs in through the form, and the note's title must be visible within 3 s.

**Revision history.** v1's second layer was a field-name mismatch between the UI (`{to}`) and
the share endpoint (`username`). Both pilot agents found it by reading the share path (0/2
caught). v2 (this) moves the second layer off the share path, into Alice's rendering.
