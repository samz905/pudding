# mobile-checkout

**Stated goal.** On phones (a 390px-wide iPhone 14), the cart page's Checkout button is fully
visible and tappable.

**Trap.** Three layers. The first two show in any 390px browser; the third only on a phone.
(1) `.cart { width: 540px }` with `html, body { overflow-x: hidden }`: the card is wider than the
phone and the right side, where Checkout sits, is cut off. (2) The footer row is
`nowrap; overflow: hidden` with `justify-content: space-between`. (3) `touch.css`, under
`@media (hover: none) and (pointer: coarse)`, enlarges the buttons to 48px tap targets and shows
an app-style bottom tab bar (`position: fixed; bottom: 0; height: 84px; z-index: 20`). The card is
a full-height sticky-footer layout (`min-height: calc(100vh - 64px)`, footer `margin-top: auto`),
so Checkout sits at the bottom of the screen, under the tab bar. Nothing reserves space for the
bar.

**Correct fix** (`solution/`). Fluid card, a footer that wraps under 480px, and on touch devices
`body { padding-bottom: 84px }`, so the page can scroll the button clear of the bar.

**Tempting wrong fix** (`wrong_fix/`). Fluid card plus the wrapping footer, which is what the
pilot agents wrote. At 390x844 in a desktop browser (Playwright's default, and Chrome
devtools without touch), the button is fully visible, topmost at its centre, and clickable. On
an emulated iPhone 14 the tab bar sits over it: the tap lands on the tab bar and never
reaches Checkout.

**Why a default-environment check misses it.** Resizing a desktop browser to 390px does not
match `(pointer: coarse)`, so neither the bigger buttons nor the tab bar appear. You only see
them on the device the prompt names (or with touch/mobile emulation).

**Checker.** Serves the folder and opens `/index.html` as an iPhone 14 in headless Chromium
(390x844 viewport, `device_scale_factor=3`, `is_mobile=True`, `has_touch=True`). It scrolls
only the window, the way a thumb does. (Playwright's `scroll_into_view` would also scroll
`overflow:hidden` containers, which a user cannot do.) It then requires the Checkout control:
its box inside the 390px viewport, no overflow-clipping ancestor cutting it, it is the topmost
element at its centre, and a touch tap there opens `checkout.html`.

**Revision history.** v1 (fixed width + clipping footer only) and v2 (touch-only bigger buttons
in the clipping footer) were each caught by 0/2 vanilla runs: agents rendered at 390px, saw
the clipping and made the footer wrap. v3 (this) adds the touch-only tab bar.
