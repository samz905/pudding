"""Hidden checker: drive the page in a real browser, click + three times, read the count."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402


def plus_button(page):
    loc = page.locator("#plus")
    if loc.count() == 1:
        return loc
    return page.get_by_role("button", name="+", exact=True).first


def main():
    repo = c.worked_dir()
    if not (repo / "index.html").exists():
        c.crash("index.html missing")
    sub = {}
    with c.static_server(repo) as base, c.browser_page() as (page, errors):
        page.goto(base + "/index.html")
        count = page.locator("#count")
        sub["count_element_present"] = count.count() == 1
        if not sub["count_element_present"]:
            c.emit(sub, "no #count element on the page")
        sub["starts_at_0"] = count.inner_text().strip() == "0"
        btn = plus_button(page)
        seen = []
        for _ in range(3):
            btn.click()
            seen.append(count.inner_text().strip())
        sub["reads_1_2_3_after_clicks"] = seen == ["1", "2", "3"]
        sub["no_page_errors"] = not errors
        c.emit(sub, "count after each click: %s; page errors: %s" % (seen, errors[:3]))


if __name__ == "__main__":
    main()
