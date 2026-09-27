"""Bundle static/src into static/dist: drop comment lines and indentation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "static"
HEADER = "/* built by build.py from static/src - do not edit */\n"


def minify(text):
    lines = (l.strip() for l in text.splitlines())
    return "\n".join(l for l in lines if l and not l.startswith("//") and not l.startswith("/*"))


def main():
    (ROOT / "dist").mkdir(exist_ok=True)
    for src in sorted((ROOT / "src").iterdir()):
        body = minify(src.read_text())
        (ROOT / "dist" / src.name).write_text(HEADER + body + "\n")
        print("built", src.name)


if __name__ == "__main__":
    main()
