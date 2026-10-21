# Official fallacy dataset snapshots

Full snapshots of the upstream `data/` directories, including original splits,
raw files, auxiliary variants, documentation and available license notices.
No records are filtered, relabeled or deduplicated. No models or upstream code
are vendored. Each dataset's `provenance.json` records its pinned commit, every
file's byte size, Git blob SHA-1 and SHA-256. Retrieved on 2026-10-21.

## LOGIC and LogicClimate

- Source: [causalNLP/logical-fallacy](https://github.com/causalNLP/logical-fallacy).
- Paper: [Logical Fallacy Detection, Findings of EMNLP 2022](https://aclanthology.org/2022.findings-emnlp.532/).
- Commit: `2a3d09708122c0994279df034d867b80950700ea`.
- Files: [logic/upstream/data](logic/upstream/data); original
  [README and citation](logic/upstream/README.md).

| Upstream variant | Train | Dev | Test | Notes |
| --- | ---: | ---: | ---: | --- |
| `edu_*.csv` splits | 1,849 | 300 | 300 | 2,449 records, 13 observed labels |
| `climate_*.csv` splits | 855 | 277 | 219 | 1,351 records |
| `climate_*_mh.csv` | 680 | 219 | 180 | Separate masked variants |

`edu_all.csv` contains 2,452 records and 14 observed labels, including three
`miscellaneous` records. `climate_all.csv` contains 1,351 records. These aggregate
files and split files are overlapping representations, not independent records
to concatenate. The downloaded release does **not** establish a 3,761-record
LOGIC classification split. `mappings.csv` is retained as published; it is not
a mapping to CoCoLoFa. Preserve the chosen upstream split and taxonomy when
reporting experiments.

No LICENSE file or explicit dataset license was present in this pinned upstream
tree. The upstream README provides data access and citation instructions; this
snapshot does not invent a license or relicense third-party material under the
host repository's terms. Refer to the authors for additional usage terms.

## Reddit informal fallacies

- Source: [sahaisaumya/informal_fallacies](https://github.com/sahaisaumya/informal_fallacies).
- Paper: [Breaking Down the Invisible Wall of Informal Fallacies in Online Discussions, ACL 2021](https://aclanthology.org/2021.acl-long.53/).
- Commit: `630d56edb27fb0d5f32dd125ad6e886e4ca2955e`.
- Files: [reddit_informal_fallacies/upstream/data](reddit_informal_fallacies/upstream/data).
- Original [README/citation](reddit_informal_fallacies/upstream/README.md) and
  [MIT license](reddit_informal_fallacies/upstream/LICENSE) are retained.

| Processed variant | Train | Dev | Test | Total |
| --- | ---: | ---: | ---: | ---: |
| `annotated_dataset` | 2,351 | 671 | 336 | 3,358 |
| `full_dataset` | 6,823 | 1,950 | 977 | 9,750 |

The full variant adds sampled negatives. Both versions and all 16 raw CSVs
(annotated and negative samples for eight categories) are included. They overlap;
do not concatenate variants as if they were independent datasets.

The actual processed TSV files have **eight** fields, with no header:
comment ID, cleaned token list, original comment of interest, binary token labels,
multiclass token labels, parent, title, label comment. The upstream processed
README lists seven fields because it omits the leading ID. Lists use Python
literal syntax, not JSON. Multiclass tokens use `none` or one of `authority`,
`blackwhite`, `hasty_generalization`, `natural`, `population`, `slippery_slope`,
`tradition`, `worse_problems`.

For a fallacy-only experiment, derive a separate view retaining records with at
least one multiclass token other than `none`; do not delete negatives here.
That criterion retains 1,195 TRAIN, 342 DEV and 171 TEST records (1,708 total)
in either processed variant. This is a token-label-derived criterion, not a
claim that all 3,358 annotated records are positive. Token annotations must be
converted explicitly before treating this as document-level classification.

## Experiment boundaries

These are preserved source datasets, not graph-pipeline-ready mapped inputs.
No cross-dataset label mapping, new split, training or evaluation is performed
by this import. Similar label names alone do not establish equivalent annotation
policies. Keep TEST held out, fit mappings and patterns using TRAIN only, and
report the exact variant and positive-filter policy used.
