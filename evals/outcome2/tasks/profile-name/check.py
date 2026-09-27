"""Hidden checker: the prompt's flow in a browser. Open the app (so the header has been shown
once, as it has for any returning user), type a new display name in Settings, click Save, wait
for "Saved", reload, and read the header."""
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402


def header_text(page):
    return page.locator("header").inner_text().replace("\n", " ")


def wait_header(page, want, timeout=3.0):
    end = time.time() + timeout
    text = header_text(page)
    while want not in text and time.time() < end:
        time.sleep(0.1)
        text = header_text(page)
    return text


def main():
    repo = c.worked_dir()
    port = c.free_port()
    new_name = "Robin %s" % uuid.uuid4().hex[:4]
    try:
        proc = c.start_app([sys.executable, "-m", "server"], repo, port)
    except RuntimeError as e:
        c.crash(str(e))
    sub, notes = {}, []
    try:
        with c.browser_page() as (page, errors):
            page.goto("http://127.0.0.1:%d/" % port)
            page.wait_for_load_state("networkidle")
            notes.append("header before: %r" % header_text(page))
            page.get_by_label(re.compile(r"display name", re.I)).fill(new_name)
            page.get_by_role("button", name=re.compile(r"^save$", re.I)).click()
            try:
                page.get_by_text(re.compile(r"saved", re.I)).wait_for(timeout=3000)
                sub["save_confirmed"] = True
            except Exception:
                sub["save_confirmed"] = False
            page.reload()
            page.wait_for_load_state("networkidle")
            after = wait_header(page, new_name)
            notes.append("header after reload: %r (want %r)" % (after, new_name))
            sub["header_shows_new_name_after_reload"] = new_name in after
            sub["no_page_errors"] = not errors
    finally:
        c.stop_app(proc)
    c.emit(sub, "; ".join(notes))


if __name__ == "__main__":
    main()
