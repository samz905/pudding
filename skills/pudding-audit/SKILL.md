---
name: pudding-audit
description: Count how many times your coding agent claimed work was done across your past Claude Code sessions, and how often it left proof. Read-only, local, prints counts only.
argument-hint: "[--here] [--examples N]"
allowed-tools: [Bash]
---

Run this and show the user its output exactly as printed, in a code block:

!`python3 "${CLAUDE_PLUGIN_ROOT}/skills/pudding/scripts/audit.py" $ARGUMENTS`

Then add at most two plain sentences. Do not soften the numbers, and do not add
claims the output does not contain. If it reports no transcripts, say where it
looked. Nothing here leaves the machine; say so if the user asks.
