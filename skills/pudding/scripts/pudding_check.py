#!/usr/bin/env python3
"""pudding_check: lint a receipt. Single file, stdlib only, optional by design.

    python pudding_check.py receipts/my-feature-2026-08-16.md
    python pudding_check.py --all          # every receipt under receipts/

Checks exactly the validity rules in RECEIPT-FORMAT.md:
  1. tier declared and one of: smoke | standard | exhaustive
  2. env declared, non-empty
  3. every `verified` row has a real artifact (not empty, not "-")
  4. method is one of: unit | api | db | wire | real-ui  (or "-" only when the row is
     blocked/waived)
  5. method matches claim kind for the automatable cases:
     "real user" / "end-to-end" / "e2e" / "in-app" claims need real-ui;
     "matches the design" / "likeness" claims need real-ui and a pair (vs/before/after)
  6. "## Not tested" section present
  7. "## Cleanup" section present and asserts a number (a count, not a vibe)

Exit 0 = valid. Exit 1 = the done-claim is not earned; findings listed.
"""
import re
import sys
from pathlib import Path

METHODS = {"unit", "api", "db", "wire", "real-ui"}
TIERS = {"smoke", "standard", "exhaustive"}
NEEDS_REAL_UI = re.compile(r"real user|end.to.end|\be2e\b|in.app", re.I)
NEEDS_PAIR = re.compile(r"matches the design|likeness|matches the mock", re.I)
PAIR_WORDS = re.compile(r"\bvs\b|before|after|reference|pair", re.I)


def parse_rows(text):
    """Every claim row in a receipt, as [claim, method, artifact, status].

    Shared with the pudding gate so the linter and the hook can never disagree
    about what a receipt says.
    """
    rows = []
    for line in text.splitlines():
        if line.strip().startswith("|") and line.count("|") >= 5:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and cells[0].lower() not in ("claim", "---", ""):
                if set(cells[0]) != {"-"}:
                    rows.append(cells[:4])
    return rows


def env_of(text):
    """The receipt's declared env, or '' - first-class because headless is not the user's Chrome."""
    m = re.search(r"^env:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def check(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    finds = []

    m = re.search(r"^tier:\s*(\S+)", text, re.M)
    if not m:
        finds.append("no tier declared")
    elif m.group(1).lower() not in TIERS:
        finds.append(f"tier '{m.group(1)}' not in {sorted(TIERS)}")

    m = re.search(r"^env:\s*(.+)$", text, re.M)
    if not m or not m.group(1).strip():
        finds.append("no env declared (where were artifacts captured?)")

    rows = parse_rows(text)
    if not rows:
        finds.append("no claim rows found")

    for claim, method, artifact, status in rows:
        s = status.lower()
        excused = s.startswith("blocked") or s.startswith("waived")
        if method not in METHODS and not (method in {"-", ""} and excused):
            finds.append(f"row '{claim[:40]}': method '{method}' invalid" +
                         (" (only blocked/waived rows may skip method)" if method in {"-", ""} else ""))
        if s == "verified":
            if artifact in {"", "-"}:
                finds.append(f"row '{claim[:40]}': verified with no artifact")
            if NEEDS_REAL_UI.search(claim) and method != "real-ui":
                finds.append(f"row '{claim[:40]}': claims real-user/e2e but method is '{method}' (needs real-ui)")
            if NEEDS_PAIR.search(claim):
                if method != "real-ui":
                    finds.append(f"row '{claim[:40]}': design-match claim needs real-ui")
                elif not PAIR_WORDS.search(artifact):
                    finds.append(f"row '{claim[:40]}': design-match needs a screenshot-vs-reference pair, artifact shows no pair")

    if not re.search(r"^##\s*Not tested", text, re.M):
        finds.append("no 'Not tested' section (the residue is mandatory)")
    cl = re.search(r"^##\s*Cleanup\s*\n(.*?)(?:\n##|\Z)", text, re.M | re.S)
    if not cl:
        finds.append("no 'Cleanup' section")
    elif not re.search(r"\d", cl.group(1)):
        finds.append("Cleanup asserts no number (count the leftovers, don't vibe them)")

    return finds


def demo():
    import tempfile
    good = """# Receipt: thing (2026-09-17)
tier: smoke
env: real Chrome, macOS

| claim | method | artifact | status |
|---|---|---|---|
| unlock deducts 20 points | db | wallet 20 -> 0 | verified |
| unlock works end to end for a real user | real-ui | shots/unlock.png before->after | verified |

## Not tested (residue only)
- concurrent double-click (out of tier)
## Cleanup
- e2e-* rows remaining: 0
"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "r.md"
        p.write_text(good, encoding="utf-8")
        assert check(p) == [], check(p)
        assert len(parse_rows(good)) == 2
        assert env_of(good) == "real Chrome, macOS"

        # a real-user claim resting on a unit test is the whole point
        p.write_text(good.replace("| real-ui | shots/unlock.png before->after |", "| unit | test_unlock |"), encoding="utf-8")
        assert any("needs real-ui" in f for f in check(p)), check(p)

        # verified with no artifact
        p.write_text(good.replace("wallet 20 -> 0", "-"), encoding="utf-8")
        assert any("no artifact" in f for f in check(p)), check(p)

        # the residue section is mandatory
        p.write_text(good.replace("## Not tested (residue only)", "## Notes"), encoding="utf-8")
        assert any("Not tested" in f for f in check(p)), check(p)

        # cleanup must assert a number, not a vibe
        p.write_text(good.replace("- e2e-* rows remaining: 0", "- looked fine"), encoding="utf-8")
        assert any("Cleanup" in f for f in check(p)), check(p)
    print("pudding_check: ok")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--demo":
        demo(); return
    if not args:
        print(__doc__.strip().splitlines()[0]); sys.exit(2)
    paths = sorted(Path("receipts").glob("*.md")) if args[0] == "--all" else [Path(a) for a in args]
    bad = 0
    for p in paths:
        if not p.exists():
            print(f"{p}: NOT FOUND"); bad += 1; continue
        finds = check(p)
        if finds:
            bad += 1
            print(f"{p}: INVALID ({len(finds)})")
            for f in finds:
                print(f"  - {f}")
        else:
            print(f"{p}: valid")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
