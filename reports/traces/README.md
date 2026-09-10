# Trace index

This directory is intentionally trimmed to the newest retained trace summaries.
Older per-sample trace exports were removed from `reports/traces` to avoid
mixing legacy planner/debate runs with the current diagnostic-debate work.

Retained legacy summaries:

- `nvidia-detection-adaptive-dev10-v4.md`
- `nvidia-classification-adaptive-dev10-v3.md`

Raw run artifacts, manifests and checkpoints remain under `outputs/` for runs
that have not been explicitly deleted. New Diagnostic Debate V1 runs should use
fresh output directories and, when exported for reading, add only the latest
versioned trace summaries here.
