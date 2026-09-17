# pudding

**The proof is in the pudding, not in the promise.**

> 160 sessions. 380 times my agent said it was done.
> It invoked the verification skill once.

That is measured, not rhetorical — a grep across every Claude Code transcript on my
machine since August. The skill was installed the whole time. It sat in the skill list
of every session and was never chosen, because the agent that would skip proving is the
same agent that skips the skill.

So pudding is not a skill. It is a gate the harness runs whether the agent wants it or not.

```
🍮  no pudding, no done.

  you said     It works end to end in the browser.
  you have     4 unit
  you need     a real-ui artifact: a screenshot, a DOM capture, or the URL you actually drove

  go look at it. then come back.
  (or write it down honestly:
   | works end to end | - | - | blocked: <why> |)
```

## Install

```
/plugin marketplace add samz905/pudding
/plugin install pudding@pudding
```

No account, no key, no server, no config. Restart, and it is armed.

## What it does

When your agent is about to end a turn, pudding reads the message it just wrote. If that
message claims work is done, it must be backed by a row in a receipt — and **the kind of
evidence has to match the kind of claim**:

| the claim | earned only by |
|---|---|
| works as a real user / end to end | `real-ui` — a screenshot, DOM, the URL actually driven |
| matches the design | `real-ui`, paired against the reference |
| deployed / live | `real-ui` whose `env` names the deployed target, not localhost |
| the number is right | `db` or `real-ui` showing the *surfaced* value move |
| the row / event is written | `db` |
| the request / webhook fires | `wire` |
| the bug is fixed | the reproduction, re-run, now failing to reproduce |
| faster / lighter | a before → after pair |
| the logic is correct | `unit` / `api` — necessary, never sufficient |

A thousand unit tests never add up to one "works as a real user". If the evidence does not
match, the turn does not end.

## Why this is different from a test gate

Other tools gate the **command**: did `npm test` exit 0. Replay that against real
incidents and it passes nearly all of them, because the tests were green and the *sentence*
was still false — "594 backend checks, 18 suites, all green" sitting one paragraph above a
claim about a Google sign-in flow nobody had opened. The last one that caught me was
"verified as a real user in Chrome", which was true, against `localhost`, while the user
was looking at the deployed URL.

Pudding gates the **claim**. The unit of enforcement is the sentence, not the suite.

It is also deterministic on purpose. [arXiv:2606.09863](https://arxiv.org/abs/2606.09863)
named this failure *false success* and measured five LLM judges against it: none exceeded
AUROC 0.65. A model grading a model is barely better than a coin flip here, so pudding
never asks one.

## It is not a nag

- No claim in the message → one regex sweep, and it exits. On real transcripts that is
  ~95% of turns.
- One block per claim. It cannot badger you; the harness recursion guard sees to that.
- Hedging is never punished. "Verifying on your real timeline before I tell you it works"
  passes, because it is honest.
- Quoted and code-fenced text is stripped first, so talking *about* a claim is not making one.

## Modes

```
/pudding block    no matching evidence, no end of turn   (default)
/pudding warn     claims ship, unearned ones get a scar and a log line
/pudding off      disarmed for this project
/pudding status   what it is now, and which of your prompts set it
```

Only your typed command writes the mode. The hook reads your keystrokes before the agent
sees them, so the agent is never the one holding its own leash — and if the mode file is
weakened any other way, the gate reverts to `block` and says so. **The only way to make
pudding easier on your agent is to type it yourself.**

## The receipt

Plain markdown, committed with your code, so the proof lives next to the thing it proves.

```markdown
# Receipt: unlock flow (2026-09-17)
tier: standard
env: real Chrome, macOS

| claim | method | artifact | status |
|---|---|---|---|
| unlock deducts 20 pts and splits 12/48 | db | wallet 20→0; rows ('platform',12),('creator',48) | verified |
| unlock works from the viewer's UI | real-ui | shots/unlock.png (before→after) | verified |
| forgot-password flow | - | - | blocked: SMTP capped 2/hr - user decision needed |

## Not tested (residue only)
- concurrent double-click (out of declared tier)
## Cleanup
- e2e-* rows remaining: 0
```

`env` is first class because "verified in headless Chromium" is not "works in the user's
Windows Chrome". `blocked` is a visible row because a gap you name is honest and a gap you
omit reads as covered.

`pudding_check.py` lints a receipt on its own — one file, stdlib only, no install.

## Where it came from

Months of real transcripts, mined for every time a user caught an agent claiming done on
something broken. The finding that shaped the whole design: **every incident had extensive
testing behind it.** The tests ran. The failure was always the final summary asserting more
than the evidence held. The lie lives in the prose, not the work.

Built in public at [@samarthbuilds](https://x.com/samarthbuilds). MIT.
