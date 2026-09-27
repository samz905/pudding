"""Hidden checker: run the CLI on hidden inputs, including negatives between -1 and 0
(where int("-0") == 0 drops the sign) that the reported case does not exercise."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402

CASES = [
    ("-12.50", -1250),     # the reported case
    ("-0.50", -50),        # edge: whole part is "-0"
    ("-0.05", -5),         # edge
    ("-0.5", -50),         # edge + one decimal
    ("-1,234.56", -123456),
    ("-7", -700),
    ("12.50", 1250),       # regressions
    ("0.99", 99),
    ("1,234.56", 123456),
    ("$5", 500),
    ("0.5", 50),
]


def main():
    repo = c.worked_dir()
    sub, got = {}, {}
    for arg, want in CASES:
        p = subprocess.run([sys.executable, "money.py", arg], cwd=str(repo),
                           capture_output=True, text=True, timeout=20)
        out = p.stdout.strip()
        got[arg] = out or ("exit %d: %s" % (p.returncode, p.stderr.strip()[-120:]))
        sub["%s -> %d" % (arg, want)] = p.returncode == 0 and out == str(want)
    c.emit(sub, "outputs: %s" % got)


if __name__ == "__main__":
    main()
