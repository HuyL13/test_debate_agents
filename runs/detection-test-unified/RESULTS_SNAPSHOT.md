# Detection Results Snapshot

Snapshot date: 2026-09-21.

This is a partial run, not a completed 798-sample test evaluation.
`samples.csv` contains 16 completed samples: 12 correct, 2 false positives,
2 false negatives (TP=8, TN=4). Accuracy on this partial selection is 75%.
The audit may include calls for samples without a completed trace.
No full-test metric is claimed.

Related saved-report replays in this commit:

- `../adjudication-fix-replay`: both 427:10577 and 427:10579 remain false positives.
  The audit includes earlier sandbox connection failures as well as real API calls.
- `../adjudication-perspectives-replay`: both remain false positives after changing
  the final-call payload and ordering. These are final-call replays of saved reports,
  not new runs of all three analysts.
- `../adjudication-grounded-replay`: all three attempts on 427:10577 timed out.
  There is no valid prediction; 427:10579 was not reached.

The artifacts were produced during local, uncommitted prompt/schema experiments.
The branch's committed source is not an exact reproduction of every replay variant.
The experimental source edits are intentionally outside this results-only commit.
Neither the replays nor these 16 samples establish improvement on the full benchmark.
