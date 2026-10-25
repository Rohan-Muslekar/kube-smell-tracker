# Reproduction Guide

**Status:** Documentation of the current baseline (7 repositories, 35 sampled release tags). An independent fresh-clone reproduction was performed on October 25, 2026, using Ubuntu under Windows Subsystem for Linux (WSL). The tested repository revision was `0705dce6a4b9695a2860d4fdc338870121d9666c`. The full pipeline completed successfully and reproduced the reported aggregate counts and tracked final outputs. Some regenerated raw files differed from the committed versions, as documented in Section 10.

## 1. Prerequisites

The full pipeline requires:

- A Linux environment with Bash, Git, GNU Make, jq, Python 3, and Go.
- Network access to download Go modules and clone the selected repositories.
- Sufficient disk space for the cloned repositories, analyzer binaries, and generated outputs.
- Python's `pytest` package to run the test suite.

The committed baseline was produced using Fedora Linux 44, Go 1.26.9, Python 3.14.8, Git 2.56.0, jq 1.8.1, and Bash 5.3.9. These document the reference environment; compatibility with other versions has not been fully established.

The independent reproduction was performed using Ubuntu under WSL, Go 1.26.8, Python 3.14.4, Git 2.53.0, GNU Make 4.4.1, jq 1.8.1, and pytest 9.0.2.

The analysis pipeline uses the Python standard library. The tests additionally require `pytest`.

On Ubuntu, the required packages can be installed using:

```bash
sudo apt update
sudo apt install -y golang-go make jq python3-pytest
```

Package names and installation procedures may differ across Linux distributions.

## 2. Clone the Repository

```bash
git clone https://github.com/Rohan-Muslekar/kube-smell-tracker.git
cd kube-smell-tracker
```

For exact reproduction of a particular study revision, check out its recorded commit SHA before running the pipeline.

The independently tested revision was:

```text
0705dce6a4b9695a2860d4fdc338870121d9666c
```

To check out this revision:

```bash
git checkout 0705dce6a4b9695a2860d4fdc338870121d9666c
```

This identifies the independently tested revision, not necessarily the final study revision. The final study SHA should be recorded after the team freezes the artifact.

## 3. Install the Analyzers

```bash
make tools
```

The Makefile invokes the analyzer installation procedure, which builds the pinned analyzers into `tools/bin/`:

- kube-linter v0.8.3
- kube-score v1.20.0

The underlying installation script is also available:

```bash
./tools/install.sh
```

The installation script prints the Go module information associated with each executable using `go version -m`.

The tools are installed locally within the repository, not system-wide.

During the independent reproduction, `make tools` completed successfully.

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

During the independent fresh-clone reproduction, `make all` completed successfully and reported:

```text
19346 findings, 1340 instances, 35 versions -> out/
```

These aggregate counts matched the reported baseline.

## 5. Reanalyze the Committed Raw Data

To regenerate analysis outputs without downloading repositories or running the external analyzers:

```bash
python3 -m kst --out /tmp/kube-smell-recheck
diff -ru out /tmp/kube-smell-recheck
```

This uses the committed `raw/` inputs.

If `diff` produces no output and exits successfully, the generated analysis tables match the committed `out/` directory.

This is an offline analysis reproduction, not a complete recollection of the source repositories.

The independent verification on October 25, 2026, executed the full pipeline using `make all`. The offline reproduction commands above were not separately executed during that verification.

## 6. Run the Tests

```bash
python3 -m pytest -q -rs
```

The `-rs` option displays reasons for skipped tests.

Alternatively, the Makefile provides:

```bash
make test
```

Some analyzer integration tests are skipped when the required executables are absent from `tools/bin/`. Therefore, test results should include both the number of passing tests and any skipped tests.

During the independent reproduction, `pytest` was initially unavailable and had to be installed separately. After installation, the following command completed successfully:

```bash
make test
```

Observed result:

```text
83 passed in 0.78s
```

No tests failed or were skipped in this run because the required analyzer executables were installed.

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
- Regenerated raw analyzer reports may differ in timestamps, finding content, or ordering, even when aggregate results remain unchanged.
- The ordering of object inventories and skipped-file records may vary between collection runs.
- The skipped-file records depend on how git checks out symlinks (see Section 10). The analyzer-finding differences still need investigation before claiming byte-identical reproduction of all raw artifacts.

## 10. Reproduction Evidence and Final Revision

### Previously reported team reproduction

The project README reports that a fresh-clone reproduction produced byte-identical derived tables and `data/versions.csv`. Raw analyzer reports differed in kube-linter timestamps and kube-score check ordering.

This is the reproduction evidence previously reported by the project team.

### Independent fresh-clone verification — October 25, 2026

An independent verification was performed using a fresh repository clone on Ubuntu under WSL.

**Tested repository revision:**

```text
0705dce6a4b9695a2860d4fdc338870121d9666c
```

**Environment:**

- Operating system: Ubuntu under WSL
- Go: 1.26.8
- Python: 3.14.4
- Git: 2.53.0
- GNU Make: 4.4.1
- jq: 1.8.1
- pytest: 9.0.2
- kube-linter: v0.8.3
- kube-score: v1.20.0

**Commands executed successfully:**

```bash
make tools
make all
make test
```

**Observed results:**

| Verification item | Result |
|---|---|
| Repository cloning | Successful |
| Analyzer installation | Successful |
| Full collection and analysis | Successful |
| Raw findings | 19,346 |
| Tracked instances | 1,340 |
| Analyzed versions | 35 |
| Automated tests | 83 passed, 0 failed, 0 skipped |
| Tracked final outputs in `out/` | No changes detected by Git |
| Modified object inventory TSV files | Identical content after sorting lines |
| Regenerated analyzer JSON files | 70 modified; 45 still differed after ignoring kube-linter `CheckEndTime` |
| `raw/skipped_files.txt` | 30 previously recorded `serving` entries absent from the regenerated file |

The modified TSV object inventories were compared after sorting their lines, confirming that their observed differences were limited to record ordering.

For the JSON reports, 70 modified files were compared after removing the `Summary.CheckEndTime` field. Of these, 25 were identical under that comparison, while 45 retained differences. A detailed comparison of one kube-linter report for `kube-prometheus` v0.12.0 showed that some `dangling-servicemonitor` findings present in the committed report were absent from the regenerated report.

The skipped-file comparison identified 30 entries for the `serving` repository that appeared in the committed `raw/skipped_files.txt` but were absent from the regenerated file. These entries were distributed across five sampled versions.

These 30 entries are six files per tag (for example `config/core/300-imagecache.yaml`) that Knative serving stores as git symlinks into `vendor/`. The committed run used a git with `core.symlinks=false`, which writes each link as a small text file holding the target path; the filter logged those as not Kubernetes objects. On WSL they were real symlinks, which `find -type f` in `scripts/collect.sh` skips without logging. Neither run analyzes the linked files, so the outputs are the same.

The `dangling-servicemonitor` difference is still open: `out/` did not change, so the findings should still be present after normalization, and the two reports need comparing directly. Check with:

```bash
git -C work/serving ls-files -s config/core | awk '$1 == 120000'
git config --get core.symlinks
grep -c dangling-servicemonitor out/findings.csv
```

The final output directory was checked using:

```bash
git status --short -- out/
```

The command produced no output, indicating no changes to tracked files in `out/`. This is a Git working-tree comparison rather than an independent byte-by-byte verification of every possible generated artifact.

**Interpretation:** The full pipeline executed successfully in a fresh environment, the reported aggregate counts were reproduced, and tracked final outputs remained unchanged. However, raw artifacts were not fully identical. The causes and implications of the raw differences require further investigation before claiming complete byte-identical reproduction.

### Continuous integration

The repository's CI workflow independently regenerates analysis tables from committed raw data and compares them with committed outputs. CI does not rerun full source collection or install the external analyzers.

### Final study revision

The tested SHA above records the independent verification performed on October 25, 2026. It should not automatically be treated as the final study revision.

Before final submission, the team should record the final study commit SHA after all relevant changes and pull requests have been integrated. If the final revision changes the implementation or inputs, the corresponding reproduction checks should be repeated or their scope clearly qualified.
