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

Four rules that are not negotiable:
 1. Changed code this session and handing back (not asking a question, not mid-task)?
    Leave at least one verified row for it first - what you ran and what you saw -
    however you phrase the report. The receipt has to be newer than the code.
 2. A real-ui artifact is a FILE the user can open, saved in THIS RUN'S evidence folder
    (named for you on every prompt). Reading an image into your own context shows it to
    nobody, and a path under /var/folders is a file nobody will ever open.
 3. Changed any UI? A screenshot is required whether or not you claim anything about it.
 4. Calling a SET of things done ("all items built", "everything except X", or a Done
    list beside a Not-done list) needs one row PER ITEM. One row cannot stand in for
    fifteen - that is how a whole unbuilt feature once sat inside a "done" list.

A thousand unit rows never add up to one "works as a real user". Cannot reach something?
Record it as a row with status `blocked: <why>` and say so - a gap you name is honest, a
gap you omit reads as covered.

The Stop hook checks all of this. {consequence}{extra}
"""

WELCOME = """\
\U0001F36E pudding is armed ({mode}).
   {promise}
   receipts   {receipts:<34}  committed
   evidence   {evidence:<34}  gitignored{ignored}
   /pudding help  \u00b7  /pudding {other}  \u00b7  /pudding off"""

CONSEQUENCE = {
    "block": "Unproven work does not end the turn.",
    "warn": "Unproven work is flagged to the user as unproven.",
}
PROMISE = {
    "block": "Your agent can't end a turn on \"done\" or \"it works\" without matching evidence.",
    "warn": "When your agent says \"done\" without matching evidence, you'll see it flagged.",
}

NUDGE = """

(pudding can show a live count in your statusline - ask the user once if they want it,
then stop asking.)"""


def main():
    data = core.read_hook_input()
    event = data.get("hook_event_name", "SessionStart")
    root = core.project_dir()
    mode, _, _ = core.read_mode(root)

    first_run = event == "SessionStart" and not core.has_armed_before(root)
    added = []
    if event == "SessionStart":
        core.log({"event": "armed", "session_id": data.get("session_id", ""), "mode": mode}, root)
        if mode != "off":
            added = core.ensure_ignored(root)

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

    out = {"hookSpecificOutput": {
        "hookEventName": event,
        "additionalContext": PROTOCOL.format(mode=mode, consequence=CONSEQUENCE[mode], extra=extra),
    }}
    if first_run:
        # Shown once per project. Without it a fresh install is silent until the
        # first block, which reads as "it didn't install".
        note = ("\n   (added " + " and ".join(added) + " to .gitignore)") if added else ""
        out["systemMessage"] = WELCOME.format(mode=mode, promise=PROMISE[mode],
                                              other="block" if mode == "warn" else "warn",
                                              receipts="receipts/<feature>-<date>.md",
                                              evidence=core.evidence_dir(root) + "/<date>-<run>/",
                                              ignored=note)
    core.emit(out)


def demo():
    for mode, other in (("warn", "block"), ("block", "warn")):
        w = WELCOME.format(mode=mode, promise=PROMISE[mode], other=other,
                           receipts="receipts/x.md", evidence="receipts/evidence/", ignored="")
        assert f"pudding is armed ({mode})" in w and f"/pudding {other}" in w and PROMISE[mode] in w
        out = PROTOCOL.format(mode=mode, consequence=CONSEQUENCE[mode], extra="")
        assert f"PUDDING ARMED - mode: {mode}" in out and out.count("->") >= 9
        assert "Changed code this session" in out and CONSEQUENCE[mode] in out
    print("arm: ok")

if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
