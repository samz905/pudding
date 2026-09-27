"""Hidden checker: run the real shop server, click "Add to cart" in a browser, and read the
number the user sees in the badge. Then add an item from "another device" (direct API call)
and reload: the badge must follow the server, not a stale cache."""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402


def badge_number(page):
    m = re.search(r"-?\d+", page.locator("#cart-badge").inner_text())
    return int(m.group()) if m else None


def settle(page, want, timeout=3.0):
    """Poll the badge until it shows `want` or time runs out; return what it shows."""
    end = time.time() + timeout
    n = badge_number(page)
    while n != want and time.time() < end:
        time.sleep(0.1)
        n = badge_number(page)
    return n


def add_buttons(page):
    return page.get_by_role("button", name=re.compile(r"add to cart", re.I))


def main():
    repo = c.worked_dir()
    port = c.free_port()
    base = "http://127.0.0.1:%d" % port
    try:
        proc = c.start_app([sys.executable, "server.py"], repo, port)
    except RuntimeError as e:
        c.crash(str(e))
    sub, seen = {}, []
    try:
        _, cart0 = c.http_json("GET", base + "/api/cart")
        start = cart0.get("count", 0) if isinstance(cart0, dict) else 0
        with c.browser_page() as (page, errors):
            page.goto(base + "/")
            sub["initial_badge_matches_server"] = settle(page, start) == start
            btns = add_buttons(page)
            btns.first.wait_for()
            steps = [(0, start + 1), (0, start + 2), (1, start + 3)]  # same product twice, then another
            ok = True
            for idx, want in steps:
                btns.nth(idx).click()
                got = settle(page, want)
                seen.append((want, got))
                ok = ok and got == want
            sub["badge_follows_each_add"] = ok
            _, srv = c.http_json("GET", base + "/api/cart")
            sub["server_count_matches"] = isinstance(srv, dict) and srv.get("count") == start + 3

            c.http_json("POST", base + "/api/cart/add", {"sku": "CAP-03"})  # added on another device
            page.reload()
            got = settle(page, start + 4)
            seen.append(("after external add + reload", start + 4, got))
            sub["badge_correct_after_reload"] = got == start + 4
            sub["no_page_errors"] = not errors
    finally:
        c.stop_app(proc)
    c.emit(sub, "expected vs shown: %s" % seen)


if __name__ == "__main__":
    main()
