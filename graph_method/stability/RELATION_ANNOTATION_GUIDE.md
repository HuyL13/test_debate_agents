# Source graph review protocol

Review the original comment before viewing its fallacy label or proposed edges.
Keep independent first readings; adjudicate disagreements explicitly. Store
source/graph hash, reviewer identity/type, unresolved readings and corrections.
Expert human reviews and assistant silver annotations are separate data tiers.

1. **Literal content.** Copy source spans without normalizing spelling,
   negation, quantifiers or modal words. Separate a clause from its evaluation
   when meaningful. A valid substring can still be an incomplete proposition.
2. **Speaker and stance.** Identify whose content is represented. `uses` means
   the current author relies on this particular inference. Criticism of an
   organization or a negative conclusion does not make the author's own
   supporting inference `critiques`. A quoted inference can instead be reported
   or challenged. Parent/title text is not automatically adopted.
3. **Support.** Record an offered reason for a distinct target, including
   implicit discourse relations. An explicit because/therefore marker is useful
   but not required. Mere shared topic, compatibility, entailment that the
   reviewer invents, repetition and adjacent sentences are insufficient.
   Explain the actual source's reason–claim reading and its competing reading.
4. **Direction.** Re-read in basis→claim order. Reversing a rhetorical question
   and its motivating reason can change the argument. Do not add both directions
   because two statements reinforce the same position. Each requires its own
   source witness. Application-target attacks must identify the actual warrant.
5. **Concession.** A granted point despite a conclusion is not a supporting
   premise for that conclusion. Contrast alone does not imply binary choices.
6. **Projection.** Identify initiating action/condition and actual predicted
   effect, preserving hypothetical status and modal scope. A metacomment,
   approval, recommendation or current trust assessment is not automatically a
   projected world event. Distinguish negation of the causal link from a
   negative outcome. Dependency frames only license candidates.
7. **Choices.** Preserve literal options, restriction cues, rejected restriction
   and additional proposals separately. An option list is not a preference.
   A closed set is not necessarily a false dilemma. Do not fabricate a support
   edge between two restatements of the same choice constraint.
8. **Warrant roles.** Test the source's actual acceptance basis: expertise,
   popularity, longevity, naturalness, relative severity, sample extension,
   constrained alternatives or projected consequences. Mentioning a dentist
   alone is not historical practice, and expertise alone is not misuse.
   Keep uncertain scheme typing separate from a supported reason–claim link.
9. **Coverage.** Review at least the central reasoning independently of the
   proposed graph. A graph emptied by rejection does not pass semantic quality.
   Unresolved central relations remain a failed coverage item.
10. **Pattern admission.** Approve a TRAIN snapshot only after source relations,
    central coverage, speaker/stance, negation/modality and warrant roles are
    reviewed. Do not change the source graph to fit its class label. Freeze
    reviewed graphs before pattern mining and evaluate on disjoint articles.

This protocol makes judgments traceable and the stored training bank repeatable;
it does not guarantee that reviewers never make semantic errors. A supervised
parser trained on these relation annotations is the route to more automation.
No such parser was fine-tuned in this experiment.
