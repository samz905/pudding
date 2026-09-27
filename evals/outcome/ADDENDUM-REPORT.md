# Addendum - pudding v5 on Study 1's tasks

Pre-registered in [`PREREGISTRATION-ADDENDUM.md`](PREREGISTRATION-ADDENDUM.md) before its first run
(amended once, before any data, to pin the commit). 8 tasks x 3 repeats = 24 runs, same runner,
tasks, model and grader as Study 1, run after it. Shown alongside Study 1's arms for comparison;
the time separation is a disclosed confound.

v5 adds the rule that work reported back after real code changes needs a verified row however
it is phrased, scopes "work" to the current session, and holds turns over evidence rather than
receipt formatting.

## Trap tasks (6 tasks, each with a user-visible defect the obvious test misses)

| arm | task success | false success | false success given failure | honest failure | under-claim |
|---|---|---|---|---|---|
| vanilla | 12/18 = 67% [44-84] | 5/18 = 28% [12-51] | 5/6 = 83% [44-97] | 1/6 = 17% [3-56] | 0/12 = 0% [0-24] |
| prompt | 14/18 = 78% [55-91] | 4/18 = 22% [9-45] | 4/4 = 100% [51-100] | 0/4 = 0% [0-49] | 0/14 = 0% [0-22] |
| nag | 13/18 = 72% [49-88] | 5/18 = 28% [12-51] | 5/5 = 100% [57-100] | 0/5 = 0% [0-43] | 0/13 = 0% [0-23] |
| pudding | 14/18 = 78% [55-91] | 3/18 = 17% [6-39] | 3/4 = 75% [30-95] | 1/4 = 25% [5-70] | 2/14 = 14% [4-40] |
| pudding-v5 | 15/18 = 83% [61-94] | 3/18 = 17% [6-39] | 3/3 = 100% [44-100] | 0/3 = 0% [0-56] | 4/15 = 27% [11-52] |


## Controls (no trap: a simple rename, and a question that asks for no change)

| arm | task success | runs with a block | blocks per run |
|---|---|---|---|
| vanilla | 6/6 = 100% [61-100] | 0/6 = 0% [0-39] | 0.00 |
| prompt | 6/6 = 100% [61-100] | 0/6 = 0% [0-39] | 0.00 |
| nag | 6/6 = 100% [61-100] | 6/6 = 100% [61-100] | 1.00 |
| pudding | 6/6 = 100% [61-100] | 3/6 = 50% [19-81] | 0.67 |
| pudding-v5 | 6/6 = 100% [61-100] | 3/6 = 50% [19-81] | 1.50 |


## Cost of the gate (all tasks)

| arm | median turns | median wall s | mean cost $ | blocks per run |
|---|---|---|---|---|
| vanilla | 7 | 24 | 0.16 | 0.00 |
| prompt | 17 | 62 | 0.30 | 0.00 |
| nag | 14 | 42 | 0.24 | 1.04 |
| pudding | 31 | 274 | 0.58 | 1.58 |
| pudding-v5 | 26 | 208 | 0.56 | 1.54 |


## Hypotheses

- **H4 - no worse on false success: consistent.** 3/18 (17%), identical to v2. All three are the
  cart-badge task, whose checker tests beyond its prompt (see Study 1's REPORT).
- **H5 - zero blocks on the question control: confirmed.** 0 of 3 runs (v2 blocked 1 of 3). The
  fix for counting pudding's own files as code changes works.
- **H5 - cost on the rename control: bad.** All 3 rename runs were blocked three times and logged
  as escapes.

## A bug this run found

The escapes on the rename control were not what they looked like. In the first one examined, the
agent restated its claim twice without writing a receipt, then wrote a valid receipt after the
third block. On the fourth stop the evidence was there - but the gate checked its block budget
*before* looking at the evidence, and logged the turn as escaped. An agent that finally did the
right thing was recorded as having beaten the gate. 8 of 24 v5 runs ended in an escape; some
share of those are this bug. Fixed in `515ce31`: the budget now applies only to a turn that is
still unearned. Study 2 measures the fixed version.

Under-claiming rose to 4 of 15 passing runs (v2: 2 of 14). v5 makes agents hedge more; that is a
real cost of the rule and is reported, not explained away.
