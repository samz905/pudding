# Addendum - pudding v5 arm

Written and committed before any run of this arm, while the pre-registered matrix
(`PREREGISTRATION.md`, commit `2f7251b`) was still running and before any of its
results had been graded or analysed.

## Why

While the matrix ran, three held-out detector evaluations put the claim detector's
recall on unseen phrasing near 65% (`evals/claims/results/`), and a blind-labeled
sample of real messages put it lower. Separately, the matrix surfaced a false block
on the `control-question` task, traced to pudding counting its own `.gitignore`
write as a code change. v5 changes the gate so that evidence is owed whenever the
session changed code and the agent reports back, whether or not the detector
recognises a claim, and stops counting pudding's own files as code changes.

## Arm

`pudding-v5`: the pudding plugin at the commit containing this file, run with the
same runner, tasks, checkers, model (Sonnet), flags (`--setting-sources
project,local`), 3 repeats, 15-minute limit, grader and analysis as the main matrix.

## Hypotheses

- H4: pudding-v5's false-success rate on trap tasks is no higher than the
  pre-registered pudding arm's.
- H5 (cost): on `control-question`, pudding-v5 blocks 0 runs (the fix). On
  `control-rename`, where code changes and there is nothing to find, report runs
  with a block and blocks per run as the cost of the new rule.

## Known confound, disclosed

This arm runs after the matrix rather than interleaved with it, so any drift over
the afternoon (API latency, model serving) is confounded with the arm. It is run
only after the matrix finishes so that the two runners never share ports.

## Analysis change

`analyze.py` reports whichever arms appear in the data, in the pre-registered order
followed by `pudding-v5`. No definition or metric changes.
