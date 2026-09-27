#!/usr/bin/env python3
"""Precision and recall of pudding's claim detector on the independent labeled splits.

    python3 evals/claims/eval.py dev            # the split used for tuning
    python3 evals/claims/eval.py test           # the frozen split; the reported numbers
    python3 evals/claims/eval.py test --errors  # every miss and false alarm, for reading

"Detected" means exactly what the gate treats as a claim: a claim sentence, or a
completeness claim (including a Done list beside a Not-done list).
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "hooks"))
from claims import claims_completeness, detect  # noqa: E402


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def predict(msg):
    return bool(detect(msg)) or claims_completeness(msg)


def rate(k, n):
    lo, hi = wilson(k, n)
    return f"{k:>3}/{n:<3} {100*k/n if n else 0:5.1f}%  [{100*lo:4.1f}-{100*hi:5.1f}]"


def evaluate(rows):
    c = Counter()
    for r in rows:
        p, y = predict(r["message"]), r["claim"]
        c[("tp" if y else "fp") if p else ("fn" if y else "tn")] += 1
    return c


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    rows = [json.loads(line) for line in (HERE / f"{split}.jsonl").read_text().splitlines() if line.strip()]
    c = evaluate(rows)
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    print(f"split: {split}  n={len(rows)}  (95% Wilson intervals)\n")
    print(f"  precision   {rate(tp, tp + fp)}   of what it flagged, how much was a real claim")
    print(f"  recall      {rate(tp, tp + fn)}   of real claims, how many it caught")
    print(f"  false alarm {rate(fp, fp + tn)}   of non-claims, how many it wrongly flagged")
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0
    print(f"  F1          {f1:.3f}")
    for diff in ("easy", "hard"):
        sub = [r for r in rows if r["difficulty"] == diff]
        s = evaluate(sub)
        print(f"\n  {diff:<5} recall {rate(s['tp'], s['tp'] + s['fn'])}   false alarm {rate(s['fp'], s['fp'] + s['tn'])}")
    print("\n  recall by family:")
    fams = Counter(r["family"] for r in rows if r["claim"])
    for fam, n in sorted(fams.items(), key=lambda kv: -kv[1]):
        k = sum(1 for r in rows if r["claim"] and r["family"] == fam and predict(r["message"]))
        print(f"    {fam:<15} {k}/{n}")
    if "--errors" in sys.argv:
        for kind, want_label, want_pred in (("MISSED", True, False), ("FALSE ALARM", False, True)):
            print(f"\n=== {kind} ===")
            for r in rows:
                if r["claim"] == want_label and predict(r["message"]) == want_pred:
                    one = " ".join(r["message"].split())[:170]
                    print(f"  {r['id']} [{r['family']}/{r['difficulty']}] {one}")


if __name__ == "__main__":
    main()
