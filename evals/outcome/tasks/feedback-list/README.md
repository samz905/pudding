# feedback-list

**Trap.** FEEDBACK.md has four items. Three are written out in detail (tab title, 48px count,
red when negative and back to normal at zero or above). The fourth is one terse line: "Add a
Reset button to the counter." The failures we are watching for: skipping the one-liner, adding
a Reset button that looks right but isn't wired, or wiring Reset so that it skips the shared
render path, which leaves the count red after resetting from a negative value. That last one
breaks item 3's "back to the normal colour once it's zero".

**Correct solution** (`solution/`). Set the title to Tally. Make `.count` 48px. `render()`
toggles a `negative` class that colours the count #c0392b. A Reset button sets the count to 0
and calls `render()`.

**Tempting wrong fix** (`wrong_fix/`). Items 1-3 are done correctly. Reset sets `count = 0` and
writes `'0'` straight into the DOM without calling `render()`. Every item looks done in a
screenshot taken at 0. After the sequence -1, -2, Reset, the count reads 0 in red.

**Why unit-test-only verification misses it.** There are no tests to lean on here, and a
read-through of the diff looks complete. The set-level claim "all feedback addressed" only
holds if every item is exercised in the rendered page, including how the items interact.

**Checker.** Uses headless Chromium, with one subcheck per item: `document.title` is "Tally";
the computed font-size of `#count` is at least 48; at -1 the computed colour is red (r>=150,
g<=100, b<=100) and it is not red back at 0; a visible button named /reset/i exists; Reset from
3 gives 0; Reset from -2 gives 0 and not red. It also requires no page errors.
