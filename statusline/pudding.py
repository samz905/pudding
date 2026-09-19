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


def main():
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    c = counts(root)
    earned, blocked, unearned, escaped = c["earned"], c["blocked"], c["unearned"], c["escaped"]

    if "--stats" in sys.argv:
        total = earned + blocked + unearned + escaped
        if not total:
            print("pudding: no claims recorded yet in this project.")
            return
        print(f"claims made        {total}")
        print(f"  earned           {earned}")
        print(f"  blocked          {blocked}")
        print(f"  shipped unearned {unearned}   (mode was warn)")
        print(f"  escaped          {escaped}   (repeated past the block budget)")
        print(f"\n{100 * earned // total}% of done-claims carried matching evidence.")
        if c["mode"]:
            print(f"mode changed {c['mode']} time(s); sessions armed: {c['armed']}")
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
