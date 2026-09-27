#!/usr/bin/env python3
"""pudding audit: how often did your agent say "done", and how often did it prove it?

    python3 audit.py              every project in your Claude Code history
    python3 audit.py --here       only the current project
    python3 audit.py --examples 5 also print 5 of the claims it found

Read-only and local. It reads the transcripts Claude Code already keeps under
~/.claude/projects/ and prints counts. Nothing is sent anywhere, and no message
text is printed unless you ask for examples.

The claim detector is the same one the pudding gate uses, so the number you get
here is the number the gate would have seen.
"""
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "hooks"))
from claims import detect  # noqa: E402

VERIFY_SKILLS = re.compile(r"pudding|proving-features-work|verification-before-completion|\bverify\b", re.I)
RECEIPT_PATH = re.compile(r"(?:^|/)receipts/[^/]+\.md$")
# Agents write files through Bash as often as through the Write tool - every receipt
# in pudding's own live tests went in via a heredoc - so both have to count.
BASH_RECEIPT = re.compile(r"(?:>|tee\s+(?:-a\s+)?|write_text\(|open\()[^\n]{0,40}?receipts/[\w.-]+\.md")


def config_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def encoded(path):
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def transcripts(here=False):
    base = config_dir() / "projects"
    if not base.exists():
        return []
    dirs = [base / encoded(Path.cwd().resolve())] if here else [d for d in base.iterdir() if d.is_dir()]
    return [f for d in dirs if d.exists() for f in d.glob("*.jsonl")]


def scan(files, want_examples=0):
    c = Counter()
    fams, examples, days, projects = Counter(), [], set(), set()
    for f in files:
        had_line = False
        try:
            fh = f.open(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"assistant"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "assistant" or d.get("isSidechain"):
                    continue
                had_line = True
                if d.get("timestamp"):
                    days.add(d["timestamp"][:10])
                for b in (d.get("message") or {}).get("content") or []:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text"):
                        c["messages"] += 1
                        found = detect(b["text"])
                        if found:
                            c["claims"] += 1
                            fams.update(x.family.name for x in found)
                            if len(examples) < want_examples:
                                examples.append(found[0].sentence.strip()[:140])
                    elif b.get("type") == "tool_use":
                        inp = b.get("input") or {}
                        if b.get("name") == "Skill" and VERIFY_SKILLS.search(str(inp.get("skill", ""))):
                            c["verify"] += 1
                        if b.get("name") in ("Write", "Edit") and RECEIPT_PATH.search(str(inp.get("file_path", ""))):
                            c["receipts"] += 1
                        elif b.get("name") == "Bash" and BASH_RECEIPT.search(str(inp.get("command", ""))):
                            c["receipts"] += 1
        if had_line:
            c["sessions"] += 1
            projects.add(f.parent.name)
    return c, fams, examples, sorted(days), len(projects)


def report(c, fams, examples, days, nprojects):
    if not c["sessions"]:
        return "pudding audit: no Claude Code transcripts found under " + str(config_dir() / "projects")
    span = f"{days[0]} to {days[-1]}" if days else "unknown dates"
    pct = (100 * c["claims"] / c["messages"]) if c["messages"] else 0
    lines = [
        f"\U0001F36E pudding audit - {c['sessions']} sessions across {nprojects} project(s), {span}",
        "",
        f"  messages from your agent        {c['messages']:>6}",
        f"  ...that claimed work was done   {c['claims']:>6}   ({pct:.1f}%)",
        f"  verification skill invoked      {c['verify']:>6}",
        f"  receipts written                {c['receipts']:>6}",
        "",
        f"  your agent said it was done {c['claims']} times.",
        f"  it wrote proof for {c['receipts']} of them.",
    ]
    if fams:
        lines += ["", "  kinds of claim: " + ", ".join(f"{k} {v}" for k, v in fams.most_common(6))]
    if examples:
        lines += ["", "  examples:"] + [f"    - {e}" for e in examples]
    lines += ["", "  counts only; nothing left this machine."]
    return "\n".join(lines)


def demo():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        os.environ["CLAUDE_CONFIG_DIR"] = td
        proj = Path(td) / "projects" / "-tmp-demo"
        proj.mkdir(parents=True)
        rows = [
            {"type": "assistant", "timestamp": "2026-09-01T00:00:00Z",
             "message": {"content": [{"type": "text", "text": "Done. It works end to end in the browser."}]}},
            {"type": "assistant", "timestamp": "2026-09-02T00:00:00Z",
             "message": {"content": [{"type": "text", "text": "Here is the plan for tomorrow."}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill",
                                                           "input": {"skill": "pudding"}}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write",
                                                           "input": {"file_path": "/x/receipts/a-2026.md"}}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash",
                "input": {"command": "cat > receipts/b-2026.md <<'EOF'\n| x |\nEOF"}}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash",
                "input": {"command": "cat receipts/b-2026.md"}}]}},  # reading is not writing
            {"type": "user", "message": {"content": "it works end to end"}},  # the user's words never count
        ]
        (proj / "s1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        c, fams, ex, days, n = scan(transcripts(), want_examples=2)
        assert (c["sessions"], c["messages"], c["claims"], c["verify"], c["receipts"]) == (1, 2, 1, 1, 2), c
        assert days == ["2026-09-01", "2026-09-02"] and n == 1
        out = report(c, fams, ex, days, n)
        assert "said it was done 1 times" in out and "works end to end" in out
        del os.environ["CLAUDE_CONFIG_DIR"]
    print("audit: ok")


def main():
    args = sys.argv[1:]
    if "--demo" in args:
        return demo()
    n = 0
    if "--examples" in args:
        i = args.index("--examples")
        n = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 5
    print(report(*scan(transcripts(here="--here" in args), want_examples=n)))


if __name__ == "__main__":
    main()
