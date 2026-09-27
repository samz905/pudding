# Receipt format (v1) - normative

A receipt is a markdown file the agent fills **while** testing, from which the
done-report is generated. Plain markdown + a five-value method enum. Zero configuration.
Agent-agnostic by construction.

## Files

- `receipts/<feature-slug>-<YYYY-MM-DD>.md` at the **project root** - the one folder the
  gate reads. Committed with the code, so the proof travels with it.
- `receipts/evidence/<YYYY-MM-DD>-<request>/` - screenshots, DOM captures, logs. One
  folder per user request, named to the agent at the start of every prompt. Gitignored
  by default; `/pudding evidence <dir>` moves it.

## Schema

```markdown
# Receipt: <feature> (<YYYY-MM-DD>)
tier: smoke | standard | exhaustive     # declared BEFORE testing; proof attaches to the diff
env: <where artifacts were captured>    # e.g. "real Chrome, Windows" / "headless chromium" / "deployed preview"

| claim | method | artifact | status |
|---|---|---|---|
| <one specific claim> | unit|api|db|wire|real-ui | <pointable evidence> | verified |
| <a claim you could not reach> | - | - | blocked: <why - user decision needed> |
| <a claim the user chose to skip> | - | <who waived, date, quote if short> | waived |

## Not tested (residue only)
- <genuine blocker, surfaced> / <explicitly out of declared tier>

## Cleanup
- <tag pattern> rows remaining: 0    # asserted with a query, not assumed
```

## Field rules

- **tier** - declared up front, one of three. Raising scope mid-run is fine; lowering it
  to dodge a failing row is not.
- **env** - first-class because "verified in headless Chromium" ≠ "works in the user's
  Windows Chrome". Name the real environment; one receipt per env if they differ.
- **claim** - one specific, falsifiable statement. "Auth works" is not a claim;
  "login with wrong password shows the error and does not set a session cookie" is.
- **method** - exactly one of `unit` · `api` · `db` · `wire` · `real-ui`. `wire` = a
  captured payload (request/webhook/queue message). Method must MATCH the claim kind
  (see SKILL.md gate table). The enum is closed: a new method name is a spec change,
  not a judgment call.
- **artifact** - pointable by a third party: file path, screenshot path, query + result,
  before→after values, named test. Prose is not an artifact.
  A `real-ui` artifact must be a **file inside the evidence folder** that exists, is
  non-empty, and - for .png/.jpg/.gif/.webp - really is an image. A path in a temp dir,
  or an image read into the agent's own context and never saved, does not count.
- **status** - `verified` · `unverified` · `blocked: <reason>` · `waived: <who/when>`.
  `blocked` surfaces a decision; `waived` records one already made. Both are visible
  rows, never deletions.
- **Not tested** - residue only: blockers and out-of-tier items. Anything testable and
  in-scope belongs in the table as a row, tested.
- **Cleanup** - test data is tagged at creation and its absence asserted at the end.

## Freshness

A receipt only counts if it is newer than the code it describes: newer than every file
`git status` reports changed and every commit that touched non-runtime files since.
Evidence written before the code moved on is evidence for different work.

## Sets

A claim about a set - "all items built", "everything except X", or a Done list beside a
Not-done list - needs **one verified row per item**. One row cannot stand in for fifteen.

## Validity

A receipt is **invalid** if: a `verified` row has no artifact · a claim's method doesn't
match its kind per the gate table · the Not-tested section is missing · cleanup is
unasserted. An invalid receipt means the done-claim is not earned. `pudding_check.py`
(optional, single file) lints exactly these rules.
