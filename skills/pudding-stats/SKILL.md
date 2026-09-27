---
name: pudding-stats
description: Show how many of this project's done-claims actually carried evidence, from pudding's own log.
allowed-tools: [Bash]
---

Show the user this report exactly as printed, in a code block. Do not restate or
recompute any number in it:

!`python3 "${CLAUDE_PLUGIN_ROOT}/statusline/pudding.py" --stats < /dev/null`

Then at most one plain sentence. If the numbers are unflattering, leave them that way.
