# Latest graph experiment: 2026-10-20

These are local experimental results, not expert-reviewed graph gold. Raw calls,
licensed source data, generated graphs and large HTML reports remain local.

- TRAIN: 3,168 source-contract-valid graphs after roundtrip, targeted retry and
  span repair. Eighteen contain no inference applications.
- Automatic silver bank: 70 tentative and 49 stable strict/core patterns across
  eight labels; 2,658 witnesses revalidated. Minimum distinct articles 5, purity
  0.45, bootstrap recovery 0.8 over 30 rounds. Stability is structural, not a
  semantic correctness guarantee.
- Frozen TEST: 481/481 completed; 475 source-contract-valid graphs; 183 samples
  have a gold-label candidate (38.05%); 259 have no candidate. Accuracy 160/481
  (33.26%), macro-F1 0.4192, counting missing and rejected predictions as errors.
  TRAIN/TEST article overlap is zero in the saved freeze.
- Selection statuses: confirmed 185 (151 gold-correct), quality_rejected 20,
  weak_candidate 5 (4 correct), forced_candidate 12 (5 correct), no_candidate 259.
  Reported accuracy uses the legacy ranking prediction, including weak and forced
  candidates, rather than the separate selective author-fallacy decision.
- Only nine TEST graphs have no applications. Thus no-candidate failures are
  mostly not empty-graph failures. Exact motif matching and source relation/role
  errors both limit candidate recall; their individual shares are not measured.
- Observed cases: 427:6677 omits the central authority inference; 5:3011 maps a
  dangerous precedent to historical practice and confirms Tradition instead of
  Slippery Slope; 146:3884 maps severity-based dismissal to closed alternatives
  and confirms False Dilemma instead of Worse Problems.
- Raw verifier calls for 347:6439 were rejected twice for the brief-reason
  contract; 599:8995 was rejected for brief reason and then output length.
  Contract rejection is distinct from a demonstrated semantic error.
- Direct TRAIN retrieval corrected 6/12 selected previously incorrect exposed
  TEST cases. This is diagnostic evidence only, not independent generalization.

Evidence filenames in the local stability directory:
`full_train_span_fixed_r1_graphs.json`,
`full_train_silver_multires_patterns_r1_metrics.json`,
`test_multires_oss120b_r1_results.json`,
`test_multires_oss120b_r1_metrics.json`,
`test_multires_oss120b_r1_freeze.json`,
`direct_train_graph_diagnostic_r1_metrics.json`.

The primary limitation is semantic source-graph coverage combined with brittle
candidate retrieval. Valid source spans, repeated LLM agreement, witnessed motifs
and bootstrap recovery do not certify correct argument semantics. Reviewed TRAIN
admission remains required for an expert-tier bank.
