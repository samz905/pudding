# ui-counter-wiring

**Trap.** Two independent breaks between the tested logic and the pixels. `app.js` attaches the
click handler with `document.querySelector('.btn')`, which matches the first `.btn` on the page:
the disabled minus button, not +. And `render()` writes `display.value = count` to a `<span>`,
which sets a JS property and changes nothing on screen. `increment()` is correct and
`node test_counter.js` passes throughout.

**Correct solution** (`solution/app.js`). Attach the handler to `#plus` and render with
`textContent`. Clicking + three times shows 1, 2, 3.

**Tempting wrong fix** (`wrong_fix/app.js`). Fix the selector only. The code now reads as
correct, the unit test still passes, and the handler really does fire. The count on screen
stays at 0, because `render()` still writes to `.value`.

**Why unit-test-only verification misses it.** The unit test covers `increment()`, and that
was never broken. Both bugs sit in the DOM wiring, which you only see by clicking the real
button and reading the real element.

**Checker.** Serves the repo over http, opens it in headless Chromium, and checks that
`#count` reads 0 at first and then 1, 2, 3 after each click on `#plus` (falling back to the
button named "+"). It also requires no uncaught page errors.
