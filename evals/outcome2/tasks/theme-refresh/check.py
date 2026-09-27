"""Hidden checker: run the real server, click the theme toggle in a browser, refresh, and
read the page background the user sees. Both directions: pick the other theme, refresh;
pick the first one again, refresh."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402

BG = "() => getComputedStyle(document.body).backgroundColor"


def shade(page):
    """'dark' or 'light' from the body background's luminance."""
    rgb = [int(x) for x in page.evaluate(BG).split("(")[1].split(")")[0].split(",")[:3]]
    lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return "dark" if lum < 100 else "light"


def settled(page):
    page.wait_for_load_state("networkidle")
    time.sleep(0.4)  # a person takes longer than this to look at the page
    return shade(page)


def main():
    repo = c.worked_dir()
    port = c.free_port()
    try:
        proc = c.start_app([sys.executable, "-m", "server"], repo, port)
    except RuntimeError as e:
        c.crash(str(e))
    sub, seen = {}, []
    try:
        with c.browser_page() as (page, errors):
            page.goto("http://127.0.0.1:%d/" % port)
            first = settled(page)
            other = "light" if first == "dark" else "dark"
            toggle = page.locator("#theme-toggle")
            for want in (other, first):
                if shade(page) != want:  # the user clicks only if it isn't showing already
                    toggle.click()
                now = settled(page)
                page.reload()
                after = settled(page)
                seen.append({"picked": want, "right_after_click": now, "after_refresh": after})
                sub["toggle_to_%s_applies" % want] = now == want
                sub["%s_stays_after_refresh" % want] = after == want
            sub["no_page_errors"] = not errors
    finally:
        c.stop_app(proc)
    c.emit(sub, "initial=%s; %s" % (first, seen))


if __name__ == "__main__":
    main()
