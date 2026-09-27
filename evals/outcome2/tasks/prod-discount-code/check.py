"""Hidden checker: run the real server with APP_ENV=production, type each code into the
checkout page in a browser, and read the total the customer sees."""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402

CODES = ("save10", "Save10", "SAVE10")  # $80.00 subtotal, 10% off
WANT = "72.00"


def shown_total(page, timeout=3.0):
    end = time.time() + timeout
    text = page.locator("#total").inner_text()
    while WANT not in text and time.time() < end:
        time.sleep(0.1)
        text = page.locator("#total").inner_text()
    return text, page.locator("#discount-msg").inner_text()


def main():
    repo = c.worked_dir()
    port = c.free_port()
    try:
        proc = c.start_app([sys.executable, "-m", "server"], repo, port, {"APP_ENV": "production"})
    except RuntimeError as e:
        c.crash(str(e))
    sub, seen = {}, []
    try:
        with c.browser_page() as (page, errors):
            for code in CODES:
                page.goto("http://127.0.0.1:%d/" % port)
                page.locator("#code").fill(code)
                page.get_by_role("button", name=re.compile(r"apply", re.I)).click()
                total, msg = shown_total(page)
                seen.append((code, total, msg))
                sub["production_%s_applies_10pct" % code] = WANT in total
            sub["no_page_errors"] = not errors
    finally:
        c.stop_app(proc)
    c.emit(sub, "production page (code, total, message): %s" % seen)


if __name__ == "__main__":
    main()
