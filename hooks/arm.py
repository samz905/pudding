#!/usr/bin/env python3
"""SessionStart / SubagentStart: tell the agent the rules before it writes the claim.

SessionStart does not reach subagents (ponytail hit this as their #252), and in a
subagent-driven workflow the subagents are where done-claims originate - so both
events are wired, and both get the JSON form, which is the only shape SubagentStart
accepts.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pudding_core as core  # noqa: E402

PROTOCOL = """\
\U0001F36E PUDDING ARMED - mode: {mode}

A completion claim is earned by attached evidence, never asserted from memory. Before
saying done / it works / verified / deployed, there must be a row in a receipt at
<project root>/receipts/<feature>-<date>.md - that exact folder, not a receipts/ dir
inside some subproject - written WHILE testing, not reconstructed after:

    | claim | method | artifact | status |

method is exactly one of: unit | api | db | wire | real-ui. It must match the claim:

    works as a real user / end to end   -> real-ui  (screenshot, DOM, the URL you drove)
    matches the design                  -> real-ui, paired against the reference
    deployed / live                     -> real-ui whose env names the DEPLOYED target
    the number is right                 -> db or real-ui showing the surfaced value move
    the row / event is written          -> db
    the request / webhook fires         -> wire
    the bug is fixed                    -> the repro, re-run, now failing to reproduce
    faster / lighter                    -> a before -> after pair
    the logic is correct                -> unit/api: necessary, never sufficient

A thousand unit rows never add up to one "works as a real user". Cannot reach something?
Record it as a row with status `blocked: <why>` and say so - a gap you name is honest, a
gap you omit reads as covered.

The Stop hook checks this. An unearned claim does not end the turn.{extra}
"""

NUDGE = """

(pudding can show a live count in your statusline - ask the user once if they want it,
then stop asking.)"""


def main():
    data = core.read_hook_input()
    event = data.get("hook_event_name", "SessionStart")
    root = core.project_dir()
    mode, _, _ = core.read_mode(root)

    if event == "SessionStart":
        core.log({"event": "armed", "session_id": data.get("session_id", ""), "mode": mode}, root)

    if mode == "off":
        core.emit({})

    extra = ""
    if event == "SessionStart":
        sentinel = Path.home() / ".claude" / ".pudding-statusline-nudged"
        if not sentinel.exists():
            try:
                sentinel.parent.mkdir(parents=True, exist_ok=True)
                sentinel.write_text("1")
                extra = NUDGE
            except Exception:
                pass

    core.emit({"hookSpecificOutput": {
        "hookEventName": event,
        "additionalContext": PROTOCOL.format(mode=mode, extra=extra),
    }})


def demo():
    assert "real-ui" in PROTOCOL and "{mode}" in PROTOCOL
    out = PROTOCOL.format(mode="block", extra="")
    assert "PUDDING ARMED - mode: block" in out and out.count("->") >= 9
    print("arm: ok")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
