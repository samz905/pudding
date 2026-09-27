# The detector on real end-of-turn messages

Synthetic splits can flatter a detector, so it was also measured on the maintainer's
own Claude Code transcripts. The messages are private and are not published; the
method and the aggregates are.

## Method

End-of-turn messages only (`stop_reason: end_turn`), since that is what the gate
reads. A stratified random sample: 60 messages the detector flagged and 60 it did
not, shuffled, handed to a separate model context that labeled them with the same
definitions as the synthetic splits and never saw which were flagged. Estimates are
reweighted to the population from each stratum's sampling rate.

## Round 1 - detector v2, all projects (sample then used for tuning)

| kind of work | messages | precision | recall |
|---|---|---|---|
| software and content | 63 | 76% | 52% |
| grading other people's task submissions | 57 | 20% | 33% |

The grading work - reviewing someone else's submissions - is not what pudding is for
and produces most of the false alarms ("byte-identical to Task 19", "Approve - 4").
This sample exposed a real bug: agents bold their verdicts ("**Fixed and live.**") and
the markdown hid every sentence-initial pattern. Fixed in v4. Having been read, this
sample stopped being a test.

## Round 2 - detector v4, software and content sessions, fresh sample

A new stratified sample of 120 messages none of which had been read before, drawn
after v4 was frozen.

| | |
|---|---|
| precision | **78%** (47 of 60 flagged were real claims; 95% CI 66-87%) |
| recall | **about 67%** (estimated 603 of 898 real claims in 1,507 turns) |

This agrees with the synthetic held-out plateau (84% precision, 64% recall on split 3).
About a third of real claims are phrased in ways a lexical detector doesn't catch,
which is why the gate no longer depends on the detector to decide *whether* evidence
is owed after real work - only *what kind*.
