#!/usr/bin/env python3
"""UserPromptSubmit: the only thing that may change pudding's strictness.

This hook reads the user's own typed prompt, before it reaches the model, and
writes the mode itself. That is deliberate. If the agent were the one flipping the
switch, the tool would disable itself on exactly the night it was needed - so the
only way to make pudding easier on the agent is for the human to type it.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pudding_core as core  # noqa: E402

CMD = re.compile(r"^\s*[/@]?pudding[ -]?(?:mode\s+)?(block|warn|off|status|help|statusline)\b", re.I)
EVIDENCE_CMD = re.compile(r"^\s*[/@]?pudding\s+evidence\s+(\S+)", re.I)

HELP = """\
\U0001F36E pudding - a done-claim has to carry matching evidence

  /pudding status            current mode, and which of your prompts set it
  /pudding block             no matching evidence, no end of turn   (default)
  /pudding warn              claims go through, unearned ones get flagged
  /pudding off               disarmed for this project
  /pudding evidence <dir>    where screenshots must be saved
  /pudding statusline        show earned/blocked counts in your statusline
  /pudding-stats             how many of this project's claims had evidence
  /pudding-audit             count the done-claims in your past sessions

  receipts  receipts/<feature>-<date>.md      committed with your code
  evidence  {evidence}/<date>-<run>/    gitignored
  only your typed /pudding commands change the mode - never the agent"""

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

    if want == "help":
        card = HELP.format(evidence=core.evidence_dir(root))
        core.emit({"systemMessage": card, "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "[pudding] The help card is already on the user's screen. "
                                 "Reply in one line; do not repeat it.",
        }})

    if want == "statusline":
        msg = install_statusline()
        core.emit({"systemMessage": msg, "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "[pudding] " + msg + " Acknowledge in one line.",
        }})

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


def install_statusline():
    """Point the user's statusline at pudding - never over an existing one.

    The script is copied to a stable path first: the plugin itself lives in a
    versioned cache dir that is replaced on every update, so pointing settings at
    it would break the statusline on the next upgrade.
    """
    import json
    import shutil
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    src = Path(__file__).resolve().parent.parent / "statusline" / "pudding.py"
    dst = base / "pudding-statusline.py"
    try:
        shutil.copyfile(src, dst)
    except Exception as e:
        return f"\U0001F36E pudding: could not copy the statusline script ({e})."
    cmd = f'python3 "{dst}"'
    settings_path = base / "settings.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8-sig")) if settings_path.exists() else {}
    except Exception:
        return ("\U0001F36E pudding: your settings.json did not parse, so I left it alone. "
                f"Add a statusLine with command: {cmd}")
    if settings.get("statusLine"):
        return ("\U0001F36E pudding: you already have a statusline, so I did not touch it.\n"
                f"   To add pudding to it, append the output of:  {cmd}")
    settings["statusLine"] = {"type": "command", "command": cmd}
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return "\U0001F36E pudding: statusline installed. Restart Claude Code to see it."


def demo():
    import tempfile
    import tempfile, json as _j
    with tempfile.TemporaryDirectory() as cfg:
        os.environ["CLAUDE_CONFIG_DIR"] = cfg
        assert "installed" in install_statusline()
        st = _j.loads((Path(cfg) / "settings.json").read_text())["statusLine"]["command"]
        assert "pudding-statusline.py" in st and (Path(cfg) / "pudding-statusline.py").exists()
        # an existing statusline is never replaced
        (Path(cfg) / "settings.json").write_text(_j.dumps({"statusLine": {"type": "command", "command": "mine"}}))
        assert "did not touch" in install_statusline()
        assert _j.loads((Path(cfg) / "settings.json").read_text())["statusLine"]["command"] == "mine"
        del os.environ["CLAUDE_CONFIG_DIR"]
    assert "block" in HELP and "/pudding-audit" in HELP
    for text in ["/pudding evidence docs/proof", "/pudding evidence .pudding/shots"]:
        assert EVIDENCE_CMD.match(text), text
    assert not EVIDENCE_CMD.match("/pudding warn")
    for text, want in [("/pudding help", "help"), ("/pudding statusline", "statusline"),
                       ("/pudding warn", "warn"), ("  /pudding off", "off"),
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
