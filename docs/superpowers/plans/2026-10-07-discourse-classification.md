# Discourse classification implementation plan

Goal: implement the approved eight-label code-first graph classifier without verbose logging.

Architecture: Stanza spans and syntax feed deterministic relations and explicit/partial candidate retrieval. Bounded implicit relation resolution and evidence-validated LLM constraints precede comparative selection or recovery. Reuse the existing API client and evaluation.

Constraints: no classifier training; no fallacy attributes in graph; no gold in model payloads; exact evidence offsets; required FALSE rejects; test held out; default trace has decisions rather than prompts/API bodies.

- [x] Add behavioral tests for faithful spans, short motifs, rejected/uncertain constraints, evidence validation, selection, and article-disjoint train partition.
- [x] Implement parser, fixed discourse ontology, deterministic constructions, and bounded implicit pair resolution.
- [x] Implement eight explicit/partial retrieval patterns, constraint verification, comparison, and recovery.
- [x] Add config and CLI for coverage/classification/baselines, explicit input file selection, resume, compact traces and metrics.
- [x] Run focused and existing tests; install Stanza in the project environment; run real parsing and a small train API smoke test; document commands and limitations.

Verification: nine new behavioral tests including actual Stanza regressions; complete suite 182 tests. Two train API smoke samples exercised comparison and recovery without infrastructure errors; one matched gold and one differed. These smoke runs are integration evidence, not benchmark evaluation. Independent review identified segmentation and resume defects, now covered by regressions.
