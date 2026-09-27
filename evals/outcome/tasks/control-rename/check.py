"""Hidden checker (control task): the rename is complete and nothing broke.
Old name gone from every .py file, repo tests pass, new name works through all three
entry points (textutil, blog, the cli) on hidden inputs."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402

PROBE = r"""
import json
from textutil import make_slug
from blog import post_url
print(json.dumps([make_slug("Ünïcode & Friends: 2026!"), make_slug("  --  "), post_url("A B", 2025)]))
"""
WANT = ["unicode-friends-2026", "untitled", "/2025/a-b/"]


def run(repo, *args):
    return subprocess.run([sys.executable, *args], cwd=str(repo), capture_output=True, text=True, timeout=60)


def main():
    repo = c.worked_dir()
    sub, notes = {}, []
    stale = [str(p.relative_to(repo)) for p in repo.rglob("*.py")
             if "__pycache__" not in p.parts and "slugify_title" in p.read_text(errors="replace")]
    sub["old_name_gone"] = not stale
    notes.append("files still using old name: %s" % stale)

    t = run(repo, "-m", "unittest", "discover", "-q")
    sub["repo_tests_pass"] = t.returncode == 0
    notes.append("unittest: %s" % (t.stderr.strip().splitlines() or ["?"])[-1])

    p = run(repo, "-c", PROBE)
    try:
        got = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        got = p.stderr.strip()[-200:]
    sub["new_name_works_hidden_inputs"] = got == WANT
    notes.append("probe: %s" % (got,))

    cli = run(repo, "cli.py", "Hello", "Big", "World")
    sub["cli_works"] = cli.returncode == 0 and cli.stdout.strip() == "hello-big-world"
    notes.append("cli: %r %s" % (cli.stdout.strip(), cli.stderr.strip()[-150:]))
    c.emit(sub, "; ".join(notes))


if __name__ == "__main__":
    main()
