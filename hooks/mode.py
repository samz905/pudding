#!/usr/bin/env python3
"""UserPromptSubmit: the only thing that may change pudding's strictness.

This hook reads the user's own typed prompt, before it reaches the model, and
writes the mode itself. That is deliberate. If the agent were the one flipping the
switch, the tool would disable itself on exactly the night it was needed - so the
only way to make pudding easier on the agent is for the human to type it.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pudding_core as core  # noqa: E402

CMD = re.compile(r"^\s*[/@]?pudding[ -]?(?:mode\s+)?(block|warn|off|status)\b", re.I)
EVIDENCE_CMD = re.compile(r"^\s*[/@]?pudding\s+evidence\s+(\S+)", re.I)

BLURB = {
    "block": "block - a claim without matching evidence does not end the turn.",
    "warn": "warn - claims still ship, but unearned ones are marked and logged.",
    "off": "off - the gate is disarmed for this project.",
}


def main():
    data = core.read_hook_input()
    prompt = data.get("prompt", "") or ""
    root = core.project_dir()

    ev = EVIDENCE_CMD.match(prompt)
    if ev:
        path = ev.group(1).strip().strip("/")
        core.write_setting("evidence", path, prompt.strip(), data.get("session_id", ""), root)
        core.log({"event": "setting", "evidence": path, "session_id": data.get("session_id", "")}, root)
        core.ensure_ignored(root)  # the new location, not the old one
        core.emit({"systemMessage": f"\U0001F36E pudding: real-ui artifacts now live under {path}/"})

    m = CMD.match(prompt)
    if not m:
        # Every other turn: say where THIS run's evidence goes, before the work starts.
        # The agent cannot save to the right folder if it only learns the path at the block.
        if core.read_mode(root)[0] != "off":
            core.emit({"hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "[pudding] Screenshots and other real-ui artifacts for "
                                     "this run go in " + core.run_folder(data.get("prompt_id", ""), root)
                                     + "/ - a file the user can open, not a temp dir.",
            }})
        core.emit({})

    want = m.group(1).lower()

    if want == "status":
        mode, authorized, fm = core.read_mode(root)
        note = "" if authorized else " (reverted: the mode file was weakened without a /pudding command)"
        msg = f"pudding is {mode}{note}"
        if fm.get("at"):
            msg += f" - set {fm['at'][:19]} by: {fm.get('prompt', '?')}"
        msg += f"; evidence -> {core.evidence_dir(root)}/"
        core.emit({"systemMessage": msg, "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"[pudding] {msg}. Tell the user plainly; do not change it yourself.",
        }})

    core.write_mode(want, data.get("prompt", "").strip(), data.get("session_id", ""), root)
    core.log({"event": "mode", "mode": want, "session_id": data.get("session_id", "")}, root)
    core.emit({
        "systemMessage": f"\U0001F36E pudding: {BLURB[want]}",
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"[pudding] The user set pudding to {want}. {BLURB[want]} "
                "Acknowledge in one line. You cannot set this yourself - only their typed "
                "/pudding command writes it, and weakening the file any other way reverts to block."
            ),
        },
    })


def demo():
    import tempfile
    for text in ["/pudding evidence docs/proof", "/pudding evidence .pudding/shots"]:
        assert EVIDENCE_CMD.match(text), text
    assert not EVIDENCE_CMD.match("/pudding warn")
    for text, want in [("/pudding warn", "warn"), ("  /pudding off", "off"),
                       ("pudding block", "block"), ("/pudding-mode warn", "warn"),
                       ("/pudding status", "status")]:
        assert CMD.match(text) and CMD.match(text).group(1).lower() == want, text
    for text in ["tell me about pudding", "the pudding gate blocks claims",
                 "/puddings warn", "make pudding warn about things"]:
        assert not CMD.match(text), text
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        core.write_mode("warn", "/pudding warn", "s1", root)
        assert core.read_mode(root)[0] == "warn"
        assert "/pudding warn" in core.state_path(root).read_text()
    print("mode: ok")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
