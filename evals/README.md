# How pudding is measured

Everything here is reproducible, and every result is committed as it came out - including
the rounds that didn't go well. If a number in the README can't be traced to a file in this
folder, that's a bug; please open an issue.

| question | where | headline |
|---|---|---|
| Does it recognise a completion claim? | [`claims/`](claims/) | On fresh real messages: 78% precision, ~67% recall. On synthetic held-out: 84% / 64%. [All rounds](claims/results/). |
| Does it change what agents tell you? | [`outcome/`](outcome/) (Study 1), [`outcome2/`](outcome2/) (Study 2) | See each `REPORT.md`. |
| Does every feature work in a real session? | [`e2e/`](e2e/) | 12 scenarios, each a real headless Claude Code session. |

## Principles

- **Held-out means never seen.** Each labeled split was frozen, hash committed, before the
  detector version it measures was run on it. Tuning happened on other splits.
- **Independent labels.** Datasets were written and labeled by separate model contexts that
  never saw the detector. Real-world samples were labeled blind to what the detector said.
- **Pre-registered outcomes.** Each outcome study's tasks, checkers, arms, metrics and analysis
  were committed before its first run. Deviations are reported in the study's REPORT.md.
- **State, not self-report.** Outcome checkers test the real result (a browser clicks the
  button, a server is restarted and read back), never the agent's own tests.
- **Fair controls.** The strongest control receives pudding's exact rules as a prompt, so the
  only difference is enforcement. A second control forces one extra "double-check" turn, so a
  win can't be explained by the extra attempt alone.
- **Raw data published.** Every run's transcript, diff and checker output is attached to the
  GitHub release, with personal data scrubbed by `package_results.py`.

## Reproduce

```
python3 evals/claims/eval.py test3                 # detector on a held-out split
python3 evals/e2e/run.py                           # every feature, in real sessions
cd evals/outcome && python3 run.py --help          # an outcome study (costs real API usage)
```
