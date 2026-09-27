"""Hidden checker: open the cart page on an emulated iPhone 14 (390px wide, touch, mobile,
3x - the phone the prompt names),
scroll to the Checkout button, and require it to be fully on screen, not covered or clipped
at its centre, and to open checkout.html when tapped there."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402

WIDTH = 390
CLIPPED = """e => { const r = e.getBoundingClientRect();
  for (let a = e.parentElement; a; a = a.parentElement) {
    const cs = getComputedStyle(a);
    if (cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
    const c = a.getBoundingClientRect();
    if (a === document.body || a === document.documentElement) continue;  // viewport checked separately
    if (r.left < c.left - 0.5 || r.right > c.right + 0.5 || r.top < c.top - 0.5 || r.bottom > c.bottom + 0.5) return a.className || a.tagName;
  }
  return null; }"""
HIT = """([x, y]) => { const el = document.elementFromPoint(x, y);
  const btn = [...document.querySelectorAll('a, button')].find(e => /checkout/i.test(e.textContent));
  return !!(el && btn && (el === btn || btn.contains(el))); }"""


def main():
    repo = c.worked_dir()
    sub, notes = {}, []
    with c.static_server(repo) as base:
        with c.browser_page(viewport={"width": WIDTH, "height": 844}, device_scale_factor=3,
                            is_mobile=True, has_touch=True) as (page, errors):
            page.goto(base + "/index.html")
            btn = page.get_by_role("link", name=re.compile(r"^\s*checkout\s*$", re.I))
            if btn.count() == 0:
                btn = page.get_by_role("button", name=re.compile(r"^\s*checkout\s*$", re.I))
            sub["checkout_button_present"] = btn.count() == 1
            if btn.count() != 1:
                c.emit(sub, "found %d Checkout controls" % btn.count())
            # Scroll the window only, the way a thumb does. Playwright's scroll_into_view would
            # also scroll overflow:hidden containers, which a user cannot do.
            btn.evaluate("e => window.scrollTo(0, Math.max(0, e.getBoundingClientRect().top + scrollY - 200))")
            box = btn.bounding_box()
            vw = page.evaluate("() => document.documentElement.clientWidth")
            notes.append("box=%s viewport_width=%s" % (box, vw))
            inside = bool(box) and box["x"] >= 0 and box["x"] + box["width"] <= vw + 0.5 and box["width"] > 0
            sub["fully_within_390px"] = inside
            clipper = btn.evaluate(CLIPPED)
            notes.append("clipped_by=%s" % clipper)
            sub["not_clipped_by_a_container"] = clipper is None
            cx, cy = (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2) if box else (-1, -1)
            on_screen = 0 <= cx < vw and 0 <= cy < 844
            sub["centre_not_clipped_or_covered"] = on_screen and page.evaluate(HIT, [cx, cy])
            if on_screen:
                page.touchscreen.tap(cx, cy)
                try:
                    page.wait_for_url(re.compile(r"checkout\.html"), timeout=3000)
                except Exception:
                    pass
            notes.append("after tap: %s" % page.url)
            sub["tap_opens_checkout"] = page.url.endswith("checkout.html")
            sub["no_page_errors"] = not errors
    c.emit(sub, "; ".join(notes))


if __name__ == "__main__":
    main()
