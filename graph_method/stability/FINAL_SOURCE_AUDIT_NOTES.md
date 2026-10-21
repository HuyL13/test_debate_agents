# Final source audit notes ? reserved TRAIN, frozen configuration

These are assistant source observations, not expert-human precision gold. No
prompt or source parser was tuned on these sixteen articles.

All16 requests completed. Source graphs14/16 contract-valid; two source relation
stages failed their validators. Three accepted graphs contain no applications.
The source-only reviewer admitted24/60 proposed applications. Admission is not
correctness: one predeclared definite reversed-direction control still survived.

Concrete observed failures:

- 376,613,567: empty argument graphs despite explicit expertise, voting or
  naturalness-based reasoning. Valid empty JSON does not satisfy coverage.
- 56: an accepted target is the fragment `But maybe this is`; source review
  admitted an edge to it. Literal quote alignment does not ensure a proposition.
- 582: the proposal reverses the ancestors/history-books reasoning and introduces
  projections from an article clearing up the issue to ancestors communicating.
  The source reviewer accepted several of these. A parser-licensed initial and
  an accepted reviewer verdict do not establish the actual relation.
- 88: the author relies on reasons to dismiss an issue, but the extractor marks
  those supporting inferences critiques. Criticizing a topic is not rejecting
  one's own offered inference. The reviewer rejected the edges rather than
  recovering the central reasoning.
- 482: dense, largely unsupported support edges; source review rejects all16.
  This reduces contamination while retaining no central coverage.
- 637: a recommendation to intervene is linked to deaths as a cause, while the
  source predicts harm under non-intervention. Review rejects the proposed
  links. The initiating condition's negation must be represented explicitly.
- 426: accepted hoarding?prior suspicion direction fails to resolve the source's
  actual `so this would make the most sense` reasoning adequately.
- 578,194: source relation outputs rejected; never counted as semantic successes.

The predeclared exact reference audit matches1/16 positive controls, before and
after source review. This is strict endpoint/arity/span coverage, not semantic
accuracy: split clauses and jointly represented premises can differ from the
assistant reference. It is reported without upgrading near matches or using it
as exhaustive precision. Manual failures above independently establish rejection
of unattended automatic graph induction.

No test split was read. Critical/fresh articles are disjoint. Source-code hashes
match the pre-audit freeze. Expert TRAIN graph approvals and a measured eight-label
pattern bank have not been produced; neither is claimed by the architectural
selection.
