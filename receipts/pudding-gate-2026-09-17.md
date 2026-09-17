# Receipt: pudding v1 gate (2026-09-17)
tier: standard
env: macOS, python3.12, scratch git repo; hooks driven by piping real payloads to the scripts. NOT a live Claude Code session - see blocked rows.

| claim | method | artifact | status |
|---|---|---|---|
| claim detection finds the 11 families and ignores hedged, imperative and quoted sentences | unit | `hooks/claims.py --demo`, 18 assertions incl. "Verifying ... before I tell you it works" -> no claim | verified |
| detector fires on 5.4% of real assistant messages, not 14% | unit | replay over 205 messages from 6 x-account transcripts: 14% naive -> 5.4% tuned | verified |
| stripping quoted spans does not fabricate claims by merging fragments | unit | `claims.py --demo`; bug found in replay ("isn proven it works all green verified end to end"), fixed by breaking the sentence at each strip | verified |
| an apostrophe in a contraction is not treated as a quote delimiter | unit | replay produced fragment "s deployed / it"; `strip_quoted("it's deployed / it's live and it works")` now returns the string intact | verified |
| gate blocks a real-user claim backed only by unit rows | api | `hooks/gate.py --demo`; piped Stop payload -> `{"decision":"block"}` with `needs real-ui` | verified |
| gate passes the same claim once a real-ui row exists | api | piped Stop payload in scratch repo -> empty output (turn allowed), log event `earned` | verified |
| gate blocks a deployed claim whose receipt env says localhost | api | piped payload, env `localhost:8724` -> block, "localhost is not the deploy" | verified |
| gate returns empty while `stop_hook_active` is true | api | piped payload with the flag -> no output, exit 0 | verified |
| `/pudding warn` writes the mode and records the authorizing prompt | api | piped UserPromptSubmit -> `.claude/pudding.local.md` holds `set_by: user-prompt`, `prompt: "/pudding warn"` | verified |
| a mode weakened without a typed command reverts to block | unit | `pudding_core.py --demo` + `gate.py --demo`: hand-written `mode: off` -> block + "weakened" systemMessage | verified |
| warn mode scars instead of blocking | api | piped payload under warn -> `systemMessage` only, no `decision` key | verified |
| receipt linter and gate agree on rows (one parser) | unit | `pudding_check.py --demo`, 5 assertions; `parse_rows` now shared by both | verified |
| session-start timestamp is timezone-correct | api | bug found by the piped run (UTC parsed as local put session start 5.5h ahead, so no receipt was ever fresh); fixed, retest passes | verified |
| statusline reads the log and is silent when absent | unit | `statusline/pudding.py --demo`; `--stats` on the scratch log printed 6 claims, 1 earned | verified |
| plugin and marketplace manifests are valid | api | `claude plugin validate . --strict` and `./.claude-plugin/plugin.json --strict` both "Validation passed" | verified |
| hooks fire in a live Claude Code session | - | - | blocked: hooks load at session start and never hot-reload, so this cannot be tested from inside the session that would need to load them. Needs `claude --plugin-dir` + restart. |
| `last_assistant_message` contains clean final text (no thinking blocks, sane joining of multiple text blocks) | - | - | blocked: same restart. The field is in the 2.1.274 schema and documented as "text content of the last assistant message", but the extraction function was not decompilable. A transcript fallback is specced but not written. |
| the block renders as `⏿ <stopReason>` under the claim in the terminal | - | - | blocked: same restart. No `preventedContinuation: true` record exists in any transcript on this machine, so the rendering is read from the binary's renderer, never observed. |
| typing `/pudding warn` in the real composer reaches UserPromptSubmit rather than being eaten as an unknown slash command | - | - | blocked: same restart. ponytail relies on the identical mechanism at 140k stars, which is evidence but not proof for this command name. |
| SubagentStop blocks a subagent that claims done with no receipt | - | - | blocked: same restart. |
| the statusline counter appears in the terminal | - | - | blocked: needs a `statusLine` entry in settings.json, which is the user's file and the user's call. |

## Not tested (residue only)
- Every `blocked` row above: all six need a Claude Code restart with the plugin loaded, which is the user's action and cannot be performed from inside this session.
- Windows behaviour. `read_hook_input` falls back to a plain blocking read there (no `select` on Windows pipes) and relies on the hooks.json timeout; marked with a `ponytail:` comment.
- Long-session behaviour of the 6-hour receipt-freshness fallback when the `armed` log line is missing.

## Cleanup
- scratch repos created under $TMPDIR: 2, both inside mktemp dirs, no writes outside them
- files written to this repo outside the plugin tree: 0
- `__pycache__` directories remaining: 0 (gitignored)
