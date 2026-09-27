# Receipt: pudding 1.0.0 (2026-09-27)
tier: exhaustive
env: macOS 26 (Darwin 25.6), Claude Code 2.1.283, Python 3.12 and system Python 3.9.6; GitHub Actions ubuntu-latest and macos-latest for CI; interactive sessions driven through tmux, headless sessions through `claude -p`

| claim | method | artifact | status |
|---|---|---|---|
| installs from GitHub with the two README commands, scoped to one project | real-ui | receipts/evidence/2026-09-27-release/github-install-settings.json | verified |
| a fresh install shows the welcome once, in a real interactive terminal | real-ui | receipts/evidence/2026-09-27-release/github-install-session.txt | verified |
| from that install, a done-claim with no evidence is blocked on screen and the agent retracts it | real-ui | receipts/evidence/2026-09-27-release/github-install-session.txt (block, then "I cannot claim it works end to end") | verified |
| every user-facing behaviour works in a real headless session - 12 scenarios | api | receipts/evidence/2026-09-27-release/e2e-results.md (12/12) | verified |
| every self-check passes on Python 3.9 and 3.12, Linux and macOS | api | receipts/evidence/2026-09-27-release/ci-run.txt (4/4 jobs) | verified |
| the detector is 84% precise with 64% recall on a held-out split frozen before it existed | unit | receipts/evidence/2026-09-27-release/detector-heldout.txt | verified |
| on fresh real messages, the detector is 78% precise with about 67% recall | db | evals/claims/results/real-world.md (blind-labeled sample of 120) | verified |
| agents claim success on most of their failures, whatever you tell them | db | evals/outcome/REPORT.md (Study 1: 75-100% of failures, every arm) | verified |
| pudding lowers false success against the same rules given as a prompt | db | evals/outcome2/ (Study 2, running at time of writing) | unverified |
| works on Windows | - | - | blocked: no Windows machine; hooks call python3, which Windows may not provide |
| the social preview card is set on GitHub | - | assets/social.png exists | blocked: GitHub only accepts it through the web UI - a maintainer action |

## Not tested (residue only)
- Windows (blocked above).
- Other agent harnesses (Cursor, Codex): out of scope - enforcement is Claude Code's Stop hook.
- Detector recall on phrasing outside web and general software: out of scope by design.

## Cleanup
- tmux test sessions remaining: 0
- scratch repositories left inside this repo: 0 (a stray skills/pudding-receipt/receipts/ was found and removed)
