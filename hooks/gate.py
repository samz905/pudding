#!/usr/bin/env python3
"""Stop / SubagentStop: a completion claim does not leave the turn without matching evidence.

The whole point is that this is not a skill. A skill has to be chosen, and the
agent that would skip proving is the agent that skips the skill - measured on one
machine: 380 done-claims, 1 verification-skill invocation, and the pudding skill
itself never once. So the harness runs this, not the agent's goodwill.

Cheap by design: a message with no claim in it costs one regex sweep and exits.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "skills" / "pudding" / "scripts"))

import pudding_core as core          # noqa: E402
from claims import detect            # noqa: E402
from pudding_check import parse_rows, env_of, check, PAIR_WORDS  # noqa: E402

LOCAL_ENV = re.compile(r"localhost|127\.0\.0\.1|0\.0\.0\.0|file://|\blocal(?:host)?\b", re.I)
# ponytail: receipts older than this are ignored when the session start is unknown.
STALE_SECONDS = 6 * 3600


def session_start(session_id, root):
    """When this session armed. Falls back to a window, so a missing log never
    turns stale evidence into fresh evidence."""
    try:
        for line in reversed(core.log_path(root).read_text(encoding="utf-8").splitlines()):
            e = json.loads(line)
            if e.get("event") == "armed" and e.get("session_id") == session_id:
                # fromisoformat keeps the offset; time.mktime would read UTC as local
                # and put session start hours in the future, so nothing is ever fresh.
                return datetime.fromisoformat(e["ts"]).timestamp()
    except Exception:
        pass
    return time.time() - STALE_SECONDS


def source_changed(root, since):
    """Did this session touch code? Talking about work is not claiming it."""
    try:
        st = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                            capture_output=True, text=True, timeout=3)
        if st.returncode == 0 and st.stdout.strip():
            return True
        ct = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%ct"],
                            capture_output=True, text=True, timeout=3)
        if ct.returncode == 0 and ct.stdout.strip():
            return int(ct.stdout.strip()) >= since
    except Exception:
        pass
    return True  # never let a git failure quietly disarm the gate


def fresh_receipt(root, since):
    try:
        cands = [p for p in (root / "receipts").glob("*.md") if p.stat().st_mtime >= since]
    except Exception:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def verified_rows(text):
    return [r for r in parse_rows(text) if r[3].lower().startswith("verified")]


def satisfies(fam, rows, env):
    """Does any verified row earn this claim? The gate table, mechanically."""
    for claim, method, artifact, _ in rows:
        if fam.methods is not None and method not in fam.methods:
            continue
        if fam.pair and not PAIR_WORDS.search(artifact + " " + claim):
            continue
        if fam.deployed and (LOCAL_ENV.search(env) or not env.strip()):
            continue
        return True
    return False


def have_summary(rows):
    if not rows:
        return "no verified rows"
    counts = {}
    for _, method, _, _ in rows:
        counts[method] = counts.get(method, 0) + 1
    return ", ".join(f"{n} {m}" for m, n in sorted(counts.items(), key=lambda kv: -kv[1]))


def render(unmet, receipt, rows):
    """stopReason is read by a human; reason is read by the model."""
    c = unmet[0]
    said = c.sentence if len(c.sentence) <= 76 else c.sentence[:73] + "..."
    have = have_summary(rows)
    where = str(receipt.name) if receipt else "no receipt written this session"

    stop_reason = (
        "\n\U0001F36E  no pudding, no done.\n\n"
        f"  you said     {said}\n"
        f"  you have     {have}\n"
        f"  you need     {c.family.hint}\n\n"
        "  go look at it. then come back.\n"
        "  (or write it down honestly:\n"
        f"   | {c.phrase} | - | - | blocked: <why> |)\n"
    )

    lines = [
        "pudding blocked this turn: a completion claim with no matching evidence.",
        "",
        f"receipt: {where}",
        "",
    ]
    for c in unmet:
        lines += [f'claim   "{c.sentence.strip()}"',
                  f"family  {c.family.name}",
                  f"needs   {c.family.hint}",
                  ""]
    lines += [
        "Do one of these, then say it again:",
        "  1. Go get the evidence, drive it the way the user does, and add the row.",
        "  2. If you cannot reach it, record that honestly as a row with",
        "     status `blocked: <why - user decision needed>` and say so in your report.",
        "  3. If the user already waived it, record `waived: <who/when>`.",
        "",
        "Do not restate the claim without doing one of those. A softer sentence with",
        "the same unearned meaning is the failure this exists to catch.",
    ]
    return stop_reason, "\n".join(lines)


def decide(data, root):
    """The whole verdict, as a pure function of the hook input and the repo. Returns
    the JSON payload to print ({} means: let the turn end)."""
    if data.get("stop_hook_active"):
        return {}  # one block per claim; never fight the harness cap

    claims = detect(data.get("last_assistant_message") or "")
    if not claims:
        return {}  # the common case, and it costs one regex sweep

    session_id = data.get("session_id", "")
    since = session_start(session_id, root)
    if not source_changed(root, since):
        return {}

    mode, authorized, _ = core.read_mode(root)
    if mode == "off":
        return {}

    receipt = fresh_receipt(root, since)
    text = receipt.read_text(encoding="utf-8-sig") if receipt else ""
    rows, env = verified_rows(text), env_of(text)
    findings = check(receipt) if receipt else ["no receipt written this session"]
    receipt_ok = bool(receipt) and not findings

    unmet = [c for c in claims if not (receipt_ok and satisfies(c.family, rows, env))]
    base = {"session_id": session_id, "event_kind": data.get("hook_event_name", "Stop"),
            "claims": [c.family.name for c in claims],
            "receipt": receipt.name if receipt else None, "mode": mode}

    if not unmet:
        core.log({"event": "earned", **base}, root)
        return {}

    stop_reason, reason = render(unmet, receipt, rows)
    if receipt and findings:
        reason += "\n\nThe receipt is also invalid:\n" + "\n".join(f"  - {f}" for f in findings)

    if mode == "warn":
        core.log({"event": "unearned", **base}, root)
        return {"systemMessage": stop_reason}

    core.log({"event": "blocked", **base}, root)
    out = {"decision": "block", "reason": reason, "stopReason": stop_reason}
    if not authorized:
        out["systemMessage"] = ("pudding: the project mode file was weakened without a /pudding "
                                "command, so the gate reverted to block.")
    return out


def main():
    core.emit(decide(core.read_hook_input(), core.project_dir()))


def demo():
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
    UI = "| unlock works for a real user | real-ui | shots/a.png before->after | verified |"

    def setup(td, rows, env="real Chrome, macOS"):
        root = Path(td)
        (root / "receipts").mkdir(parents=True, exist_ok=True)
        sp.run(["git", "init", "-q", str(root)], check=True)
        (root / "src.py").write_text("x = 1\n")  # dirty tree == source changed
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
        assert "real-ui" in out["reason"] and "no pudding" in out["stopReason"]
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

    with tempfile.TemporaryDirectory() as td:  # no receipt at all
        root = setup(td, None)
        out = run(root, "Done and verified.")
        assert out.get("decision") == "block" and "no receipt" in out["reason"], out

    print("gate: ok")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
