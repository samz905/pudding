#!/usr/bin/env python3
"""Self-check for the pudding gate. Run: python3 hooks/test_gate.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "pudding" / "scripts"))

import pudding_core as core  # noqa: E402
from gate import MAX_BLOCKS_PER_PROMPT, decide, excerpt  # noqa: E402


def full(out):
    """Everything the block says, to either audience."""
    return (out.get("reason") or "") + "\n" + (out.get("hookSpecificOutput") or {}).get("additionalContext", "")


def main():
    # a real-ui row naming a file that does not exist is a promise, not proof
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _td:
        from gate import artifact_is_real
        _r = Path(_td)
        ev = _r / "receipts" / "evidence"
        ev.mkdir(parents=True)
        assert not artifact_is_real("receipts/evidence/ghost.png (before->after)", _r)
        (ev / "real.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
        assert artifact_is_real("receipts/evidence/real.png (before->after)", _r)
        assert not artifact_is_real("I looked at it in Chrome", _r)
        # a text file wearing a .png extension is not a screenshot
        (ev / "fake.png").write_text("definitely a screenshot")
        assert not artifact_is_real("receipts/evidence/fake.png", _r)
        (ev / "empty.txt").write_text("")
        assert not artifact_is_real("receipts/evidence/empty.txt", _r)
        (ev / "log.txt").write_text("GET /api 200")
        assert artifact_is_real("receipts/evidence/log.txt", _r), "non-image evidence just has to be non-empty"
        # a real file in a temp dir is still not somewhere the user will look
        stray = _r / "stray.png"; stray.write_bytes(b"x")
        assert not artifact_is_real("stray.png", _r), "outside the evidence dir is not evidence"

    import subprocess as sp
    import tempfile

    RECEIPT = """# Receipt: thing (2026-09-17)
tier: smoke
env: {env}

| claim | method | artifact | status |
|---|---|---|---|
{rows}

## Not tested (residue only)
- nothing
## Cleanup
- e2e-* rows remaining: 0
"""
    UNIT = "| the logic is right | unit | test_thing.py::test_ok | verified |"
    UI = ("| unlock works for a real user | real-ui | "
          "receipts/evidence/a.png before->after | verified |")

    def setup(td, rows, env="real Chrome, macOS"):
        root = Path(td)
        (root / "receipts").mkdir(parents=True, exist_ok=True)
        sp.run(["git", "init", "-q", str(root)], check=True)
        (root / "src.py").write_text("x = 1\n")  # dirty tree == source changed
        ev = root / "receipts" / "evidence"
        ev.mkdir(parents=True, exist_ok=True)
        (ev / "a.png").write_bytes(b"\x89PNG fixture")  # the row must point at a real file
        if rows is not None:
            (root / "receipts" / "r.md").write_text(RECEIPT.format(rows=rows, env=env))
        return root

    def run(root, msg, **kw):
        return decide({"last_assistant_message": msg, "session_id": "s1", **kw}, root)

    with tempfile.TemporaryDirectory() as td:
        root = setup(td, UNIT)
        # a real-user claim resting on unit rows is the whole thesis
        out = run(root, "It works end to end in the browser.")
        assert out.get("decision") == "block", out
        assert "no pudding" in out["reason"] and "real-ui" in out["reason"]
        assert len(out["reason"].splitlines()) <= 16, "short enough to read at a glance"
        assert "/var/" not in out["reason"] and "/tmp" not in out["reason"], "relative paths only"
        assert "receipts/evidence/" in out["reason"], "tells it where to save"
        # the harness recursion guard wins over everything
        assert run(root, "It works end to end.", stop_hook_active=True) == {}
        # no claim, no cost
        assert run(root, "Here is the plan. I will start on it now.") == {}
        # hedged honesty is never punished
        assert run(root, "Verifying on your real timeline before I tell you it works.") == {}

    with tempfile.TemporaryDirectory() as td:
        root = setup(td, UNIT + "\n" + UI)
        assert run(root, "It works end to end in the browser.") == {}, "real-ui row earns it"

    with tempfile.TemporaryDirectory() as td:  # deployed claims must not rest on localhost
        root = setup(td, UI, env="localhost:8724, headless chromium")
        assert run(root, "It is deployed and the dashboard is live.").get("decision") == "block"
        root2 = setup(tempfile.mkdtemp(), UI, env="https://x-account.vercel.app, real Chrome")
        assert run(root2, "It is deployed and the dashboard is live.") == {}

    with tempfile.TemporaryDirectory() as td:  # warn scars instead of blocking
        root = setup(td, UNIT)
        core.write_mode("warn", "/pudding warn", "s1", root)
        out = run(root, "It works end to end in the browser.")
        assert "decision" not in out and "no pudding" in out["systemMessage"], out
        core.write_mode("off", "/pudding off", "s1", root)
        assert run(root, "It works end to end in the browser.") == {}

    with tempfile.TemporaryDirectory() as td:  # tampering reverts to block and says so
        root = setup(td, UNIT)
        core.state_path(root).parent.mkdir(parents=True, exist_ok=True)
        core.state_path(root).write_text("---\nmode: off\n---\n")
        out = run(root, "It works end to end in the browser.")
        assert out.get("decision") == "block" and "weakened" in out["systemMessage"], out
        assert "no pudding, no done" in out["reason"], "the human reads reason on the block path"

    with tempfile.TemporaryDirectory() as td:  # a receipt older than the code is not evidence
        root = setup(td, UNIT + "\n" + UI)
        def commit(msg):
            sp.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
            sp.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", msg], check=True, capture_output=True)
        commit("baseline")
        (root / "receipts" / "r.md").touch()
        msg = "It works end to end in the browser."
        assert run(root, msg) == {}, "a receipt newer than the code earns it"

        (root / "noise.db-wal").write_text("churn")   # background writer, uncommitted
        assert run(root, msg) == {}, "a volatile artifact is not code"
        commit("data only")                            # ...and committing it changes nothing
        assert run(root, msg) == {}, "committing volatile data is not code"

        # Pin the receipt's mtime well into the past instead of racing git's 1-second
        # commit resolution - this test flaked roughly one run in five on timing alone.
        import os
        old = time.time() - 60
        os.utime(root / "receipts" / "r.md", (old, old))
        (root / "src.py").write_text("x = 2\n")        # real code moves on; the receipt does not
        out = run(root, msg)
        assert out.get("decision") == "block", f"stale receipt must not earn a new claim: {out}"
        assert "no receipt this session" in full(out)
        commit("src change")                           # and status going blind must not rescue it
        out = run(root, msg)
        assert out.get("decision") == "block", f"committed code must still age the receipt: {out}"

    with tempfile.TemporaryDirectory() as td:  # every stop is checked, up to the cap
        root = setup(td, UNIT)
        msg = "It works end to end in the browser."
        for i in range(MAX_BLOCKS_PER_PROMPT):
            out = run(root, msg, prompt_id="P1", stop_hook_active=bool(i))
            assert out.get("decision") == "block", f"stop {i} must still be checked: {out}"
        out = run(root, msg, prompt_id="P1", stop_hook_active=True)
        assert "decision" not in out, "cap reached -> the claim gets through"
        assert "UNPROVEN" in out["systemMessage"], "...but never silently"
        import json as _j
        events = [_j.loads(l)["event"] for l in core.log_path(root).read_text().splitlines()]
        assert events[-1] == "escaped", f"the escape must leave a row: {events}"
        assert run(root, msg, prompt_id="P2").get("decision") == "block", "new prompt, fresh budget"
        # with no prompt_id the coarse guard still applies
        assert run(root, msg, stop_hook_active=True) == {}

    long = ("Test stimulus, as requested (deliberately unearned - no receipt exists): "
            "it works end to end.")
    assert "works end to end" in excerpt(long, "works end to end"), excerpt(long, "works end to end")
    assert len(excerpt(long, "works end to end")) <= 82
    assert excerpt("It works end to end.", "works end to end") == "It works end to end."

    with tempfile.TemporaryDirectory() as td:  # the block names the one path it reads
        root = setup(td, UNIT)
        out = run(root, "It works end to end in the browser.", prompt_id="P9")
        assert "receipts/<feature>-<date>.md" in out["reason"]

    with tempfile.TemporaryDirectory() as td:  # no receipt at all
        root = setup(td, None)
        out = run(root, "Done and verified.")
        assert out.get("decision") == "block" and "no receipt this session" in full(out), out

    with tempfile.TemporaryDirectory() as td:  # a set-claim needs a row per member
        root = setup(td, UI)
        partition = ("## What shipped\n- cutting room floor \u00b7 clip download\n"
                     "- Refine with Oddie \u00b7 Free price tier\n\n## Not done\n- spending history\n")
        out = run(root, partition)
        assert out.get("decision") == "block", "partition claims completeness without saying 'all'"
        assert "Refine with Oddie" in full(out), full(out)
        assert "cutting room floor" in full(out)
        # the one item the receipt does speak to is not named as missing
        assert "unlock" not in full(out).split("No row speaks to:")[1]

        out = run(root, "Everything from your list is done.")
        assert out.get("decision") == "block", "bare universal, no enumerable items"

    with tempfile.TemporaryDirectory() as td:  # changed UI needs a screenshot, claim or not
        root = setup(td, UNIT)
        (root / "components").mkdir()
        (root / "components" / "Button.tsx").write_text("export const B = () => null\n")
        out = run(root, "Rewrote the button. Let me know what you think.")
        assert out.get("decision") == "block", f"UI changed with no screenshot: {out}"
        assert "Button.tsx" in full(out), full(out)

        # and a real screenshot on disk clears it
        (root / "receipts" / "r.md").write_text(RECEIPT.format(rows=UI, env="real Chrome"))
        (root / "receipts" / "r.md").touch()
        out = run(root, "Rewrote the button.")
        assert out == {}, f"a real screenshot clears it: {out}"

    with tempfile.TemporaryDirectory() as td:  # reporting back after real work needs a row, phrased any way
        root = setup(td, None)
        plain = "Swapped the loop for a set lookup in dedupe.py and updated the call site."
        out = run(root, plain, prompt_id="w1")
        assert out.get("decision") == "block", f"a claim-free report after code changes still needs proof: {out}"
        assert "work you did" in full(out)
        assert run(root, "Changed dedupe.py. Want me to update the docs too?", prompt_id="w2") == {}, "a question"
        assert run(root, "Still working: dedupe.py is half done, continuing with the call sites.",
                   prompt_id="w3") == {}, "in progress"
        (root / "receipts").mkdir(exist_ok=True)
        (root / "receipts" / "r.md").write_text(RECEIPT.format(rows=UNIT, env="local"))
        assert run(root, plain, prompt_id="w4") == {}, "a fresh verified row earns a plain report"

    with tempfile.TemporaryDirectory() as td:  # old dirty files are not this session's work
        root = Path(td)
        sp.run(["git", "init", "-q", str(root)], check=True)
        (root / "app.py").write_text("x = 1\n")
        sp.run(["git", "-C", str(root), "add", "-A"], check=True)
        sp.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "b"],
               check=True, capture_output=True)
        import os as _os, time as _t
        (root / "app.py").write_text("x = 2\n")                          # last session's edit, uncommitted
        old = _t.time() - 600
        _os.utime(root / "app.py", (old, old))
        core.log({"event": "armed", "session_id": "new"}, root)            # a new session starts now
        report = "Here are this project's stats: 4 claims, 1 earned."
        assert decide({"last_assistant_message": report, "session_id": "new", "prompt_id": "n1"}, root) == {}, \
            "a dirty tree from before the session must not make this turn owe evidence"

    with tempfile.TemporaryDirectory() as td:  # the gate wants evidence, not paperwork
        root = setup(td, None)
        (root / "receipts" / "loose.md").write_text(
            "# notes\n**Tier:** dev\n\n| claim | method | artifact | status |\n|---|---|---|---|\n"
            "| script prints hi | unit | ran python3 app.py -> hi | verified |\n")
        out = run(root, "Added the comment and ran the script; it prints hi.", prompt_id="loose")
        assert out == {}, f"honest rows in a loosely formatted receipt earn a plain report: {out}"

    with tempfile.TemporaryDirectory() as td:  # pudding's own writes are not a code change
        root = Path(td)
        sp.run(["git", "init", "-q", str(root)], check=True)
        (root / "net.py").write_text("x = 1\n")
        sp.run(["git", "-C", str(root), "add", "-A"], check=True)
        sp.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "b"],
               check=True, capture_output=True)
        import os as _os, time as _t
        base = _t.time() - 120
        _os.utime(root / "net.py", (base, base))
        core.log({"event": "armed", "session_id": "q"}, root)       # session starts after the commit
        core.ensure_ignored(root)                                    # pudding edits .gitignore
        explain = "1. The request succeeds and resp.read() is returned immediately. Done."
        out = decide({"last_assistant_message": explain, "session_id": "q", "prompt_id": "q1"}, root)
        assert out == {}, f"a question answered with no code change must not be blocked: {out}"
        (root / "net.py").write_text("x = 2\n")                    # now real code moves
        out = decide({"last_assistant_message": explain, "session_id": "q", "prompt_id": "q2"}, root)
        assert out.get("decision") == "block", "after a real change, the same claim is gated"

    print("gate: ok")



if __name__ == "__main__":
    main()
