---
name: pudding
description: Use when about to claim work is done, tested, working, verified, or "should work" - and when planning how to verify a feature end-to-end. Triggers on user-facing behavior, tracked metrics/events, money/accounting, permissions/gating, more than one actor, or the urge to say "tested end to end" after only unit/API checks. No pudding, no done.
---

# pudding

> If this skill was opened by the user typing `/pudding <word>` (block, warn, off,
> status, help, evidence, statusline), the pudding hook has already handled it and
> shown the result. Reply in one line and stop; do not summarize this document.

**The proof is in the pudding, not in the promise.**

A completion claim is **earned by attached evidence, never asserted from memory.** The
failure this prevents is not skipped testing - it is real testing narrated as more than
it was: "I hit the API" reported as "works as a real user," a done-report written from a
tired memory of a long session. The lie lives in the prose, not the work. Pudding makes
the claim carry proof.

**Core loop:** plan the proof → fill a **receipt** while testing → the done-report is
**generated from the receipt**, and a claim without a row does not get said.

Write the receipt to a file at the project root, `receipts/<feature>-<date>.md`. It must
survive a long session and context compaction - which is exactly when overclaiming
happens. Screenshots and other captures go in the evidence folder named at the start of
each prompt (`receipts/evidence/<date>-<request>/`), never a temp dir.

With the pudding plugin installed, a Stop hook enforces this: after real code changes, a
turn that hands back needs a fresh verified row, and a claim needs a row whose method
matches it. This skill is how to plan and produce that evidence well.

## When to use

BEFORE saying done / working / tested / verified / "should work" about anything with:
user-facing behavior, tracked metrics or events, money or accounting, permissions or
gating, or more than one actor. Skip for: pure refactors already covered by tests, docs,
changes with no runtime surface.

## Phase 1 - Plan the proof (write it down)

1. **Declare the tier** (proof attaches to the DIFF, not the whole app):
   `smoke` (happy path, one actor - low-risk) · `standard` (all actors, main journeys,
   key edges - most work) · `exhaustive` (+ reconciliation, all edges, concurrency -
   money and data integrity).
2. **Actors.** Every party whose perspective changes the outcome. Two actors that cannot
   be the same person = two accounts. A single account cannot test a split, a follow,
   self-exclusion, or "the other person's view."
3. **Effects → prove the loop.** For every claimed effect (metric, event, row, email,
   charge), trace **trigger → persistence → surface** and observe all three. A 200
   response is not the number the user sees.
4. **Edges.** empty/first-run · unauthorized/other-actor/self-action · boundary
   (0, max, rounding, dedup/idempotency/double-submit) · concurrent · gated/locked ·
   error + retry, interrupt mid-action · non-destructive invariants.
5. **Fixtures & env.** What data/accounts must exist first? Which DB does the *running*
   app use? What needs a real browser? Record the **env** artifacts are captured in -
   headless ≠ the user's actual browser, and the receipt says which one you had. Name
   every blocker you cannot reach and **surface it - never silently substitute a weaker
   method.**

## Phase 2 - Execute and record

Drive the work the way the actor really does. For each planned row, record **as you go**:

```
claim | method | artifact | status
```

- **method** ∈ `unit` · `api` · `db` · `wire` (captured payload) · `real-ui`
  (screenshot/DOM/URL). Exact - this is the anti-lie field.
- **artifact** = something anyone can point at: a screenshot path, a before→after delta,
  a query result, a captured request, a named test. No artifact → status stays
  `unverified`. A `real-ui` artifact is a file inside the evidence folder that the user
  can open - an image you only looked at in your own context is not one.
- **status** ∈ `verified` · `unverified` · `blocked: <why - user decision needed>` ·
  `waived: <who/when>`. A skip the user chose is a **recorded decision** (`waived`),
  never a silent absence.
- Found a bug? Log it, fix it, **re-run that row**. A run that finds no bugs on
  non-trivial work is suspect, not reassuring.

## Phase 3 - The gate (before "done")

**1. Method integrity** - a claim may only rest on evidence of the matching kind:

| Claim | Only earned by |
|---|---|
| "works as a real user / end-to-end" | a **real-ui** artifact |
| "the number/metric is right" | **real-ui** or **db** showing the *surfaced* value moved |
| "the event/row is written" | **db** |
| "the request/webhook fires correctly" | **wire** |
| "matches the design" | a screenshot-vs-reference **pair**, not a checkbox |
| "the logic is correct" | **unit/api** - necessary, never sufficient for a user-facing claim |

A thousand `unit` artifacts never sum to one "works as a real user." Mismatched evidence
= claim not earned: downgrade it or go get the right kind.

**2. Generate the report FROM the receipt, not memory.** Two mandatory sections:
- **Verified** - each claim with method + artifact.
- **Not tested** - the honest *residue only*: genuine blockers (surfaced for a decision)
  and out-of-tier items. Testable + in-scope = you test it; this section is never a
  place to park work you could have done. Omitting a gap is a lie; parking dodged work
  here is the same lie wearing a disclaimer.

**3. Clean up and assert it.** Delete test data you created (tag it `e2e-*`), query to
confirm zero leftovers, state the result in the receipt.

## Red flags - you are about to overclaim

"I hit the endpoint, so it works" · "tests pass, it's done" · "it should work" ·
"basically end-to-end" · writing the report from memory · no Not-tested section ·
"I did tons of testing" (volume ≠ method) · "the API returns the right data, the UI
just displays it" (the wiring is where it silently breaks) · "it's late, I've clearly
done enough" (long sessions are when method-conflation happens - trust the receipt, not
the feeling) · "I'll mention gaps if they ask" (unstated gaps read as covered).

All of these mean: stop, open the receipt, downgrade the claim or go get the evidence.

## The bottom line

Plan the actors and the loops. Record evidence by method as you go. Let the receipt
write the report - and never claim more than the evidence earns. No pudding, no done.
