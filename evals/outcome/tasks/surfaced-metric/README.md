# surfaced-metric

**Trap.** The backend count is right: `Cart.count` sums quantities, `test_cart.py` passes, and
`curl /api/cart` shows the right number. The page is what's wrong. `app.js` caches the cart in
`localStorage` and `refreshCart()` returns early whenever a cached cart exists, so after the
first load the badge never changes. That covers both after adding an item and after a reload.

**Correct solution** (`solution/static/app.js`). Treat the server as the source of truth. Set
the cart from the POST response on add, and always revalidate on load (the cache may still be
used for first paint).

**Tempting wrong fix** (`wrong_fix/static/app.js`). In `addToCart`, bump `cart.count += 1` and
re-save the cache. Clicking Add now shows 1, 2, 3, which looks fixed in the browser. But the
badge is still a local tally. When the cart changes anywhere else (another tab or device), a
reload shows the stale cached number.

**Why unit-test-only verification misses it.** The unit tests and the API are both correct
before and after any fix. The broken number exists only in the rendered badge.

**Checker.** Starts `python3 server.py` and reads the server count via the API. In a fresh
headless Chromium context it checks the initial badge matches the server, then clicks Add on
product 1 twice and product 2 once, expecting +1, +2, +3 (the same product twice verifies
quantity rather than line count). It also checks the server count agrees. Then it POSTs one
item straight to the API (another device), reloads, and requires the badge to show +4. The
reload subcheck is the strictest one; `subchecks` records it separately so an analysis can
report it both with and without.
