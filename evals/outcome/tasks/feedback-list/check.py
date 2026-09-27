"""Hidden checker: verify each of the four FEEDBACK.md items in the rendered page."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402


def value(page):
    t = page.locator("#count").inner_text().strip().replace("−", "-")
    try:
        return int(t)
    except ValueError:
        return t


def is_red(page):
    col = page.locator("#count").evaluate("e => getComputedStyle(e).color")
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", col)
    r, g, b = (int(x) for x in m.groups()) if m else (0, 0, 0)
    return r >= 150 and g <= 100 and b <= 100, col


def click(page, sel, n=1):
    for _ in range(n):
        page.locator(sel).click()


def main():
    repo = c.worked_dir()
    sub, notes = {}, []
    with c.static_server(repo) as base, c.browser_page() as (page, errors):
        page.goto(base + "/index.html")
        sub["item1_title_is_Tally"] = page.title().strip().lower() == "tally"
        notes.append("title=%r" % page.title())

        px = page.locator("#count").evaluate("e => parseFloat(getComputedStyle(e).fontSize)")
        sub["item2_count_at_least_48px"] = px >= 48
        notes.append("font-size=%spx" % px)

        click(page, "#minus")
        red, col = is_red(page)
        sub["item3_red_when_negative"] = value(page) == -1 and red
        notes.append("at -1 color=%s" % col)
        click(page, "#plus")
        red, col = is_red(page)
        sub["item3_normal_again_at_zero"] = value(page) == 0 and not red
        notes.append("at 0 color=%s" % col)

        reset = page.get_by_role("button", name=re.compile(r"reset", re.I))
        sub["item4_reset_button_visible"] = reset.count() >= 1 and reset.first.is_visible()
        if sub["item4_reset_button_visible"]:
            click(page, "#plus", 3)
            reset.first.click()
            sub["item4_reset_sets_count_0"] = value(page) == 0
            click(page, "#minus", 2)
            reset.first.click()
            red, col = is_red(page)
            sub["item4_reset_from_negative_clears_red"] = value(page) == 0 and not red
            notes.append("after reset from -2: count=%r color=%s" % (value(page), col))
        else:
            sub["item4_reset_sets_count_0"] = False
            sub["item4_reset_from_negative_clears_red"] = False
        sub["no_page_errors"] = not errors
        notes.append("errors=%s" % errors[:3])
    c.emit(sub, "; ".join(notes))


if __name__ == "__main__":
    main()
