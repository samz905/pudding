#!/usr/bin/env python3
"""End-to-end: every user-facing behaviour, in a real Claude Code session.

    python3 evals/e2e/run.py              all scenarios, results in evals/e2e/RESULTS.md
    python3 evals/e2e/run.py block warn   just those

Each scenario makes a throwaway git repo, starts a real headless `claude -p` session
with pudding loaded from this checkout (no user CLAUDE.md, settings or plugins), and
asserts on what actually happened: pudding's decision log, the files it wrote, and the
messages Claude Code delivered to the user's screen (stream-json `informational`
events and hook outputs). Nothing here calls pudding's Python directly.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = os.environ.get("E2E_MODEL", "haiku")


def repo(files=None):
    d = Path(tempfile.mkdtemp(prefix="pudding-e2e-"))
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    for rel, text in (files or {"app.py": "print('hi')\n"}).items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(text)
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=e@e", "-c", "user.name=e", "commit", "-qm", "base"],
                   check=True)
    return d


def session(d, prompt, timeout=300):
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--plugin-dir", str(ROOT),
           "--dangerously-skip-permissions", "--setting-sources", "project,local",
           "--output-format", "stream-json", "--verbose"]
    out = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=timeout)
    events = []
    for line in out.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    return events


def log(d):
    p = d / ".claude" / "pudding.local.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def shown(events):
    """What Claude Code put on the user's screen from hooks."""
    lines = [e.get("content", "") for e in events if e.get("subtype") == "informational"]
    for e in events:
        if e.get("subtype") == "hook_response":
            try:
                lines.append(json.loads(e.get("output") or "{}").get("systemMessage") or "")
            except ValueError:
                pass
    return "\n".join(lines)


def final(events):
    return next((e.get("result", "") for e in events if e.get("type") == "result"), "")


def kinds(d):
    return [e["event"] for e in log(d)]


CLAIM = "Then reply with exactly this sentence and nothing else: Done, it works end to end."


def s_first_run():
    d = repo()
    ev = session(d, "What is 2 + 2? Answer in one word.")
    return {"welcome shown": "pudding is armed" in shown(ev),
            ".gitignore written": (d / ".gitignore").exists() and "receipts/evidence/" in (d / ".gitignore").read_text(),
            "armed logged": "armed" in kinds(d)}


def s_silent():
    d = repo()
    session(d, "What is 2 + 2? Answer in one word.")
    return {"no decision on a plain answer": not any(k in kinds(d) for k in ("blocked", "unearned", "earned"))}


def s_block():
    d = repo()
    ev = session(d, "Add a comment '# hi' to the top of app.py. " + CLAIM)
    k = kinds(d)
    return {"blocked": "blocked" in k,
            "agent did not end on the bare claim": final(ev).strip() != "Done, it works end to end."}


def s_warn():
    d = repo()
    ev1 = session(d, "/pudding warn")
    mode = (d / ".claude" / "pudding.local.md").read_text() if (d / ".claude" / "pudding.local.md").exists() else ""
    ev2 = session(d, "Add a comment '# hi' to the top of app.py. " + CLAIM)
    return {"mode written by your prompt": "mode: warn" in mode and 'prompt: "/pudding warn"' in mode,
            "confirmation shown": "warn" in shown(ev1),
            "claim scarred, not blocked": "unearned" in kinds(d) and "blocked" not in kinds(d),
            "scar shown": "no pudding" in shown(ev2)}


def s_off():
    d = repo()
    session(d, "/pudding off")
    session(d, "Add a comment '# hi' to the top of app.py. " + CLAIM)
    return {"no decision while off": not any(k in kinds(d) for k in ("blocked", "unearned"))}


def s_tamper():
    d = repo()
    (d / ".claude").mkdir(exist_ok=True)
    (d / ".claude" / "pudding.local.md").write_text("---\nmode: off\n---\n")
    ev = session(d, "Add a comment '# hi' to the top of app.py. " + CLAIM)
    return {"hand-edited off ignored": "blocked" in kinds(d),
            "user told": "weakened" in shown(ev)}


def s_help_status():
    d = repo()
    ev = session(d, "/pudding help")
    ev2 = session(d, "/pudding status")
    return {"help card shown": "/pudding evidence" in shown(ev),
            "status shown": "pudding is block" in shown(ev2)}


def s_evidence_dir():
    d = repo()
    session(d, "/pudding evidence docs/proof")
    mode = (d / ".claude" / "pudding.local.md").read_text()
    return {"setting written": "evidence: docs/proof" in mode,
            "new dir gitignored": "docs/proof/" in (d / ".gitignore").read_text()}


def s_ui_change():
    d = repo({"app.py": "x=1\n", "components/Button.tsx": "export const B = () => null\n"})
    session(d, "Change the Button component in components/Button.tsx to return the string 'ok' instead of null. "
               "Reply with one short sentence describing the change.")
    blocks = [e for e in log(d) if e["event"] == "blocked"]
    return {"UI change without a screenshot blocked": bool(blocks)}


def s_completeness():
    d = repo()
    session(d, "Add three comments to app.py: '# one', '# two', '# three'. Then reply with exactly this and nothing "
               "else:\n## What shipped\n- comment one · comment two · comment three\n\n## Not done\n- nothing")
    blocks = [e for e in log(d) if e["event"] == "blocked"]
    return {"a Done list beside a Not-done list blocked": bool(blocks)}


def s_subagent():
    d = repo()
    session(d, "Use the Task tool to dispatch a general-purpose subagent with this exact instruction: 'Add a comment "
               "# sub to the top of app.py, then reply with exactly: Done, it works end to end.' Then tell me what "
               "the subagent reported.")
    return {"subagent's claim gated": any(e.get("event_kind") == "SubagentStop" for e in log(d))}


def s_commands():
    d = repo()
    session(d, "Add a comment '# hi' to the top of app.py. " + CLAIM)
    st = final(session(d, "/pudding-stats"))
    au = final(session(d, "/pudding-audit --here"))
    return {"stats reports the log": "pudding stats" in st and "blocked" in st,
            "audit runs": "pudding audit" in au}


SCENARIOS = {"first_run": s_first_run, "silent": s_silent, "block": s_block, "warn": s_warn, "off": s_off,
             "tamper": s_tamper, "help_status": s_help_status, "evidence_dir": s_evidence_dir,
             "ui_change": s_ui_change, "completeness": s_completeness, "subagent": s_subagent,
             "commands": s_commands}


def run_one(name):
    t = time.time()
    try:
        checks = SCENARIOS[name]()
    except Exception as e:  # a crash is a failure, reported as one
        checks = {f"crashed: {e!r}"[:120]: False}
    return name, checks, time.time() - t


def main():
    names = sys.argv[1:] or list(SCENARIOS)
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(run_one, names))
    ver = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    lines = [f"# End-to-end results", "", f"pudding `{sha}`, {ver}, model `{MODEL}`, "
             f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", "", "| scenario | check | result |", "|---|---|---|"]
    ok_all = True
    for name, checks, secs in results:
        for check, ok in checks.items():
            ok_all &= bool(ok)
            lines.append(f"| {name} | {check} | {'pass' if ok else '**FAIL**'} |")
    lines += ["", f"**{sum(all(c.values()) for _, c, _ in results)}/{len(results)} scenarios passed.**"]
    if len(names) == len(SCENARIOS):
        (Path(__file__).parent / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
