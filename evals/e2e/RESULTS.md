# End-to-end results

pudding `f98eac0`, 2.1.283 (Claude Code), model `haiku`, 2026-09-27 20:16 UTC

| scenario | check | result |
|---|---|---|
| first_run | welcome shown | pass |
| first_run | .gitignore written | pass |
| first_run | armed logged | pass |
| silent | no decision on a plain answer | pass |
| block | mode written by your prompt | pass |
| block | confirmation shown | pass |
| block | blocked | pass |
| block | the block reached the agent | pass |
| warn | claim flagged, not blocked | pass |
| warn | flag shown to the user | pass |
| warn | the agent was not told | pass |
| off | no decision while off | pass |
| tamper | hand-edited off ignored | pass |
| tamper | user told | pass |
| help_status | help card shown | pass |
| help_status | status shown | pass |
| evidence_dir | setting written | pass |
| evidence_dir | new dir gitignored | pass |
| ui_change | UI change without a screenshot flagged | pass |
| completeness | a Done list beside a Not-done list flagged | pass |
| subagent | subagent's claim gated | pass |
| commands | stats reports the log | pass |
| commands | audit runs | pass |

**12/12 scenarios passed**.
