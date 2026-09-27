r"""Outcome benchmark runner: each (task, arm, repeat) runs `claude -p` in a fresh copy of the
task repo, then the task's hidden checker grades the real resulting state.

    python3 run.py --arms vanilla,prompt,nag,pudding --tasks all --repeats 2 --model sonnet \
        --parallel 3 --protocol-file /path/to/protocol.txt --out results/<timestamp>/

Arms:
  vanilla  nothing extra
  prompt   --append-system-prompt <contents of --protocol-file>
  nag      --plugin-dir evals/outcome/nag      (blocks once per turn, no evidence logic)
  pudding  --plugin-dir <pudding repo root>

This script does NOT label whether the final message claims completion; a separate grader
reads runs.jsonl for that. The checker must run under a python that has playwright
(--check-python), because five of the eight checkers drive a real browser.
"""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUDDING = HERE.parents[1]
NAG = HERE / "nag"
ARMS = ("vanilla", "prompt", "nag", "pudding")
RESULT_FIELDS = ("result", "num_turns", "duration_ms", "duration_api_ms", "total_cost_usd",
                 "usage", "modelUsage", "session_id", "is_error", "subtype", "stop_reason")
GIT_ID = ["-c", "user.name=eval", "-c", "user.email=eval@localhost", "-c", "core.hooksPath=/dev/null"]


def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, **kw)


def clean_env(tmp):
    """A child session must not inherit the parent CLI session's identity.
    TMPDIR is per run so tempfile users cannot see a parallel run's files."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env["TMPDIR"] = str(tmp)
    return env


def arm_args(arm, protocol_text):
    if arm == "prompt":
        return ["--append-system-prompt", protocol_text]
    if arm == "nag":
        return ["--plugin-dir", str(NAG)]
    if arm == "pudding":
        return ["--plugin-dir", str(PUDDING)]
    return []


def prepare(task):
    work = Path(tempfile.mkdtemp(prefix="pudding-eval-%s-" % task.name)).resolve() / "repo"
    shutil.copytree(task / "repo", work)
    sh(["git", "init", "-q"], work, check=True)
    sh(["git", "add", "-A"], work, check=True)
    sh(["git", *GIT_ID, "commit", "-qm", "baseline"], work, check=True)
    return work, sh(["git", "rev-parse", "HEAD"], work).stdout.strip()


def run_claude(cmd, work, timeout):
    """Returns (stdout, stderr, exit_code, timed_out, wall_seconds). Kills the whole process
    group afterwards so servers the agent left running cannot leak into the next run."""
    t0 = time.time()
    tmp = work.parent / "tmp"
    tmp.mkdir(exist_ok=True)
    p = subprocess.Popen(cmd, cwd=str(work), env=clean_env(tmp), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, start_new_session=True)
    timed_out = False
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    return out, err, p.returncode, timed_out, round(time.time() - t0, 1)


def capture_diff(work, base, dest):
    """Stage everything (index only, temp repo) and diff against the baseline commit - by sha,
    not HEAD, so commits the agent made itself are still in the diff."""
    sh(["git", "add", "-A"], work)
    (dest / "diff.patch").write_text(sh(["git", "diff", "--cached", "--binary", base], work).stdout)
    status = sh(["git", "diff", "--cached", "--name-status", base], work).stdout.splitlines()
    changed = [line.split("\t", 1) for line in status if "\t" in line]
    created = [f for s, f in changed if s == "A"]
    return [{"status": s, "path": f} for s, f in changed], created


def copy_pudding_state(work, dest):
    """pudding writes .claude/pudding.local.* and receipts/ in the project. Copy whatever exists."""
    got = []
    for rel in (".claude/pudding.local.jsonl", ".claude/pudding.local.md", "receipts"):
        src = work / rel
        if src.exists():
            target = dest / "pudding" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, target)
            got.append(rel)
    return got


def copy_transcript(session_id, work, dest):
    """Transcripts live at ~/.claude/projects/<encoded cwd>/<session-id>.jsonl, where the
    encoded cwd is the real path with every non-alphanumeric char replaced by '-'. We pin the
    session id with --session-id, so we can glob for it rather than trust the encoding."""
    projects = Path.home() / ".claude" / "projects"
    expected_dir = "".join(ch if ch.isalnum() else "-" for ch in str(work))
    hits = sorted(projects.glob("*/%s.jsonl" % session_id)) if session_id else []
    info = {"transcript": None, "transcript_expected_dir": expected_dir, "transcript_dir_matches": None}
    if hits:
        src = hits[0]
        shutil.copy2(src, dest / "transcript.jsonl")
        sub = src.with_suffix("")  # <session-id>/ holds subagent transcripts, if any
        if sub.is_dir():
            shutil.copytree(sub, dest / "transcript_extra")
        info.update(transcript=str(dest / "transcript.jsonl"), transcript_source=str(src),
                    transcript_dir_matches=src.parent.name == expected_dir)
    return info


def run_checker(py, task, work, dest):
    try:
        p = sh([py, str(task / "check.py"), str(work)], HERE, timeout=300)
    except subprocess.TimeoutExpired:
        return {"pass": None, "details": "checker timed out after 300s", "subchecks": {}}
    (dest / "check.stdout").write_text(p.stdout + "\n--- stderr ---\n" + p.stderr)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"pass": None, "details": "checker crashed: %s" % p.stderr.strip()[-400:], "subchecks": {}}


def one_run(job, cfg):
    task, arm, rep = job
    run_id = "%s__%s__r%d" % (task.name, arm, rep)
    dest = cfg["out"] / "runs" / run_id
    dest.mkdir(parents=True, exist_ok=True)
    work, base = prepare(task)
    session_id = str(uuid.uuid4())
    prompt = (task / "prompt.md").read_text().strip()
    cmd = (["claude", "-p", prompt, "--model", cfg["model"], "--dangerously-skip-permissions",
            "--output-format", "json", "--session-id", session_id]
           + arm_args(arm, cfg["protocol_text"]) + cfg["extra_args"])
    out, err, code, timed_out, wall = run_claude(cmd, work, cfg["timeout"])
    (dest / "claude.stdout.json").write_text(out)
    (dest / "claude.stderr.txt").write_text(err)
    try:
        res = json.loads(out)
    except ValueError:
        res = {}
    files_changed, created = capture_diff(work, base, dest)
    row = {
        "run_id": run_id, "task": task.name, "arm": arm, "repeat": rep, "model": cfg["model"],
        "model_resolved": sorted((res.get("modelUsage") or {}).keys()),
        "claude_version": cfg["claude_version"], "workdir": str(work), "cmd": [("<protocol-file>" if x == cfg["protocol_text"] and x else x) for x in cmd[:1] + ["-p", "<prompt.md>"] + cmd[3:]],
        "exit_code": code, "timed_out": timed_out, "wall_s": wall,
        "claude_json_parsed": bool(res), "final_message": res.get("result"),
        **{k: res.get(k) for k in RESULT_FIELDS if k != "result"},
        "session_id_requested": session_id,
        "files_changed": files_changed, "files_created": created,
        "pudding_state": copy_pudding_state(work, dest),
        **copy_transcript(res.get("session_id") or session_id, work, dest),
    }
    row["check"] = run_checker(cfg["check_python"], task, work, dest)
    row["paths"] = {k: str(dest / f) for k, f in (("dir", ""), ("claude_json", "claude.stdout.json"),
                    ("stderr", "claude.stderr.txt"), ("diff", "diff.patch"), ("check", "check.stdout"))}
    return row


def summarize(rows, out):
    lines = ["# Outcome run summary", "", "| task | arm | runs | checker pass | timeouts | mean turns | mean cost $ | mean wall s |",
             "|---|---|---|---|---|---|---|---|"]
    groups = {}
    for r in rows:
        groups.setdefault((r["task"], r["arm"]), []).append(r)

    def mean(xs):
        xs = [x for x in xs if isinstance(x, (int, float))]
        return "%.2f" % (sum(xs) / len(xs)) if xs else "-"
    for (t, a), rs in sorted(groups.items()):
        lines.append("| %s | %s | %d | %d | %d | %s | %s | %s |" % (
            t, a, len(rs), sum(r["check"].get("pass") is True for r in rs), sum(r["timed_out"] for r in rs),
            mean(r.get("num_turns") for r in rs), mean(r.get("total_cost_usd") for r in rs), mean(r["wall_s"] for r in rs)))
    lines += ["", "## Runs", "", "| run | checker | details | transcript | final message (first 160 chars) |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["run_id"]):
        msg = (r.get("final_message") or "").replace("\n", " ").replace("|", "/")[:160]
        det = str(r["check"].get("details", "")).replace("|", "/")[:160]
        lines.append("| %s | %s | %s | %s | %s |" % (r["run_id"], r["check"].get("pass"), det,
                                                     "yes" if r.get("transcript") else "MISSING", msg))
    (out / "summary.md").write_text("\n".join(lines) + "\n")


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--tasks", default="all")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--out", default=None, help="default: results/<timestamp>/ next to this file")
    ap.add_argument("--protocol-file", default=None, help="text appended as system prompt in the prompt arm")
    ap.add_argument("--timeout", type=int, default=900, help="per-run wall clock limit, seconds")
    ap.add_argument("--check-python", default=sys.executable, help="python with playwright, for checkers")
    ap.add_argument("--extra-args", default="", help="extra claude CLI args for every arm, shell-quoted")
    return ap.parse_args()


def main():
    a = parse_args()
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    bad = [x for x in arms if x not in ARMS]
    if bad:
        sys.exit("unknown arm(s): %s (valid: %s)" % (bad, ", ".join(ARMS)))
    all_tasks = sorted(p for p in (HERE / "tasks").iterdir() if (p / "check.py").exists())
    tasks = all_tasks if a.tasks == "all" else [HERE / "tasks" / t.strip() for t in a.tasks.split(",")]
    for t in tasks:
        if not (t / "check.py").exists():
            sys.exit("no such task: %s" % t.name)
    protocol_text = ""
    if "prompt" in arms:
        if not a.protocol_file:
            sys.exit("--protocol-file is required for the prompt arm")
        protocol_text = Path(a.protocol_file).read_text()
    if "nag" in arms and not NAG.is_dir():
        sys.exit("nag arm needs the plugin at %s" % NAG)
    probe = sh([a.check_python, "-c", "import playwright"], HERE)
    if probe.returncode != 0:
        sys.exit("--check-python %s cannot import playwright; browser checkers would not run" % a.check_python)
    out = Path(a.out) if a.out else HERE / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out = out if out.is_absolute() else (Path.cwd() / out)
    out.mkdir(parents=True, exist_ok=True)
    version = sh(["claude", "--version"], HERE).stdout.strip()
    cfg = {"out": out, "model": a.model, "timeout": a.timeout, "check_python": a.check_python,
           "extra_args": shlex.split(a.extra_args), "protocol_text": protocol_text, "claude_version": version}
    manifest = {"started": datetime.now().isoformat(), "argv": sys.argv, "claude_version": version,
                "arms": arms, "tasks": [t.name for t in tasks], "repeats": a.repeats, "model": a.model,
                "protocol_file": a.protocol_file,
                "protocol_sha256": hashlib.sha256(protocol_text.encode()).hexdigest() if protocol_text else None,
                "pudding_rev": sh(["git", "rev-parse", "HEAD"], PUDDING).stdout.strip(),
                # the pudding arm loads the working tree, not HEAD: record uncommitted edits
                "pudding_dirty": sh(["git", "status", "--porcelain", "--", "hooks", "skills", ".claude-plugin"],
                                    PUDDING).stdout.splitlines(),
                "check_python": a.check_python, "extra_args": cfg["extra_args"]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # arm-major order: jobs running at the same time are different tasks, so agents that
    # hardcode /tmp paths or ports (seen: http.server 8934) rarely collide with a twin run.
    jobs = [(t, arm, r) for r in range(1, a.repeats + 1) for arm in arms for t in tasks]
    rows, lock = [], threading.Lock()

    def work(job):
        try:
            row = one_run(job, cfg)
        except Exception as e:  # a harness bug in one run must not lose the others
            row = {"run_id": "%s__%s__r%d" % (job[0].name, job[1], job[2]), "task": job[0].name,
                   "arm": job[1], "repeat": job[2], "harness_error": repr(e), "timed_out": False,
                   "wall_s": None, "check": {"pass": None, "details": "harness error"}}
        with lock:
            rows.append(row)
            with (out / "runs.jsonl").open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print("[%d/%d] %s check=%s timeout=%s" % (len(rows), len(jobs), row["run_id"],
                  row["check"].get("pass"), row["timed_out"]), flush=True)

    with ThreadPoolExecutor(max_workers=a.parallel) as ex:
        list(ex.map(work, jobs))
    summarize(rows, out)
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
