#!/usr/bin/env python3
"""Package raw benchmark results for publication, with personal data scrubbed.

    python3 evals/package_results.py <results-dir> [<results-dir> ...] -o out.tar.gz

Claude Code writes the user's account email into every transcript's context, and
local paths name the user's home directory. Both are replaced before anything is
published; the output is then re-scanned and the script refuses to write the
archive if anything personal or credential-shaped survives.
"""
import io
import os
import re
import sys
import tarfile
from pathlib import Path

SCRUB = [
    (re.compile(r"[\w.+-]+@(?:gmail|googlemail|outlook|hotmail|icloud|yahoo|proton(?:mail)?)\.[a-z.]+"), "<redacted-email>"),
    (re.compile(re.escape(str(Path.home()))), "~"),
    (re.compile(r"/private/var/folders/[\w/.-]+?/T/"), "$TMPDIR/"),
]
LEAKS = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|xox[bp]-[0-9]{6,}|"
                   r"[\w.+-]+@(?:gmail|outlook|hotmail|icloud|yahoo)\.com")


def scrub(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data  # binary (screenshots): no text to leak
    for rx, rep in SCRUB:
        text = rx.sub(rep, text)
    return text.encode("utf-8")


def main():
    args = sys.argv[1:]
    out = Path(args[args.index("-o") + 1])
    dirs = [Path(a) for a in args[:args.index("-o")]]
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for d in dirs:
            for f in sorted(d.rglob("*")):
                if not f.is_file():
                    continue
                data = scrub(f.read_bytes())
                if LEAKS.search(data.decode("utf-8", "ignore")):
                    sys.exit(f"refusing to publish: something personal survived in {f}")
                info = tarfile.TarInfo(str(Path(d.name) / f.relative_to(d)))
                info.size = len(data)
                info.mtime = int(f.stat().st_mtime)
                tar.addfile(info, io.BytesIO(data))
    out.write_bytes(buf.getvalue())
    print(f"wrote {out} ({len(buf.getvalue()) // 1024} KB)")


if __name__ == "__main__":
    main()
