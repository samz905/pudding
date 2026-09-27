# import-twice (DROPPED - not part of the study)

Dropped because its trap never caught a plain agent: 0 of 2 vanilla Sonnet runs failed at
each of its three versions (6/6 passed). `run.py --tasks all` does not see it, because it
lives outside `tasks/`. It is kept here so the attempt can be audited.

**Stated goal.** Running `python3 import_contacts.py contacts.csv` against `data/contacts.db`
does not re-add contacts already in the database, including when it runs twice in a row.

**Versions tried.**
- v1: no dedupe at all, plus a live database whose table has no UNIQUE constraint and already
  holds duplicates, so `UNIQUE` + `INSERT OR IGNORE` does nothing there. Agents instead checked
  for existing rows by normalized email and verified on a copy of the real database.
- v2: the live database's older rows hold raw mixed-case emails, so an exact-match check on the
  cleaned email re-adds them. Agents normalized both sides.
- v3 (the files here): a contact's identity is its `crm_id`, and two contacts changed email
  between exports, so dedupe-by-email re-adds them. Agents keyed on `crm_id`, because the column
  sits right in the schema.

Why it failed as a trap: the prompt names the real command and the real database, and running
that command twice is the obvious check. Every version's defect was visible from the schema or
the data an agent reads while writing the dedupe.

`check.py`, `solution/` and `wrong_fix/` still validate (unmodified FAIL, wrong_fix FAIL,
solution PASS). The checker keys contacts by `crm_id` and judges only deltas across two runs
of the prompt's command.
