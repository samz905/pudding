---
name: pudding-stats
description: Show how many of this project's done-claims actually carried evidence, from pudding's own log.
allowed-tools: [Read, Bash]
---

Report this project's claim record from `.claude/pudding.local.jsonl`:

!`python3 -c "import json,collections;c=collections.Counter();[c.update([json.loads(l).get('event','?')]) for l in open('.claude/pudding.local.jsonl')] if __import__('os').path.exists('.claude/pudding.local.jsonl') else None;print(dict(c))" 2>/dev/null || echo "no pudding log in this project yet"`

Present it plainly, in this order:

1. **claims made** — `earned` + `blocked` + `unearned`
2. **earned** — the claim had a matching row, first time
3. **blocked** — the claim was stopped for having no matching evidence
4. **shipped unearned** — went out with a scar because the mode was `warn`
5. the percentage of done-claims that carried evidence

Say the number plainly even when it is unflattering, and especially then — a
flattering summary of an accountability log is the exact failure being measured.
Do not editorialise the number upward, and do not add claims the log does not hold.
