# Detectors v3 and v4 on held-out split 3

Split 3 frozen at `f251614` (sha256 `638e19d8...`) after v3 (`66fd8f4`) and v4 (`6fc5f6c`) were
frozen. Each scored exactly once.

```
=== v3 (66fd8f4) on held-out split 3
split: test3  n=200  (95% Wilson intervals)

  precision    58/69   84.1%  [73.7- 90.9]   of what it flagged, how much was a real claim
  recall       58/90   64.4%  [54.1- 73.6]   of real claims, how many it caught
  false alarm  11/110  10.0%  [ 5.7- 17.0]   of non-claims, how many it wrongly flagged
  F1          0.730

  easy  recall  33/51   64.7%  [51.0- 76.4]   false alarm   2/40    5.0%  [ 1.4- 16.5]

  hard  recall  25/39   64.1%  [48.4- 77.3]   false alarm   9/70   12.9%  [ 6.9- 22.7]

  recall by family:
=== v4 (6fc5f6c) on held-out split 3
split: test3  n=200  (95% Wilson intervals)

  precision    58/69   84.1%  [73.7- 90.9]   of what it flagged, how much was a real claim
  recall       58/90   64.4%  [54.1- 73.6]   of real claims, how many it caught
  false alarm  11/110  10.0%  [ 5.7- 17.0]   of non-claims, how many it wrongly flagged
  F1          0.730

  easy  recall  33/51   64.7%  [51.0- 76.4]   false alarm   2/40    5.0%  [ 1.4- 16.5]

  hard  recall  25/39   64.1%  [48.4- 77.3]   false alarm   9/70   12.9%  [ 6.9- 22.7]

  recall by family:
```

## Across all held-out measurements

| detector | held-out split | precision | recall | false alarm |
|---|---|---|---|---|
| v1 | 1 | 89.5% | 56.7% | 5.5% |
| v2 | 2 | 81.9% | 65.6% | 11.8% |
| v3 | 3 | 84.1% | 64.4% | 10.0% |
| v4 | 3 | 84.1% | 64.4% | 10.0% |

Every round lifted the scores on text the detector had been tuned on (dev recall 97%) and
left held-out recall near 65%. That plateau is the honest capability of a lexical detector on
phrasing it has not seen. v4's changes came from real transcripts (markdown-bolded verdicts,
adverbs, commits) and do not move this synthetic split - they are measured on real messages instead.
