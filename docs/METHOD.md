# Method

The system implements Conflict-Guided Multi-Agent Fallacy Reasoning for CoCoLoFa.

The analytical roles operationalize established operations from argumentation theory: argument-scheme analysis, enthymematic reconstruction, and critical-question-based evaluation. The conflict-guided interaction topology is the system design.

## Flow

1. `scheme` checks whether TARGET directly supports a fallacy structure.
2. `enthymeme` identifies any required hidden assumption and whether the text licenses it.
3. `critical` tests whether the candidate's mandatory condition is actually met.
4. `conflicts.build_conflicts` deterministically detects candidate disagreement or structural contradictions.
5. Targeted resolvers compare only the conflicting candidates.
6. `arbiter` emits the final task label.

The raw TARGET text is authoritative. TITLE and immediate parent are context only. Evidence spans must be substrings of TARGET.

## Trace

Per-sample traces are YAML files with sample metadata, input text, initial analysis, conflicts, arbiter output, and call/token/time stats. There is no post-hoc pretty trace.
