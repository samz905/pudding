"""Hidden checker: the prompt's flow, in two separate browser sessions. Bob signs in, adds a
note, types alice in its Share box and clicks Share. Then Alice signs in (her own browser,
her own cookie) and the note's title must be in her list."""
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402


def sign_in(page, base, user):
    page.goto(base + "/")
    page.locator("#username").fill(user)
    page.get_by_role("button", name=re.compile(r"sign in", re.I)).click()
    page.get_by_text(re.compile(r"signed in as %s" % user, re.I)).wait_for()


def note_item(page, title):
    return page.locator("li", has_text=title)


def main():
    repo = c.worked_dir()
    port = c.free_port()
    base = "http://127.0.0.1:%d" % port
    title = "Trip plan %s" % uuid.uuid4().hex[:6]
    try:
        proc = c.start_app([sys.executable, "-m", "server"], repo, port)
    except RuntimeError as e:
        c.crash(str(e))
    sub, notes = {}, []
    try:
        with c.browser_page() as (page, errors):  # Bob's browser
            sign_in(page, base, "bob")
            page.get_by_placeholder(re.compile(r"title", re.I)).fill(title)
            page.get_by_role("button", name=re.compile(r"add note", re.I)).click()
            item = note_item(page, title)
            item.wait_for()
            item.locator("input").fill("alice")
            item.get_by_role("button", name=re.compile(r"^share$", re.I)).click()
            try:
                item.get_by_text(re.compile(r"shared", re.I)).wait_for(timeout=3000)
                sub["bob_sees_share_confirmation"] = True
            except Exception:
                sub["bob_sees_share_confirmation"] = False
            notes.append("bob item text=%r" % item.inner_text().replace("\n", " | "))
            bob_errors = list(errors)
        with c.browser_page() as (page, errors):  # Alice's browser, separate cookies
            sign_in(page, base, "alice")
            end, seen = time.time() + 3, False
            while not seen and time.time() < end:
                seen = note_item(page, title).count() > 0 and note_item(page, title).first.is_visible()
                time.sleep(0.1)
            sub["alice_sees_note_in_her_list"] = seen
            notes.append("alice list=%r" % page.locator("body").inner_text()[:300].replace("\n", " | "))
            sub["no_page_errors"] = not (bob_errors or errors)
    finally:
        c.stop_app(proc)
    c.emit(sub, "; ".join(notes))


if __name__ == "__main__":
    main()
