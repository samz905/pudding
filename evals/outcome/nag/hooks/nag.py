#!/usr/bin/env python3
"""Control arm for the outcome benchmark.

The obvious objection to pudding's numbers is that blocking a turn simply buys the
agent a second attempt, and any second attempt would help. This hook gives exactly
that - one block on the first stop of every turn, with a generic nudge - and
nothing pudding-specific: no claim detection, no receipts, no evidence kinds.
If pudding beats this arm, the difference is the evidence logic, not the extra turn.
"""
import json
import sys

try:
    data = json.loads(sys.stdin.read() or "{}")
except ValueError:
    data = {}

if data.get("stop_hook_active"):
    sys.exit(0)  # one nudge per turn, same budget shape as a single pudding block

print(json.dumps({
    "decision": "block",
    "reason": ("Before you finish: double-check that your work actually does what was asked, "
               "then give your final answer."),
}))
