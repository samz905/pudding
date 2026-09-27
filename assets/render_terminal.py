#!/usr/bin/env python3
"""Render the README's terminal image from pudding's REAL block output.

    python3 assets/render_terminal.py            writes assets/block.svg

The block text is produced by calling the gate itself on a throwaway repo, so the
image can't drift from what the hook actually prints.
"""
import html
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "hooks"), str(ROOT / "skills" / "pudding" / "scripts")]
import gate  # noqa: E402

PROMPT = "fix the discount on checkout and make sure it actually works"
CLAIM = "Checkout is done - the discount flow works end to end in the browser, all 42 tests pass."
RECEIPT = """# Receipt: checkout (2026-09-27)
tier: standard
env: local

| claim | method | artifact | status |
|---|---|---|---|
| cart total is computed correctly | unit | test_cart.py::test_total | verified |
| discount applies on the server | api | POST /cart -> 200, total 45.00 | verified |
| totals round to the cent | unit | test_cart.py::test_rounding | verified |
| empty cart shows the empty state | unit | test_cart.py::test_empty | verified |

## Not tested (residue only)
- none
## Cleanup
- e2e rows remaining: 0
"""


def real_block():
    td = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", str(td)], check=True)
    (td / "receipts").mkdir()
    (td / "checkout.tsx").write_text("x")
    (td / "receipts" / "checkout-2026-09-27.md").write_text(RECEIPT)
    out = gate.decide({"hook_event_name": "Stop", "session_id": "readme", "prompt_id": "a91f3c0e",
                       "last_assistant_message": CLAIM}, td)
    return out["reason"]


def svg(lines, width=920):
    lh, top, left = 23, 58, 28
    h = top + lh * len(lines) + 26
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" viewBox="0 0 {width} {h}">',
           '<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:15px;'
           'white-space:pre}</style>',
           f'<rect width="{width}" height="{h}" rx="12" fill="#1E1A17"/>',
           f'<rect width="{width}" height="36" rx="12" fill="#2A2420"/><rect y="24" width="{width}" height="12" fill="#2A2420"/>',
           '<circle cx="22" cy="18" r="6" fill="#FF5F57"/><circle cx="42" cy="18" r="6" fill="#FEBC2E"/>'
           '<circle cx="62" cy="18" r="6" fill="#28C840"/>',
           f'<text x="{width // 2}" y="23" fill="#8C8076" text-anchor="middle" style="font-size:13px">claude</text>']
    for i, (color, text, weight) in enumerate(lines):
        w = ' font-weight="700"' if weight else ""
        out.append(f'<text xml:space="preserve" x="{left}" y="{top + i * lh}" fill="{color}"{w}>{html.escape(text)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    block = real_block().splitlines()
    dim, text, amber, mute, red = "#8C8076", "#EDE6DD", "#F2C24F", "#B7AA9C", "#FF8A7A"
    lines = [(dim, "> " + PROMPT, False), (dim, "", False),
             (text, "⏺ " + CLAIM, False), (dim, "", False),
             (red, "  ⎿  Stop hook error:", False)]
    for ln in block:
        if "no pudding" in ln:
            lines.append((amber, "     " + ln.strip(), True))
        elif ln.strip().startswith(("you need", "and ")):
            lines.append((amber, "   " + ln, False))
        elif ln.strip().startswith(("you said", "you have")):
            lines.append((text, "   " + ln, False))
        else:
            lines.append((mute, "   " + ln, False))
    (ROOT / "assets" / "block.svg").write_text(svg(lines))
    print("wrote assets/block.svg")


if __name__ == "__main__":
    main()
