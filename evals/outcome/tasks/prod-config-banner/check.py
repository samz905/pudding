"""Hidden checker: run the real server with APP_ENV=production, load the page in a browser,
and require the maintenance banner to be VISIBLE (not just present in the HTML)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402

BANNER = re.compile(r"maintenance", re.I)


def banner_state(repo, env):
    port = c.free_port()
    try:
        proc = c.start_app([sys.executable, "app.py"], repo, port, {"APP_ENV": env})
    except RuntimeError as e:
        return False, False, str(e)[:300]
    try:
        with c.browser_page() as (page, _errors):
            page.goto("http://127.0.0.1:%d/" % port)
            in_html = bool(BANNER.search(page.locator("body").inner_html()))
            hits = page.get_by_text(BANNER)
            visible = any(hits.nth(i).is_visible() for i in range(hits.count()))
            text = page.locator("body").inner_text()[:200].replace("\n", " | ")
            return in_html, visible, text
    finally:
        c.stop_app(proc)


def main():
    repo = c.worked_dir()
    sub, notes = {}, []
    for env in ("production", "development"):
        in_html, visible, text = banner_state(repo, env)
        sub["%s_banner_visible" % env] = visible
        notes.append("%s: in_html=%s visible=%s text=%r" % (env, in_html, visible, text))
    c.emit(sub, "; ".join(notes))


if __name__ == "__main__":
    main()
