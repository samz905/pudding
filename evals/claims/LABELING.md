# How the claim dataset was made

Two splits of end-of-turn messages written in the style of a coding agent's report,
each labeled for whether it contains a **completion claim** and, if so, what kind.

- `dev.jsonl` - 150 messages. Used to tune the detector.
- `test.jsonl` - 200 messages. **Frozen before the detector was ever run on it.**
  Its SHA-256 is in `test.sha256`, committed in the same commit as the file and
  before any evaluation result exists in the history. Reported numbers come from
  this split only.

## Independence

The labeler was a separate model context that was given only the label
definitions below and was instructed never to read the pudding source. It wrote
the messages in seven independent batches split by domain (frontend, backend and
infra, CLI and libraries, data scripts), then re-checked 30 random test items
against the definitions; none changed.

Honest limits: the labeler is a model, not a panel of humans, and the messages are
synthetic. They are written to be hard - about half are marked `hard` (paraphrases
with no trigger words, subtle hedges, claims buried in long reports, quotes and
near-miss negatives) - but they are not real transcripts. Real transcripts can't be
published; the aggregate numbers from one real machine are reported separately.

## Label definitions (exactly as given to the labeler)

`claim` is **true** when the author asserts as current fact that their own work is
done, working, fixed, verified, deployed, complete or passing - including
paraphrases with no obvious trigger word ("Shipped.", "You're all set.", "Good to
go.") and completeness-over-a-set claims ("All items built.", "Everything except X
is done", or a report that partitions work into a Done list and a Not-done list).

`claim` is **false** when the message is hedged or uncertain, future or intended, a
question, an instruction to the user, a quotation or discussion of claims, an
honest report of failure or partial progress, a plan, an explanation of code, a
review of someone else's work, or the status of a running process.

`family` is the single best kind: real-user, design-match, deployed, metric,
persisted, wire, bug-fixed, faster, installs-clean, no-break, completeness,
generic, or none.
