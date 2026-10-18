# Literature survey for the graph semantic-fidelity bottleneck

Survey date: 2026-10-17. Sources below are original papers or official proceedings. Proposed applications are our adaptations, not published CoCoLoFa results. No cited paper establishes zero semantic errors.

This is a targeted methodological survey, not a systematic meta-analysis or a reproduction. Relevant PDF passages were inspected for AIF, scheme understanding, relation mining, controlled-language parsing and CoVe. DCCD is summarized from its official proceedings abstract because the linked PDF could not be fetched and OpenReview presented a browser challenge; its complete implementation has not been reviewed. The remaining summaries rely on the original abstracts and clearly stated task/method descriptions.

## Diagnosis against our evidence

V12 passed 28 synthetic controls but failed real-source audit; V13 split role mapping and scheme assignment but still confused causality, generalization and rejected choices. Relaxing JSON schema did not fix the hard cases. Increasing reasoning budget helped some cases, not all. Existing verifier selects the gold label in 39/40 development examples where retrieval contains it; overall 39/80. Thus source-grounded extraction and candidate coverage deserve priority.

There is also a representational issue: a rebuttal to a warrant, a negative claim and an open alternative proposal are not the same object. Our single stance/alternatives tuple can make equivalent readings look inconsistent, and can conflate an author's actual argument with the argument being rejected. A policy recommendation is not a projected harmful event. These distinctions require explicit ontology and evaluation rules, not merely longer prompts.

## 1. Argument Interchange Format — Knowledge Engineering Review, 2006

[Chesñevar et al., Towards an argument interchange format](https://jmvidal.cse.sc.edu/library/chesnevar06a.pdf).

AIF distinguishes information nodes and applications of inference, conflict and preference schemes. Its relation semantics also permit attacks on inference applications, not only on propositions.

Application: retain immutable source spans, but distinguish an endorsed inference from a conflict targeting a proposed warrant. A rejection of popularity as justification should not be encoded as popularity positively supporting the author's negative sentence. Add provenance and explicit versus inferred status to any reconstructed target; never turn an inferred target into an author assertion. AIF supplies a representation foundation, not an automatic accurate parser.

## 2. Argument scheme understanding — Findings of ACL, 2025

[Bezou-Vrakatseli et al., Can Large Language Models Understand Argument Schemes?](https://aclanthology.org/2025.findings-acl.702/).

The paper evaluates zero-shot, few-shot, chain-of-thought and enhanced scheme instructions. Few-shot demonstrations help more consistently than elaborate definitions; additional reasoning does not uniformly improve performance. Real arguments are harder than generated arguments. Cause-to-effect, consequences and example schemes are particularly confusable; source-based arguments can embed other schemes. Their structured intermediate classification prompts did not provide meaningful improvements in the tested setup.

Application: stop treating our perfect synthetic controls as sufficient. Compare concise demonstrations with our lengthy instruction accumulation. Preserve embedded warrants rather than assuming one globally correct category. Test on held-out real articles and evaluate local relation grounding separately from scheme naming. This paper supports experimentation, not a guarantee that critical-question prompting alone will solve our task.

## 3. Relation-based argument mining — COLING, 2025

[Can Large Language Models perform Relation-based Argument Mining?](https://aclanthology.org/2025.coling-main.569/).

The method classifies argument pairs as support, attack or neither, with fixed few-shot examples and controlled prompt configurations. It evaluates across multiple argument datasets; argument relation classification is distinct from stance toward a topic.

Application: generate plausible local relation candidates, then independently classify each as source-supported, challenged, unrelated or unresolved. Include negative and reversed-pair examples. Do not force every nearby pair into an edge. Their pairwise task does not automatically solve multi-premise extraction or joint graph coherence; our counterexample cases require grouped premises and source context.

## 4. Draft-conditioned constrained decoding — ICML, 2026

[Reddy et al., The Hidden Cost of Structured Generation in LLMs](https://proceedings.mlr.press/v306/reddy26a.html).

DCCD first generates an unconstrained draft, then performs constrained generation conditioned on it. The paper analyzes how enforcing output validity during generation can redirect the model toward semantically poor continuations, and reports improvements on structured reasoning benchmarks.

Application: produce a concise natural-language annotation of source argument links before compiling the graph into the strict ontology. V13 is not this experiment: it constrained the role-mapping stage too. Hold source units, final schema and extraction settings fixed when comparing. The draft remains fallible; the source is authoritative. These results are on other benchmarks, so improvement on our graph task must be measured.

## 5. Controlled-language semantic parsing — EMNLP, 2021

[Shin et al., Constrained Language Models Yield Few-Shot Semantic Parsers](https://aclanthology.org/2021.emnlp-main.608/).

The method maps natural input into a controlled English-like representation that can be converted mechanically into a formal meaning representation, with constrained generation and few-shot examples.

Application: a small source-anchored intermediate language can separate semantic annotation from graph serialization. For example, explicitly identify who offers which reason, which claim is targeted, and whether the link is adopted or rejected; let code assign IDs and construct edges. Unlike unrestricted paraphrasing, controlled forms need a deterministic grammar and preserved scope. The method cannot ensure the annotation itself correctly reflects the source.

## 6. Independent verification — Findings of ACL, 2024

[Dhuliawala et al., Chain-of-Verification Reduces Hallucination in Large Language Models](https://aclanthology.org/2024.findings-acl.212/).

CoVe drafts an answer, plans verification questions, answers them independently and revises the response. Factored verification separates questions from the draft to reduce repetition of its errors.

Application: verify source ownership, qualification, offered relation, choice restriction and event roles using source evidence without exposing the initial scheme guess or explanation. Questions should check factual obligations, not ask whether the guessed label is correct. Then compile only supported properties, preserving unresolved hypotheses. This is an adaptation from factual generation; checking source fidelity is not the same as checking whether an argument is logically valid.

## 7. Limits of intrinsic correction — ICLR, 2024

[Huang et al., Large Language Models Cannot Self-Correct Reasoning Yet](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html).

The paper reports that intrinsic self-correction without external feedback can fail and sometimes degrade reasoning performance.

Application: a second prompt saying “review and fix” is not an independent correctness certificate. Combine immutable-source checks, formal invariants, independently answered questions, counterexamples and manual audit. Repeated model agreement is evidence of consistency, not proof of truth. Source-grounded evidence is useful feedback, but this alone does not remove correlated errors when the same model performs every stage.

## 8. Atomic evaluation — EMNLP, 2023

[Min et al., FActScore](https://aclanthology.org/2023.emnlp-main.741/).

FActScore decomposes generated text into atomic factual claims and assesses their support against a reliable knowledge source, instead of assigning one undifferentiated correctness judgment to the whole response.

Application: evaluate graph assertions separately: exact span, speaker, relation direction, stance, modality, scope expansion and projected-event membership. Also measure missed central links; precision alone can reward empty graphs. Our knowledge source is the original comment/context. Verify that the author made the argument, not that its conclusion is true in the world. This is an evaluation adaptation, not a direct reuse of their biography factuality metric.

## 9. Supervised argument mining — COLING, 2025

[Argument Mining with Fine-Tuned Large Language Models](https://aclanthology.org/2025.coling-main.442/).

The paper treats component classification, relation identification and relation classification, including joint formulations, as generation tasks and fine-tunes language models on argument-annotated datasets.

Application: if prompting and verification plateau, a graph parser trained on actual component/relation annotations is a substantive alternative to indefinitely extending prompts. Our fallacy labels are not gold premise, relation or event-role annotations. Any new training set must distinguish expert-gold data from agent-audited or model-generated silver data and validate it on independent articles. This is a longer-term branch; we have not fine-tuned a parser or reproduced these results.

## Experiments selected from the survey

1. Draft-conditioned compilation versus direct constrained extraction, on identical real source units and unchanged final schema. Record draft and compiler output separately.
2. Concise contrastive demonstrations versus instruction accumulation. Include source observations versus external testimony, causal consequences versus sample generalization, and rejected restrictions versus endorsed closed choices.
3. Independent source-question verification. Measure supported relation/attribute precision, central-link coverage and semantic change under repeated calls. Reject a method that obtains precision by deleting difficult arguments.
4. Introduce explicit conflict-on-warrant and projected-event roles where the present ontology conflates them. Preserve unresolved readings and their evidence; do not silently overwrite an author's qualification or import parent claims.
5. Calibrate atomic source-fidelity checks on matched positive and negative real-source hypotheses before using them to accept graph assertions. A long independent answer can still invent content, so independence alone is not a correctness certificate.

Start with the eight diagnosed real cases, then fresh article-disjoint train cases before another bulk run. Existing examples used to shape prompts are development/regression evidence, not fresh validation. No test tuning. Full pattern recovery and end-to-end usefulness remain required after extraction improves. Do not claim any approach eliminates all semantic errors.

## Experimental evidence from these adaptations

- Contrastive few-shot, free-draft compilation and independently checked draft compilation each produced valid final JSON on8/8diagnosed cases. All three retain semantic or coverage problems. These are not acceptance passes.
- The checked-draft variant corrected the blocking-warning event pair to units3→6 and kept the free-speech recommendation separate. It still produced an unsupported testimonial type for a company/profit argument and a projected edge to a disagreement statement.
- Atomic source-fidelity verification scored16/16onbalanced positive/negative regression hypotheses about the real failures. A faster configuration initially had one empty-evidence contract failure and one transport failure; an evidence-constrained schema then completed16/16correct with no model-output contract rejections. Initial transport errors remain in the records. These controls do not establish generalization to new graph assertions.
- A guard is now testing66atomic hypotheses covering20proposed relations across the eight real graphs. It keeps rejected or unresolved properties explicit, preserves supported relations when a scheme is uncertain, and prevents unsupported projected links from entering the checked graph. Source audit, coverage and repetition are still required before adopting it for train-pattern induction.

## Final decision round: structured candidates instead of unconstrained edge generation

[AMR-based event argument link prediction, ACL 2023](https://aclanthology.org/2023.acl-long.720/) uses a tailored, span-integrated graph and predicts event-argument links. We adopt the principle of source-anchored event candidates, not its trained TAG model or published scores. Dependency parsing is weaker than AMR and is NOT an event-semantics oracle.

[Argument pair extraction, ACL 2021](https://aclanthology.org/2021.acl-long.496/) formulates pair prediction through a table-filling view. Our adaptation separates candidate endpoints from relation decisions, including negative/unclear decisions. It does not establish that exhaustive pair tables or LLM adjudication will generalize on CoCoLoFa.

[Structured SVM/RNN argument mining](https://arxiv.org/abs/1704.06869) jointly models component types and relations without assuming every argument graph is a tree. Our contract likewise allows multiple independent reasons and application-target attacks; no forced tree or union of unrelated prototype paths.

[Fine-tuned LLM argument mining, COLING 2025](https://aclanthology.org/2025.coling-main.442/) trains component/relation tasks on PE, AbstRCT and CDCP. This is the evidence-backed alternative if prompting plateaus: supervise the actual extraction task with component/relation annotations. CoCoLoFa class labels alone are not such annotations; neither automatic verifier agreement nor assistant silver references should be called expert gold.

The final selection must distinguish architectural choice from passed performance gates. If frozen fresh-source/repeat/usefulness gates fail, reject unsupervised automatic pattern induction as a stable solution. Retain exact-source ontology, typed candidates, witnessed alternative prototypes and comparative verification; use reviewed train annotations for the pattern bank rather than propagating unchecked LLM edges.
