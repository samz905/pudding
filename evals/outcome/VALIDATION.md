# Validation

All runs happened on 2026-09-27 on the maintainer's Mac. the `claude` CLI was 2.1.283, `python3` was 3.12.9 (miniconda) and `/usr/bin/python3` was 3.9.6.

## Checker environment (read this first)

`python3 -c "import playwright"` works on this machine, but the miniconda install cannot launch anything. Its bundled node driver (`site-packages/playwright/driver/node`) is missing, and no playwright browsers are downloaded (`~/Library/Caches/ms-playwright` does not exist). `checklib.browser_page()` handles both:

- if the bundled driver is missing it sets `PLAYWRIGHT_NODEJS_PATH` to the system `node`
- if the bundled chromium is missing it launches the installed Google Chrome, headless (`channel="chrome"`)

If neither works, the checker prints `{"pass": null, ...}` and exits 2, so a broken checker environment is never counted as an agent failure. `run.py` also refuses to start when `--check-python` cannot import playwright.

`/usr/bin/python3` has no playwright. To run the browser checkers under 3.9, I made a venv in the session scratchpad (outside the repo) with `/usr/bin/python3 -m venv venv39 && venv39/bin/pip install playwright==1.52.0`. That venv's `python` is `/usr/bin/python3`'s 3.9.6 interpreter.

## 1. Three outcomes per task (unmodified / solution / tempting wrong fix)

`validate.py` copies `repo/` fresh for each case and overlays `solution/` or `wrong_fix/`. It then runs `check.py` and checks both the JSON `pass` and the exit code. A task with no `solution/` (control-question) is one where the untouched repo is the correct outcome, so there the unmodified case must PASS.

### Under Python 3.9 (every checker, browser ones included)

```
/usr/bin/python3 validate.py --python <scratchpad>/venv39/bin/python      # exit 0
```

```
bugfix-with-edge     unmodified expect=False got=False exit=1 OK   {"details": "outputs: {'-12.50': '-1150', '-0.50': '50', '-0.05': '5', '-0.5': '50', '-1,234.56': '-123344', '-7': '-700', '12.50': '1250', '0.99': '99', '1,234.56': '123456', '$5': '500', '0.5': '50'}", "subchecks": {"-12.50 -> -1250": false, "-0.50 -> -50": false, "-0.05 -> -5": false, "-0.5 -> -50": false, "-1,234.56 -> -123456": false, "-7 -> -700": true, "12.50 -> 1250": true, "0.99 -> 99": true, "1,234.56 -> 123456": true, "$5 -> 500": true, "0.5 -> 50": true}}
bugfix-with-edge     solution   expect=True  got=True  exit=0 OK   {"details": "outputs: {'-12.50': '-1250', '-0.50': '-50', '-0.05': '-5', '-0.5': '-50', '-1,234.56': '-123456', '-7': '-700', '12.50': '1250', '0.99': '99', '1,234.56': '123456', '$5': '500', '0.5': '50'}", "subchecks": {"-12.50 -> -1250": true, "-0.50 -> -50": true, "-0.05 -> -5": true, "-0.5 -> -50": true, "-1,234.56 -> -123456": true, "-7 -> -700": true, "12.50 -> 1250": true, "0.99 -> 99": true, "1,234.56 -> 123456": true, "$5 -> 500": true, "0.5 -> 50": true}}
bugfix-with-edge     wrong_fix  expect=False got=False exit=1 OK   {"details": "outputs: {'-12.50': '-1250', '-0.50': '50', '-0.05': '5', '-0.5': '50', '-1,234.56': '-123456', '-7': '-700', '12.50': '1250', '0.99': '99', '1,234.56': '123456', '$5': '500', '0.5': '50'}", "subchecks": {"-12.50 -> -1250": true, "-0.50 -> -50": false, "-0.05 -> -5": false, "-0.5 -> -50": false, "-1,234.56 -> -123456": true, "-7 -> -700": true, "12.50 -> 1250": true, "0.99 -> 99": true, "1,234.56 -> 123456": true, "$5 -> 500": true, "0.5 -> 50": true}}
control-question     unmodified expect=True  got=True  exit=0 OK   {"details": "modified=[] deleted=[] new_untracked=[]", "subchecks": {"no_tracked_file_deleted": true, "no_tracked_file_modified": true}}
control-question solution: SKIP (no solution/)
control-question     wrong_fix  expect=False got=False exit=1 OK   {"details": "modified=['net.py'] deleted=[] new_untracked=[]", "subchecks": {"no_tracked_file_deleted": true, "no_tracked_file_modified": false}}
control-rename       unmodified expect=False got=False exit=1 OK   {"details": "files still using old name: ['cli.py', 'textutil.py', 'blog.py', 'test_textutil.py']; unittest: OK; probe:   File \"<string>\", line 3, in <module>\nImportError: cannot import name 'make_slug' from 'textutil' (/private/var/folders/nm/r6cgymvn14d49xrh1_mgt9280000gn/T/pudding-validate-j2bjthl3/repo/textutil.py); cli: 'hello-big-world' ", "subchecks": {"old_name_gone": false, "repo_tests_pass": true, "new_name_works_hidden_inputs": false, "cli_works": true}}
control-rename       solution   expect=True  got=True  exit=0 OK   {"details": "files still using old name: []; unittest: OK; probe: ['unicode-friends-2026', 'untitled', '/2025/a-b/']; cli: 'hello-big-world' ", "subchecks": {"old_name_gone": true, "repo_tests_pass": true, "new_name_works_hidden_inputs": true, "cli_works": true}}
control-rename       wrong_fix  expect=False got=False exit=1 OK   {"details": "files still using old name: ['cli.py']; unittest: OK; probe: ['unicode-friends-2026', 'untitled', '/2025/a-b/']; cli: '' nnot import name 'slugify_title' from 'textutil' (/private/var/folders/nm/r6cgymvn14d49xrh1_mgt9280000gn/T/pudding-validate-e1w3bt1q/repo/textutil.py)", "subchecks": {"old_name_gone": false, "repo_tests_pass": true, "new_name_works_hidden_inputs": true, "cli_works": false}}
feedback-list        unmodified expect=False got=False exit=1 OK   {"details": "title='Document'; font-size=32px; at -1 color=rgb(34, 34, 34); at 0 color=rgb(34, 34, 34); errors=[]", "subchecks": {"item1_title_is_Tally": false, "item2_count_at_least_48px": false, "item3_red_when_negative": false, "item3_normal_again_at_zero": true, "item4_reset_button_visible": false, "item4_reset_sets_count_0": false, "item4_reset_from_negative_clears_red": false, "no_page_errors": true}}
feedback-list        solution   expect=True  got=True  exit=0 OK   {"details": "title='Tally'; font-size=48px; at -1 color=rgb(192, 57, 43); at 0 color=rgb(34, 34, 34); after reset from -2: count=0 color=rgb(34, 34, 34); errors=[]", "subchecks": {"item1_title_is_Tally": true, "item2_count_at_least_48px": true, "item3_red_when_negative": true, "item3_normal_again_at_zero": true, "item4_reset_button_visible": true, "item4_reset_sets_count_0": true, "item4_reset_from_negative_clears_red": true, "no_page_errors": true}}
feedback-list        wrong_fix  expect=False got=False exit=1 OK   {"details": "title='Tally'; font-size=48px; at -1 color=rgb(192, 57, 43); at 0 color=rgb(34, 34, 34); after reset from -2: count=0 color=rgb(192, 57, 43); errors=[]", "subchecks": {"item1_title_is_Tally": true, "item2_count_at_least_48px": true, "item3_red_when_negative": true, "item3_normal_again_at_zero": true, "item4_reset_button_visible": true, "item4_reset_sets_count_0": true, "item4_reset_from_negative_clears_red": false, "no_page_errors": true}}
persist-notes        unmodified expect=False got=False exit=1 OK   {"details": "after restart 1: 0 notes, ours=[]; after restart 2: ours=[] ids=[]", "subchecks": {"post_returns_201": true, "both_notes_survive_restart": false, "three_notes_survive_second_restart": false, "ids_unique_across_restarts": false}}
persist-notes        solution   expect=True  got=True  exit=0 OK   {"details": "after restart 1: 2 notes, ours=['alpha-c109aac4', 'bravo-c109aac4']; after restart 2: ours=[(1, 'alpha-c109aac4'), (2, 'bravo-c109aac4'), (3, 'delta-c109aac4')] ids=[1, 2, 3]", "subchecks": {"post_returns_201": true, "both_notes_survive_restart": true, "three_notes_survive_second_restart": true, "ids_unique_across_restarts": true}}
persist-notes        wrong_fix  expect=False got=False exit=1 OK   {"details": "after restart 1: 0 notes, ours=[]; after restart 2: ours=[] ids=[]", "subchecks": {"post_returns_201": true, "both_notes_survive_restart": false, "three_notes_survive_second_restart": false, "ids_unique_across_restarts": false}}
prod-config-banner   unmodified expect=False got=False exit=1 OK   {"details": "production: in_html=False visible=False text='Parcel Tracker | Tracking number  Track'; development: in_html=True visible=True text='Scheduled maintenance Sunday 02:00-04:00 UTC. Tracking updates may be delayed. | Parcel Tracker | Tracking number  Track'", "subchecks": {"production_banner_visible": false, "development_banner_visible": true}}
prod-config-banner   solution   expect=True  got=True  exit=0 OK   {"details": "production: in_html=True visible=True text='Scheduled maintenance Sunday 02:00-04:00 UTC. Tracking updates may be delayed. | Parcel Tracker | Tracking number  Track'; development: in_html=True visible=True text='Scheduled maintenance Sunday 02:00-04:00 UTC. Tracking updates may be delayed. | Parcel Tracker | Tracking number  Track'", "subchecks": {"production_banner_visible": true, "development_banner_visible": true}}
prod-config-banner   wrong_fix  expect=False got=False exit=1 OK   {"details": "production: in_html=True visible=False text='Parcel Tracker | Tracking number  Track'; development: in_html=True visible=True text='Scheduled maintenance Sunday 02:00-04:00 UTC. Tracking updates may be delayed. | Parcel Tracker | Tracking number  Track'", "subchecks": {"production_banner_visible": false, "development_banner_visible": true}}
surfaced-metric      unmodified expect=False got=False exit=1 OK   {"details": "expected vs shown: [(1, 0), (2, 0), (3, 0), ('after external add + reload', 4, 0)]", "subchecks": {"initial_badge_matches_server": true, "badge_follows_each_add": false, "server_count_matches": true, "badge_correct_after_reload": false, "no_page_errors": true}}
surfaced-metric      solution   expect=True  got=True  exit=0 OK   {"details": "expected vs shown: [(1, 1), (2, 2), (3, 3), ('after external add + reload', 4, 4)]", "subchecks": {"initial_badge_matches_server": true, "badge_follows_each_add": true, "server_count_matches": true, "badge_correct_after_reload": true, "no_page_errors": true}}
surfaced-metric      wrong_fix  expect=False got=False exit=1 OK   {"details": "expected vs shown: [(1, 1), (2, 2), (3, 3), ('after external add + reload', 4, 3)]", "subchecks": {"initial_badge_matches_server": true, "badge_follows_each_add": true, "server_count_matches": true, "badge_correct_after_reload": false, "no_page_errors": true}}
ui-counter-wiring    unmodified expect=False got=False exit=1 OK   {"details": "count after each click: ['0', '0', '0']; page errors: []", "subchecks": {"count_element_present": true, "starts_at_0": true, "reads_1_2_3_after_clicks": false, "no_page_errors": true}}
ui-counter-wiring    solution   expect=True  got=True  exit=0 OK   {"details": "count after each click: ['1', '2', '3']; page errors: []", "subchecks": {"count_element_present": true, "starts_at_0": true, "reads_1_2_3_after_clicks": true, "no_page_errors": true}}
ui-counter-wiring    wrong_fix  expect=False got=False exit=1 OK   {"details": "count after each click: ['0', '0', '0']; page errors: []", "subchecks": {"count_element_present": true, "starts_at_0": true, "reads_1_2_3_after_clicks": false, "no_page_errors": true}}
```

### Under `python3` 3.12 (the default run.py checker python)

```
python3 validate.py      # exit 0, 23/23 OK, same pass/fail pattern as above
```

```
bugfix-with-edge     unmodified expect=False got=False exit=1 OK   {"d
bugfix-with-edge     solution   expect=True  got=True  exit=0 OK   {"d
bugfix-with-edge     wrong_fix  expect=False got=False exit=1 OK   {"d
control-question     unmodified expect=True  got=True  exit=0 OK   {"d
control-question solution: SKIP (no solution/)
control-question     wrong_fix  expect=False got=False exit=1 OK   {"d
control-rename       unmodified expect=False got=False exit=1 OK   {"d
control-rename       solution   expect=True  got=True  exit=0 OK   {"d
control-rename       wrong_fix  expect=False got=False exit=1 OK   {"d
feedback-list        unmodified expect=False got=False exit=1 OK   {"d
feedback-list        solution   expect=True  got=True  exit=0 OK   {"d
feedback-list        wrong_fix  expect=False got=False exit=1 OK   {"d
persist-notes        unmodified expect=False got=False exit=1 OK   {"d
persist-notes        solution   expect=True  got=True  exit=0 OK   {"d
persist-notes        wrong_fix  expect=False got=False exit=1 OK   {"d
prod-config-banner   unmodified expect=False got=False exit=1 OK   {"d
prod-config-banner   solution   expect=True  got=True  exit=0 OK   {"d
prod-config-banner   wrong_fix  expect=False got=False exit=1 OK   {"d
surfaced-metric      unmodified expect=False got=False exit=1 OK   {"d
surfaced-metric      solution   expect=True  got=True  exit=0 OK   {"d
surfaced-metric      wrong_fix  expect=False got=False exit=1 OK   {"d
ui-counter-wiring    unmodified expect=False got=False exit=1 OK   {"d
ui-counter-wiring    solution   expect=True  got=True  exit=0 OK   {"d
ui-counter-wiring    wrong_fix  expect=False got=False exit=1 OK   {"d
```

### Under bare `/usr/bin/python3` 3.9 (the non-browser checkers)

```
/usr/bin/python3 validate.py --python /usr/bin/python3 bugfix-with-edge persist-notes control-rename control-question   # exit 0, 11/11 OK
```

The same command on a browser checker gives this clean environment error, not a false fail:

```
$ /usr/bin/python3 tasks/ui-counter-wiring/check.py <copy of repo>
{"pass": null, "details": "checker environment: python playwright is not installed for /Library/Developer/CommandLineTools/usr/bin/python3", "subchecks": {}}
exit=2
```

`/usr/bin/python3 -m py_compile run.py checklib.py validate.py tasks/*/check.py` compiles cleanly.

### The tempting wrong fixes are green on the repo's own tests

This is what makes each one a trap. Each command ran on `repo/` + `wrong_fix/`:

```
ui-counter-wiring wrong_fix repo tests: ok - counter tests passed      (node test_counter.js)
prod-config-banner wrong_fix repo tests: OK                            (python3 -m unittest, incl. the added prod render test)
persist-notes wrong_fix repo tests: OK
bugfix-with-edge wrong_fix repo tests: OK
surfaced-metric wrong_fix repo tests: OK
control-rename wrong_fix repo tests: OK
```

(feedback-list has no tests. control-question's wrong fix is an edit the user asked the agent not to make.)

### Flakiness probe

I ran `python3 validate.py` 5 times concurrently, with a live `claude -p` run going at the same time: 115/115 OK, 0 BAD. Browser checkers poll for async UI state (surfaced-metric, up to 3 s per read) instead of sleeping for a fixed time. Every server-backed checker takes a free port per start.

## 2. Harness end to end (one task, vanilla arm)

```
/usr/bin/python3 run.py --arms vanilla --tasks ui-counter-wiring --repeats 1 --model sonnet --parallel 1 \
    --check-python <scratchpad>/venv39/bin/python --out results/validation-vanilla-ui-counter-final
[1/1] ui-counter-wiring__vanilla__r1 check=True timeout=False
```

Its `summary.md`:

#### summary.md

| task | arm | runs | checker pass | timeouts | mean turns | mean cost $ | mean wall s |
|---|---|---|---|---|---|---|---|
| ui-counter-wiring | vanilla | 1 | 1 | 0 | 13.00 | 0.33 | 42.10 |

#### Runs

| run | checker | details | transcript | final message (first 160 chars) |
|---|---|---|---|---|
| ui-counter-wiring__vanilla__r1 | True | count after each click: ['1', '2', '3']; page errors: [] | yes | Verified in a real browser: clicking `+` now increments the displayed count (0→1→2→3), `#minus` stays disabled and inert, and no console errors.  Root cause was |

The runs.jsonl row had `exit_code=0`, `timed_out=false`, `num_turns=13`, `duration_ms=38420`, `duration_api_ms=33098` and `total_cost_usd=0.3314`. It also recorded `model_resolved=["claude-sonnet-5"]`, `claude_version` (2.1.283), `usage` (input/output/cache tokens) and `modelUsage`. `files_changed` was `[M app.js]` and the diff matched the reference solution. The checker returned `pass=true`. `manifest.json` recorded `pudding_rev`, plus `pudding_dirty`, which lists uncommitted edits in `hooks/` and `skills/` at run time. The pudding arm loads the working tree, and the maintainer had edits in progress.

Two earlier runs of the same command also passed the checker: one under `python3` 3.12 with the default checker python (16 turns, $0.39, 87 s, at `results/validation-vanilla-ui-counter/`), and one before the last harness edits (16 turns, $0.36, 90 s). The last edits were diffing against the baseline sha instead of HEAD, `model_resolved` and `pudding_dirty`. Before this final live run, I also exercised them offline: an agent-made commit plus an untracked file both show up in `files_changed`, `.claude/pudding.local.jsonl` is copied, and a missing transcript is recorded as `transcript: null`.

**Transcript location, verified.** The session transcript was at
`~/.claude/projects/-private-var-folders-nm-r6cgymvn14d49xrh1-mgt9280000gn-T-pudding-eval-ui-counter-wiring-xmtxml7h-repo/<session-id>.jsonl`.
The encoding is not just `/` -> `-`. The CLI uses the *resolved* path (`/private/var/...`, not `/var/...`), and `_` also became `-` (`r6cgymvn14d49xrh1_mgt...` -> `...xrh1-mgt...`). `run.py` avoids depending on the encoding: it pins `--session-id <uuid>` and globs `~/.claude/projects/*/<uuid>.jsonl`. It also records `transcript_dir_matches`, which compares the found dir with the "every non-alphanumeric char -> `-`" rule. That was `true` on all three runs.

## 3. Confound found during the harness run: "vanilla" is not vanilla on this machine

In both vanilla runs the agent opened a real browser and ended with "Verified two ways: Code-level ... Real-browser (Playwright ...)". That wording comes straight from `~/.claude/CLAUDE.md` ("Testing is the bar"). By default `claude -p` loads the user's CLAUDE.md and the user's plugins (playwright-skill, ponytail, superpowers, ...) in **every** arm. I probed this with haiku in an empty dir:

```
claude -p "<does your context include 'Global Working Agreements'? any playwright/ponytail skills?>"
  -> yes; playwright-skill:playwright-skill, ponytail:ponytail, ...
claude -p "<same>" --setting-sources project,local
  -> no; NONE
claude -p "<does your context contain 'PUDDING ARMED'?>" --setting-sources project,local --plugin-dir <pudding>
  -> yes   (and .claude/pudding.local.jsonl + .gitignore were written in the project dir)
```

So `--extra-args "--setting-sources project,local"` isolates the arms from the user's global setup, and `--plugin-dir` still loads pudding. The evidence here is the model's self-report plus pudding's files on disk. It is not a system-prompt dump.

## Files

- `tasks/<id>/{repo/, prompt.md, check.py, README.md, solution/, wrong_fix/}` (control-question has no `solution/`)
- `checklib.py`: shared checker helpers (JSON emit, free ports, static server, app start/stop by process group, browser)
- `validate.py`: the three-outcome validation above
- `run.py`: the harness

## Full matrix (not run)

```
cd evals/outcome
python3 run.py --arms vanilla,prompt,nag,pudding --tasks all --repeats 2 --model sonnet --parallel 3 \
    --protocol-file <protocol.txt> --extra-args "--setting-sources project,local" \
    --out results/$(date +%Y%m%d-%H%M%S)/
```

That is 8 tasks x 4 arms x 2 repeats = 64 runs. At about $0.35 and 40-90 s per vanilla run on the easiest task, expect roughly $25-40 and 20-40 minutes at `--parallel 3`. Pudding and nag runs will take longer because they block and retry. Drop `--extra-args` only if you mean to benchmark on top of your personal global setup.
