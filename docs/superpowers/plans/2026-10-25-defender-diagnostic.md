# Defender diagnostic revision implementation plan

**Goal:** Implement the user-approved Defender example without changing Prosecutor or Arbiter.

**Design:** Keep the four-field Defender schema. Replace keyword vetoes and distinct-quote requirements with advisory diagnostics. Preserve the submitted report and explanation. Reconstruct the argument, compare candidate with runner-up, then consider other labels using the same standard. No blind second LLM call in this revision.

**Execution:** Work in the current feature checkout; the user requested a directly testable change. No commits or paid inference are required.

- [x] Add regression tests for the priority-comparison example, shared quotes, malformed evidence, concessions, and pipeline audit records; observe failures.
- [x] Revise classification Defender normalization and prompt only; leave Prosecutor calls/prompts and Arbiter calls/prompts/policies unchanged.
- [x] Add separate experiment configs and document commands, audit fields, and comparison limitations.
- [x] Run targeted tests, full pytest and review diff.

**Review focus:** Quotes outside target remain invalid; regex misses and short quotes do not imply agreement; same-label normalization preserves reasoning; detection remains unchanged; experiment outputs do not overwrite baseline. New runs do not guarantee identical Prosecutor responses because the existing cache includes experiment identity.

Verification: baseline 145 tests passed; seven new regressions failed before implementation and passed afterward. Full updated suite verification recorded in the task response. No paid benchmark or mock runner invocation was performed; scripted engine tests cover pipeline execution.
