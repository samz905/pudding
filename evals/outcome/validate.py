"""Validate every task's checker three ways: unmodified repo (must FAIL), repo + solution/
(must PASS), repo + wrong_fix/ (must FAIL). solution/ and wrong_fix/ are overlays: their
files are copied on top of a fresh copy of repo/. A task with no solution/ is one where the
untouched repo IS the correct outcome (control-question), so there it must PASS.

Usage: python3 validate.py [--python /path/to/python] [task ...]
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECT = {"unmodified": False, "solution": True, "wrong_fix": False}


def stage(task: Path, overlay: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix="pudding-validate-")) / "repo"
    shutil.copytree(task / "repo", d)
    if overlay != "unmodified":
        shutil.copytree(task / overlay, d, dirs_exist_ok=True)
    return d


def run_check(py: str, task: Path, d: Path) -> dict:
    p = subprocess.run([py, str(task / "check.py"), str(d)], capture_output=True, text=True, timeout=180)
    line = (p.stdout.strip().splitlines() or [""])[-1]
    try:
        out = json.loads(line)
    except ValueError:
        out = {"pass": None, "details": "unparseable: %s %s" % (p.stdout[-300:], p.stderr[-300:])}
    out["exit"] = p.returncode
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("tasks", nargs="*")
    a = ap.parse_args()
    tasks = [HERE / "tasks" / t for t in a.tasks] or sorted(p for p in (HERE / "tasks").iterdir() if p.is_dir())
    bad = 0
    for task in tasks:
        expect = dict(EXPECT, unmodified=not (task / "solution").is_dir())
        for overlay, want in expect.items():
            if overlay != "unmodified" and not (task / overlay).is_dir():
                print("%s %s: SKIP (no %s/)" % (task.name, overlay, overlay))
                continue
            d = stage(task, overlay)
            out = run_check(a.python, task, d)
            ok = out.get("pass") is want and out["exit"] == (0 if want else 1)
            bad += not ok
            print("%-20s %-10s expect=%-5s got=%-5s exit=%d %s  %s" % (
                task.name, overlay, want, out.get("pass"), out["exit"], "OK " if ok else "BAD",
                json.dumps({"details": out.get("details"), "subchecks": out.get("subchecks")})))
            shutil.rmtree(d.parent, ignore_errors=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
