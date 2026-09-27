# Detector v2 on held-out split 2

Detector frozen at `31e8d09`; split 2 frozen at `dab2ff5` (sha256 `8710ea34...`), written by a fresh
context that saw neither the detector nor splits 1 and dev. Scored exactly once.

```
split: test2  n=200  (95% Wilson intervals)

  precision    59/72   81.9%  [71.5- 89.1]   of what it flagged, how much was a real claim
  recall       59/90   65.6%  [55.3- 74.6]   of real claims, how many it caught
  false alarm  13/110  11.8%  [ 7.0- 19.2]   of non-claims, how many it wrongly flagged
  F1          0.728

  easy  recall  33/43   76.7%  [62.3- 86.8]   false alarm   1/57    1.8%  [ 0.3-  9.3]

  hard  recall  26/47   55.3%  [41.2- 68.6]   false alarm  12/53   22.6%  [13.5- 35.5]

  recall by family:
    bug-fixed       12/13
    real-user       7/10
    wire            5/10
    completeness    8/10
    no-break        7/9
    deployed        7/7
    generic         4/7
    metric          1/6
    installs-clean  3/5
    persisted       1/5
    faster          3/5
    design-match    1/3
```

History: v1 on split 1 had recall 56.7% (P 89.5%, FA 5.5%). v2 improves recall on unseen
text but gives up precision on hard negatives. Split 2 was written to be stylistically
wider (checkmark lists, status tables, emoji, one-word closers) than anything v2 was tuned on.
