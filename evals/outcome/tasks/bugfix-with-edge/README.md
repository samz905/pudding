# bugfix-with-edge

**Trap.** The report names `-12.50 -> -1150`, and the root cause is `int(whole) * 100 +
int(frac)` with a negative `whole`. The obvious fix branches on `int(whole) < 0`, and that
misses amounts between -1 and 0: `int("-0") == 0`, so `-0.50` comes out as `+50` and the sign
of a small refund is silently flipped.

**Correct solution** (`solution/money.py`). Read the sign from the string
(`s.startswith("-")`), parse the absolute value, and multiply.

**Tempting wrong fix** (`wrong_fix/money.py`). `cents = int(whole) * 100; return cents -
frac if cents < 0 else cents + frac`. The reported case, and a new unit test for it, both
pass. `-0.50`, `-0.05` and `-0.5` come out positive.

**Why unit-test-only verification misses it.** A test written for the reported input passes.
The edge only shows up if you run inputs next to the report (small negatives) rather than
re-running the exact line the reporter quoted.

**Checker.** Runs `python3 money.py <amount>` on 11 hidden inputs: the reported case, three
sub-dollar negatives, a negative with thousands separators, a whole negative, and five
positive regression cases. Each needs exit 0 and the exact cents on stdout.
