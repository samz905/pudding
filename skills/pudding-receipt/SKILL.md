---
name: pudding-receipt
description: Start a pudding receipt for a piece of work, so evidence gets recorded while testing instead of reconstructed afterwards.
argument-hint: <feature-name>
allowed-tools: [Read, Write, Glob, Bash]
---

Create `receipts/<feature-slug>-<YYYY-MM-DD>.md` for: **$ARGUMENTS**

Today: !`date +%Y-%m-%d` · Existing receipts: !`ls receipts/*.md 2>/dev/null | tail -5`

Write the file with this shape, then keep filling it **as you test** — a receipt
written afterwards is a memory, and memory is what pudding exists to distrust:

```markdown
# Receipt: <feature> (<YYYY-MM-DD>)
tier: smoke | standard | exhaustive
env: <where artifacts are captured — name the real thing, not the convenient one>

| claim | method | artifact | status |
|---|---|---|---|
| <one specific, falsifiable claim> | unit\|api\|db\|wire\|real-ui | <pointable evidence> | verified |

## Not tested (residue only)
- <genuine blocker, surfaced for a decision> / <explicitly out of declared tier>

## Cleanup
- <tag> rows remaining: 0
```

Before writing rows, plan the proof: who the actors are, which effects must be
traced trigger → persistence → surface, and which edges the tier demands. The
`pudding` skill has the full protocol.

Rules that decide whether the row counts:
- **method must match the claim.** A real-user claim needs `real-ui`. A deployed
  claim needs `real-ui` whose `env` names the deployed target, not localhost.
- **artifact must be pointable by someone else** — a path, a query and its result,
  a before→after pair. Prose is not an artifact.
- **a claim you cannot reach is a row**, `blocked: <why>`, not a silent omission.

Then check it: `python3 <plugin>/skills/pudding/scripts/pudding_check.py receipts/<file>.md`
