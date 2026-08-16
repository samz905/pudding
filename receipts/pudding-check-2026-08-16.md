# Receipt: pudding_check.py v0 (2026-08-16)

tier: standard
env: local repo, Windows / git bash, Python 3.13

| claim | method | artifact | status |
|---|---|---|---|
| a valid receipt passes (the fixed v0-core receipt) | unit | `python pudding_check.py receipts/v0-core-2026-08-15.md` → "valid", exit 0 | verified |
| a verified row with no artifact is caught | unit | fixture e2e-noartifact.md → "verified with no artifact", exit 1 | verified |
| a real-user claim resting on api evidence is caught (method integrity) | unit | fixture e2e-methodlie.md → "claims real-user/e2e but method is 'api'" | verified |
| a missing Not-tested section is caught | unit | fixture e2e-noresidue.md → "no 'Not tested' section" | verified |
| a cleanup section with no counted number is caught | unit | fixture e2e-vibecleanup.md → "Cleanup asserts no number" | verified |
| the checker found a real bug on first contact | unit | our own v0-core receipt failed ("confirmed by ls", no count); fixed same session, now passes | verified |
| this receipt itself passes the checker | unit | `python pudding_check.py receipts/pudding-check-2026-08-16.md` → "valid" (run after writing) | verified |
| zero-dependency claim (stdlib only) | unit | imports: re, sys, pathlib only (grep import) | verified |
| design-match pair rule fires correctly | - | - | blocked: no design-match receipt exists yet to test against; fixture-only coverage deferred until one is real |

## Not tested (residue only)
- behavior on malformed markdown tables (multi-line cells) - out of declared tier, noted
  for when a real receipt hits it
- design-match pair rule against a real receipt (blocked above)

## Cleanup
- e2e-* fixture files created: 4, deleted: 4, remaining after rm: 0 (ls count: 0)
