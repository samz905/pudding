# Detector v1 on the frozen test split

Detector frozen at commit `64ee7d9`, test split frozen at `0bc3d41` (sha256 `e8b1f573...`).
Scored exactly once. Tuning after this point used this split as training material,
so these numbers can no longer improve - a new held-out split carries the next result.

```
split: test  n=200  (95% Wilson intervals)

  precision    51/57   89.5%  [78.9- 95.1]   of what it flagged, how much was a real claim
  recall       51/90   56.7%  [46.4- 66.4]   of real claims, how many it caught
  false alarm   6/110   5.5%  [ 2.5- 11.4]   of non-claims, how many it wrongly flagged
  F1          0.694

  easy  recall  31/44   70.5%  [55.8- 81.8]   false alarm   0/56    0.0%  [ 0.0-  6.4]

  hard  recall  20/46   43.5%  [30.2- 57.8]   false alarm   6/54   11.1%  [ 5.2- 22.2]

  recall by family:
    bug-fixed       8/9
    completeness    6/9
    generic         7/9
    deployed        4/8
    no-break        6/8
    installs-clean  5/8
    real-user       2/7
    metric          2/7
    faster          3/7
    persisted       1/7
    wire            4/6
    design-match    3/5
```

Dev split at the same commit: precision 95.6%, recall 95.6%, false alarms 3.7%.
The 39-point recall gap between dev and test is the overfitting the freeze exists to expose.
