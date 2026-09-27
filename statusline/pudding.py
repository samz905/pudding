#!/usr/bin/env python3
"""pudding statusline: how many claims earned themselves, how many did not.

    python3 pudding.py           ->  pudding 12/3
    python3 pudding.py --stats   ->  the fuller breakdown

Reads .claude/pudding.local.jsonl in the current project. Prints nothing when the
log is missing, so an unarmed project shows a clean statusline.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path


def counts(root: Path) -> Counter:
    c = Counter()
    try:
        for line in (root / ".claude" / "pudding.local.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                c[json.loads(line).get("event", "?")] += 1
            except Exception:
                continue
    except Exception:
        pass
    return c


def project_root():
    """Claude Code pipes {"workspace": {"project_dir": ...}} to a statusline."""
    try:
        if not sys.stdin.isatty():
            data = json.loads(sys.stdin.read() or "{}")
            ws = data.get("workspace") or {}
            d = ws.get("project_dir") or ws.get("current_dir") or data.get("cwd")
            if d:
                return Path(d)
    except Exception:
        pass
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def main():
    root = project_root()
    c = counts(root)
    earned, blocked, unearned, escaped = c["earned"], c["blocked"], c["unearned"], c["escaped"]

    if "--stats" in sys.argv:
        # Decisions, not claims: one claim can be blocked, then earned on the retry.
        total = earned + blocked + unearned + escaped
        if not total:
            print("pudding: no decisions recorded yet in this project.")
            return
        first_try = earned
        print(f"\U0001F36E pudding stats - {root.name}")
        print()
        print(f"  turns that ended on a claim     {total}")
        print(f"    had matching evidence         {earned}")
        print(f"    blocked for missing evidence  {blocked}")
        print(f"    let through in warn mode      {unearned}")
        print(f"    escaped after 3 blocks        {escaped}")
        print()
        print(f"  {100 * first_try // total}% of those turns carried matching evidence.")
        print(f"  sessions armed: {c['armed']}   mode changes you made: {c['mode']}")
        return

    if earned or blocked or unearned:
        sys.stdout.write(f"\U0001F36E {earned}✓ {blocked + unearned}✗")


def demo():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        assert counts(root) == Counter(), "missing log is silent, not an error"
        d = root / ".claude"
        d.mkdir()
        (d / "pudding.local.jsonl").write_text(
            '{"event":"earned"}\n{"event":"blocked"}\n{"event":"earned"}\nnot json\n')
        c = counts(root)
        assert c["earned"] == 2 and c["blocked"] == 1, c
    print("statusline: ok")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
