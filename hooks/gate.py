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

# Runtime artifacts, not the code a claim is about. Without this, a background
# writer (x-account's batch touches pipeline.db-wal every 10 minutes) ages out
# every receipt for reasons unrelated to the work being claimed.
VOLATILE = re.compile(r"\.(?:db|db-shm|db-wal|sqlite3?|log|jsonl|lock|pyc|pid|tmp)$", re.I)

LOCAL_ENV = re.compile(r"localhost|127\.0\.0\.1|0\.0\.0\.0|file://|\blocal(?:host)?\b", re.I)
# ponytail: receipts older than this are ignored when the session start is unknown.
STALE_SECONDS = 6 * 3600
# Blocks allowed per user prompt. The harness force-ends at 8 and prints a warning
# naming the hook, so stay well under it - but bailing on stop_hook_active alone
# (the first design) let every stop after the first one through unchecked.
MAX_BLOCKS_PER_PROMPT = 3


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


def blocks_this_prompt(prompt_id, root):
    """How many times this same user prompt has already been blocked."""
    if not prompt_id:
        return 0
    n = 0
    try:
        for line in core.log_path(root).read_text(encoding="utf-8").splitlines()[-300:]:
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event") == "blocked" and e.get("prompt_id") == prompt_id:
                n += 1
    except Exception:
        pass
    return n


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


def newest_source_mtime(root):
    """When the code last changed. Evidence written before the code it describes is
    evidence for different work - the first live session accepted a four-minute-old
    receipt about run.sh as proof for a claim about tunnel.sh.

    ponytail: reads only files git already reports as dirty, so ignored build output
    and data churn cannot age a receipt out. A background writer committing tracked
    files mid-session can still do it; per-path exclusions if that bites.
    """
    newest = 0.0
    try:
        out = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=3)
        for line in out.stdout.splitlines():
            rel = line[3:].strip().strip('"').split(" -> ")[-1]
            if rel.startswith(("receipts/", ".claude/")) or VOLATILE.search(rel):
                continue
            try:
                newest = max(newest, (root / rel).stat().st_mtime)
            except OSError:
                continue
    except Exception:
        pass
    return max(newest, newest_source_commit(root, newest))


def newest_source_commit(root, floor):
    """When code was last COMMITTED. x-account's batch commits the agent's edits
    within ten minutes, so a status-only check goes blind the moment it runs.

    Only commits touching non-volatile paths count, so the same batch writing
    data/pipeline.db every tick does not age a receipt out on its own cadence.
    """
    newest, ts = 0.0, 0.0
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "--since=@%d" % int(floor or 0),
             "--format=%ct", "--name-only"],
            capture_output=True, text=True, timeout=5)
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.isdigit():
                ts = float(line)
            elif not (line.startswith(("receipts/", ".claude/")) or VOLATILE.search(line)):
                newest = max(newest, ts)
    except Exception:
        pass
    return newest


def fresh_receipt(root, since):
    """The newest receipt that is both from this session and not older than the code."""
    floor = max(since, newest_source_mtime(root))
    try:
        cands = [p for p in (root / "receipts").glob("*.md") if p.stat().st_mtime >= floor]
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


def render(unmet, receipt, rows, root):
    """stopReason is read by a human; reason is read by the model."""
    c = unmet[0]
    said = c.sentence if len(c.sentence) <= 76 else c.sentence[:73] + "..."
    have = have_summary(rows)
    where = str(receipt) if receipt else "none written this session"

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
        f"receipt read: {where}",
        f"receipts are read from exactly one place: {root / 'receipts'}/",
        "a receipts/ folder anywhere else in the tree is not read.",
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
    prompt_id = data.get("prompt_id") or ""
    spent = blocks_this_prompt(prompt_id, root)
    if spent >= MAX_BLOCKS_PER_PROMPT:
        return {}  # said our piece; never fight the harness cap
    if not prompt_id and data.get("stop_hook_active"):
        return {}  # no prompt_id to count against, so fall back to the coarse guard

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
    base = {"session_id": session_id, "prompt_id": prompt_id,
            "event_kind": data.get("hook_event_name", "Stop"),
            "claims": [c.family.name for c in claims],
            "receipt": receipt.name if receipt else None, "mode": mode}

    if not unmet:
        core.log({"event": "earned", **base}, root)
        return {}

    stop_reason, reason = render(unmet, receipt, rows, root)
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

        time.sleep(1.1)                                # git commit time has 1s resolution
        (root / "src.py").write_text("x = 2\n")        # real code moves on; the receipt does not
        out = run(root, msg)
        assert out.get("decision") == "block", f"stale receipt must not earn a new claim: {out}"
        assert "none written this session" in out["reason"]
        commit("src change")                           # and status going blind must not rescue it
        out = run(root, msg)
        assert out.get("decision") == "block", f"committed code must still age the receipt: {out}"

    with tempfile.TemporaryDirectory() as td:  # every stop is checked, up to the cap
        root = setup(td, UNIT)
        msg = "It works end to end in the browser."
        for i in range(MAX_BLOCKS_PER_PROMPT):
            out = run(root, msg, prompt_id="P1", stop_hook_active=bool(i))
            assert out.get("decision") == "block", f"stop {i} must still be checked: {out}"
        assert run(root, msg, prompt_id="P1", stop_hook_active=True) == {}, "cap reached -> yield"
        assert run(root, msg, prompt_id="P2").get("decision") == "block", "new prompt, fresh budget"
        # with no prompt_id the coarse guard still applies
        assert run(root, msg, stop_hook_active=True) == {}

    with tempfile.TemporaryDirectory() as td:  # the block names the one path it reads
        root = setup(td, UNIT)
        out = run(root, "It works end to end in the browser.", prompt_id="P9")
        assert "receipts are read from exactly one place" in out["reason"], out["reason"]
        assert str(root) in out["reason"]

    with tempfile.TemporaryDirectory() as td:  # no receipt at all
        root = setup(td, None)
        out = run(root, "Done and verified.")
        assert out.get("decision") == "block" and "none written this session" in out["reason"], out

    print("gate: ok")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
