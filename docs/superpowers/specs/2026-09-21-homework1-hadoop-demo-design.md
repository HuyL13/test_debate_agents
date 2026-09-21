# Homework 1 Hadoop Demo Design

## Goal

Create a self-contained `homework1/` directory that a student can use to demonstrate both exercises from `Homework 1.pdf`: word counting over the Bible and Shakespeare corpus, and overlapping 9-mer counting over the supplied E. coli genome. The deliverable is optimized for a short in-class demonstration rather than a written report.

## Deliverables

- Python Hadoop Streaming mappers and reducers for word count and k-mer count.
- Local runner scripts that reproduce and verify both top-10 results without requiring Hadoop.
- A Hadoop/HDFS runner that uploads inputs, launches the streaming jobs, and prints the top 10 records by descending count.
- A data-download script using the two files linked by the official exercise page.
- A concise Vietnamese README containing setup, local verification, Hadoop execution, expected output, and a short demo sequence.
- Automated tests covering tokenization, overlapping k-mer generation, FASTA header handling, sequence-line boundaries, and aggregation.

## Structure

```text
homework1/
  README.md
  download_data.ps1
  run_local.ps1
  run_hadoop.sh
  src/
    wordcount_mapper.py
    sum_reducer.py
    kmer_mapper.py
  tests/
    test_streaming.py
  data/                 # downloaded inputs; ignored by Git
  output/               # generated local results; ignored by Git
```

## Data flow

For word count, the mapper reads text from standard input, splits each line using whitespace (matching Hadoop's standard WordCount behavior for the already punctuation-stripped corpus), and emits `word\t1`. The reducer consumes sorted mapper output and emits `word\ttotal`.

For k-mer count, the mapper reads FASTA, ignores header lines, normalizes bases to uppercase, and emits every overlapping 9-mer with value 1. It preserves sequence continuity across wrapped FASTA lines while resetting at each new header, so k-mers do not cross records. K-mers containing characters outside `A`, `C`, `G`, and `T` are excluded. The same sum reducer aggregates counts.

Local execution decompresses each input, pipes it through the mapper, sorts by key, applies the reducer, and sorts numerically by count to produce the top 10. Hadoop execution uses the same source files with Hadoop Streaming and the reducer as a combiner where supported.

## Reliability and demo behavior

Scripts fail fast when required commands or input files are absent and display actionable messages. HDFS output paths are removed only when they are the explicit homework paths chosen by the script. Expected top-10 results are recorded only after running against the exact files linked by the exercise.

The local runner provides a dependable fallback for classroom demonstration if a Hadoop cluster is unavailable. The Hadoop runner demonstrates the requested MapReduce implementation when Hadoop is available.

## Verification

Unit tests run the mappers and reducer as subprocesses using small deterministic fixtures, including the `ACACACAGT` example from the assignment. End-to-end verification downloads the official inputs, runs both local pipelines, and compares their displayed top 10 with independently computed reference counts.
