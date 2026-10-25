# Reproduction Guide

**Status:** Documentation of the current baseline (7 repositories, 35 sampled release tags). The commands below are based on the repository implementation. A fresh-clone reproduction has been reported by the project team, but has not been independently rerun as part of this documentation review.

## 1. Prerequisites

The full pipeline requires:

- A Linux environment with Bash, Git, GNU Make, jq, Python 3, and Go.
- Network access to download Go modules and clone the selected repositories.
- Sufficient disk space for the cloned repositories, analyzer binaries, and generated outputs.
- Python's `pytest` package to run the test suite.

The committed baseline was produced using Fedora Linux 44, Go 1.26.9, Python 3.14.8, Git 2.56.0, jq 1.8.1, and Bash 5.3.9. These document the reference environment; compatibility with other versions has not been fully established.

The analysis pipeline uses the Python standard library. The tests additionally require `pytest`.

## 2. Clone the Repository

```bash
git clone https://github.com/Rohan-Muslekar/kube-smell-tracker.git
cd kube-smell-tracker
```

For exact reproduction of a particular study revision, check out its recorded commit SHA before running the pipeline. The final study revision should be documented when the team freezes the artifact.

## 3. Install the Analyzers

```bash
./tools/install.sh
```

This builds the pinned analyzers into `tools/bin/`:

- kube-linter v0.8.3
- kube-score v1.20.0

The installation script prints the Go module information associated with each executable using `go version -m`.

The tools are installed locally within the repository, not system-wide.

## 4. Full Data Collection and Analysis

```bash
make all
```

The Makefile executes collection followed by analysis:

1. `scripts/collect.sh` reads the selected repositories, manifest paths, and release tags from `data/repos.json`.
2. Each repository is cloned into `work/` if it is not already available locally.
3. The selected tags are checked out and their commit SHAs recorded in `data/versions.csv`.
4. Kubernetes YAML files are filtered, and excluded files are logged.
5. Object inventories are generated.
6. kube-linter and kube-score analyze the selected manifests.
7. Analyzer outputs are checked for basic JSON validity.
8. `python3 -m kst` processes the collected data and generates analysis tables in `out/`.

The full run requires network access and previously installed analyzer executables.

The selected tags are specified in `data/repos.json`. The collection script records their resolved commit SHAs but does not independently compare them with a previously recorded revision list.

## 5. Reanalyze the Committed Raw Data

To regenerate analysis outputs without downloading repositories or running the external analyzers:

```bash
python3 -m kst --out /tmp/kube-smell-recheck
diff -ru out /tmp/kube-smell-recheck
```

This uses the committed `raw/` inputs.

If `diff` produces no output and exits successfully, the generated analysis tables match the committed `out/` directory.

This is an offline analysis reproduction, not a complete recollection of the source repositories.

## 6. Run the Tests

```bash
python3 -m pytest -q -rs
```

The `-rs` option displays reasons for skipped tests.

Some analyzer integration tests are skipped when the required executables are absent from `tools/bin/`. Therefore, test results should include both the number of passing tests and any skipped tests.

Test counts should be recorded for the specific revision tested rather than assumed to remain constant.

## 7. Output Artifacts

The main outputs include:

- `data/versions.csv`: selected tags, resolved commit SHAs, dates, and validity status.
- `raw/kube-linter/`: kube-linter JSON reports.
- `raw/kube-score/`: kube-score JSON reports.
- `raw/objects/`: object inventories.
- `raw/skipped_files.txt`: files excluded during manifest filtering.
- `raw/load_failures.tsv`: detected kube-linter file-loading failures.
- `out/findings.csv`: normalized analyzer findings.
- `out/prevalence.csv`: findings and instance counts.
- `out/instances.csv`: tracked smell instances and lifecycle information.
- `out/transitions_summary.csv`: aggregated lifecycle transitions.
- `out/transitions_by_repo.csv`: transitions by repository.
- `out/overlap_summary.csv`: analyzer overlap by category.
- `out/unmapped_checks.txt`: checks not covered by the category mapping.

## 8. Validation and Interpretation

A release tag is considered valid by the collection pipeline when at least one manifest was selected and both analyzers produced nonempty, parseable JSON arrays or objects.

This validation does not independently guarantee that every selected manifest was successfully analyzed, that all expected analyzer checks ran, or that the reports conform to a complete expected schema.

Analyzer exit codes are ignored because findings can produce nonzero exit codes. The pipeline subsequently validates the basic JSON structure of the output files.

The collection script also probes individual files for a known kube-linter loading failure. This does not guarantee detection of every possible partial parsing failure.

The overlap analysis aggregates detections across the sampled release history by repository, object identity, and category. It does not require both analyzers to flag an object-category pair at the same tag.

## 9. Known Reproduction Limitations

- Helm charts are not rendered, and some Kustomize configurations are analyzed without rendering.
- Object renaming can split a tracked identity into a removal and an introduction.
- Only five sampled release tags per repository are analyzed; changes between those tags may be missed.
- Object deletion is distinguished from candidate fixes, but further commit-level verification is required to confirm genuine fixes.
- Some unloadable files are logged rather than analyzed.
- Analyzer version pinning does not independently guarantee identical behavior across all operating systems and build environments.
- Existing raw files from previously collected tags are not automatically cleared when the tag selection changes.
- The collection script does not explicitly verify the checked-out tag SHA against a previously recorded expected SHA.

## 10. Reproduction Evidence and Final Revision

The project README reports that a fresh-clone reproduction produced byte-identical derived tables and `data/versions.csv`. Raw analyzer reports differed in kube-linter timestamps and kube-score check ordering.

The repository's CI workflow independently regenerates analysis tables from committed raw data and compares them with committed outputs. CI does not rerun full source collection or install the external analyzers.

Before the final submission, record:

- The final study commit SHA.
- The environment used for final reproduction.
- The test result, including skipped tests.
- Whether full collection was rerun or only offline analysis was reproduced.
- Any differences between generated and committed outputs.

These details should reflect actual execution evidence rather than assumed success.
