# persist-notes

**Trap.** `server.py` keeps notes in a module-level list. `store.py` already exists and looks
ready to wire in, and all its tests pass. But its round trip is broken: `append_note` writes a
bare JSON list, while `load_notes` expects `{"notes": [...]}` and swallows the error, returning
`[]`. Wiring the store into the server the obvious way therefore persists nothing that can be
read back. There is also a secondary edge: ids are `len(NOTES) + 1`, which has to keep working
after a reload.

**Correct solution** (`solution/`). Make `append_note` write `{"notes": notes}`, load notes at
server start, append on every POST, and take the next id from the max existing id.

**Tempting wrong fix** (`wrong_fix/server.py`). `NOTES = store.load_notes()` at import, plus
`store.append_note(note)` on POST, with `store.py` left untouched. `python3 -m unittest` passes
and POST still returns 201. After a restart, GET returns an empty list.

**Why unit-test-only verification misses it.** `test_store.py` tests load and append
separately, never one after the other. Only the real sequence shows the loss: POST, kill,
restart, GET.

**Checker.** Starts `python3 server.py` (cwd = repo, `PORT` set) and POSTs two uniquely tagged
notes. It stops the server with SIGTERM to the process group (what `kill <pid>` does, so
atexit-only saves fail), restarts, and GETs: both notes must be there. It then POSTs a third,
kills and restarts again: all three must be there and every id must be unique. It works with
any data file location the agent picks.
