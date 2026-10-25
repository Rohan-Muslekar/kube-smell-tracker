# Methodology

## 1. Study Overview

This study investigates the evolution of Kubernetes configuration smells across successive releases of open-source software projects. It uses a repository-mining pipeline to collect Kubernetes YAML manifests, analyze them with two static analysis tools, normalize the reported findings, and track configuration smell instances across selected release tags.

The study uses **kube-linter v0.8.3** and **kube-score v1.20.0**. Their outputs are mapped to a common representation to support longitudinal analysis and comparison between analyzers.

The methodology consists of repository and release selection, manifest collection and filtering, static analysis, finding normalization and categorization, lifecycle tracking, and analyzer overlap analysis. The implementation and supporting artifacts are maintained in the `kube-smell-tracker` repository.

## 2. Repository and Release Selection

### 2.1 Repository Selection

Repository selection was recorded on October 22, 2026. The eligibility criteria documented in `data/repos.json` required repositories to:

1. Contain plain Kubernetes YAML manifests within the source repository.
2. Have at least 500 GitHub stars and commits within the preceding six months.
3. Provide at least five release tags spanning at least 12 months.

Seven repositories were included:

| Repository | Selected manifest path |
|---|---|
| microservices-demo | `kubernetes-manifests` |
| kube-prometheus | `manifests` |
| argo-cd | `manifests/install.yaml` |
| flux2 | `manifests` |
| istio | `samples/bookinfo/platform/kube` |
| serving | `config/core` |
| pipeline | `config` |

These repositories cover different application and infrastructure contexts, including microservices, monitoring, GitOps, service mesh, serverless infrastructure, and CI/CD.

The selection configuration also records excluded candidates and their exclusion reasons. These include insufficient recent activity, reliance on Helm templates rather than plain in-tree manifests, and removal of relevant manifests from newer releases.

### 2.2 Release Selection

Release selection is supported by `kst/select_tags.py`.

The utility retrieves Git tags and recognizes version strings matching the form `v?MAJOR.MINOR.PATCH`. For each major–minor version pair, it retains the tag with the highest patch number.

A minor release is eligible when a corresponding `.0` tag exists and the Git commit date associated with that tag is on or after the specified cutoff date, October 22, 2022.

When more than five eligible minor releases are available, the utility selects five approximately evenly spaced positions in semantic-version order, including the first and last eligible entries. This spacing is based on positions in the ordered version sequence rather than equal calendar-time intervals.

The selected tags are explicitly recorded in `data/repos.json`, preserving the study selection independently of future releases.

The collection metadata in `data/versions.csv` contains **35 repository-version combinations**, representing five selected tags for each of the seven repositories. All 35 entries are marked valid. Each entry records the repository, release tag, resolved commit SHA, commit date, number of retained YAML files, validity flag, and an optional note.

## 3. Manifest Collection and Filtering

Manifest collection is implemented in `scripts/collect.sh`, using the repository URLs, selected tags, and manifest paths specified in `data/repos.json`.

For each repository and selected tag, the collection pipeline checks out the corresponding revision and identifies YAML files within the configured paths.

The filtering procedure in `kst/manifests.py` excludes files that do not meet the project's criteria for plain Kubernetes manifests. In particular, it excludes:

- Kustomization files identified by their filenames.
- Files containing recognized Helm template expressions.
- YAML files without the expected top-level Kubernetes `apiVersion` and `kind` declarations.

Skipped files and their recorded reasons are written to `raw/skipped_files.txt`.

This filtering is based on textual checks rather than complete Kubernetes schema validation. Consequently, passing the filter does not guarantee that every retained file is a valid or fully renderable Kubernetes resource.

The pipeline also constructs an inventory of Kubernetes objects from retained files using `kst/inventory.py`. This inventory supports subsequent analysis of whether an object remains present when an associated smell disappears.

Helm charts are not rendered, and Kustomize configurations are not built into their final deployed form before analysis.

## 4. Static Analysis and Output Validation

### 4.1 Analyzer Configuration

Two static analyzers are applied to the retained Kubernetes manifests:

- **kube-linter v0.8.3**, configured through `tools/kube-linter.yaml` and invoked with `--add-all-built-in`.
- **kube-score v1.20.0**, invoked with JSON output enabled.

The analyzer execution procedure is implemented in `scripts/analyze.sh`. Analyzer outputs are stored separately under `raw/kube-linter/` and `raw/kube-score/`, with diagnostic information retained where applicable.

The analyzer installation script, `tools/install.sh`, uses version-specific Go module installation commands and places the executables in the repository-local `tools/bin` directory.

### 4.2 Output Validation

The pipeline validates analyzer outputs using `kst/validate.py`.

A result is rejected when the expected output is empty or cannot be parsed as a JSON array or object. Versions without retained manifests are also considered invalid during collection.

Only versions marked valid in `data/versions.csv` are included in subsequent analysis. This prevents a failed analyzer execution from automatically being interpreted as the disappearance of previously reported smells.

However, the validation procedure checks basic JSON structure rather than exhaustively verifying analyzer-specific schemas or the completeness of all reported findings.

The collection process additionally probes individual files to identify cases that kube-linter cannot load. These cases are recorded in `raw/load_failures.tsv`.

## 5. Finding Normalization and Categorization

### 5.1 Finding Normalization

Analyzer outputs are normalized by `kst/normalize.py` into a common finding representation containing:

`repo, version, tool, check, category, kind, namespace, name, file`

For kube-linter, reported violations are converted into normalized findings.

For kube-score, checks are converted into findings when they are not skipped and their reported grade is below 10.

The normalization process also standardizes file paths and Kubernetes object namespaces. Cluster-scoped objects are represented with an empty namespace.

This common representation enables findings from different analyzers to be processed by the same tracking and reporting pipeline.

### 5.2 Smell Categorization

Findings are categorized through the mapping defined in `data/check_categories.csv`.

The mapping associates each analyzer-specific check identifier with a category and a documented classification rationale.

The five categories are:

| Category | Scope |
|---|---|
| `security` | Security-related configuration checks |
| `resource` | Resource management and reliability-related checks |
| `image` | Container image and related supply-chain checks |
| `hygiene` | Configuration consistency and maintenance-related checks |
| `other` | Checks outside the four primary smell categories |

Categorization uses the combination of analyzer name and check identifier.

Checks not present in the mapping are assigned to `other` and recorded in `out/unmapped_checks.txt`. The analysis command returns a nonzero exit status when unmapped checks are encountered.

The `other` category is retained in some intermediate and generated data but excluded from the principal smell-focused overlap analysis.

The project documents a separate procedure for independent category validation in `docs/category_validation.md`. At the time of the reviewed documentation, independent rating results and adjudication were still pending.

## 6. Configuration Smell Lifecycle Tracking

Lifecycle tracking is implemented in `kst/track.py`.

A smell instance is identified by the tuple:

`(repo, tool, kind, namespace, name, check)`

The file path is intentionally excluded from this identity. Consequently, moving an otherwise unchanged Kubernetes object between files does not automatically create a new smell identity.

The tracking algorithm examines the presence or absence of each instance across the valid release tags of its repository.

An instance present in the first observed release is identified as present at baseline rather than newly introduced during the observed study period.

For subsequent releases, the implementation records lifecycle transitions:

| Transition | Meaning |
|---|---|
| `introduced` | A smell appears after being absent, without an earlier observed presence |
| `persisted` | A smell remains present in consecutive releases |
| `removed` | A previously present smell becomes absent |
| `reappeared` | A smell returns after an earlier observed removal |

The implementation also distinguishes removals associated with the disappearance of the Kubernetes object itself. These are recorded as `removed_object_gone`.

When the object remains present but the associated finding disappears, the removal may represent a configuration correction. However, such cases require further inspection because changes in analyzer behavior, manifest parsing, or analysis coverage can also affect the findings.

Similarly, the implementation records `introduced_new_object` when a newly observed smell accompanies a newly observed object.

Tracking is performed independently for each analyzer. Therefore, equivalent problems reported by both analyzers may be represented by separate smell instances.

Because the study samples selected releases rather than every intervening commit or tag, transitions describe changes observed between sampled versions. Intermediate changes cannot be fully reconstructed.

## 7. Analyzer Overlap Analysis

Analyzer overlap is calculated using `kst/overlap.py`.

The comparison unit is identified by:

`(repo, kind, namespace, name, category)`

Findings categorized as `other` are excluded.

The comparison is restricted to object kinds represented in kube-score's analyzed output, avoiding comparisons dominated by kinds that kube-score does not evaluate.

For each comparison unit, the implementation records whether kube-linter, kube-score, or both tools reported at least one finding.

The summary classifies each unit as:

- `linter_only`
- `score_only`
- `both`

Each repository–object–category combination contributes at most once to the summary, regardless of the number of findings or sampled releases.

**The implementation aggregates analyzer observations across the selected releases. It does not require both analyzers to report a finding for the same object and category in the same release.** Therefore, `both` represents overlap over the observed study period, not necessarily simultaneous agreement at a particular tag.

The comparison is performed at the category level rather than requiring identical check identifiers between the two analyzers.

## 8. Generated Analysis Artifacts

The analysis pipeline is executed through `python3 -m kst`, implemented in `kst/__main__.py`.

It reads the stored analyzer outputs, collection metadata, and object inventories, then generates structured analysis artifacts in `out/`.

| Output | Purpose |
|---|---|
| `findings.csv` | Normalized findings, including duplicate-report counts |
| `prevalence.csv` | Finding and distinct-instance counts by repository, version, tool, and category |
| `instances.csv` | Instance presence histories and lifecycle transition counts |
| `transitions_summary.csv` | Aggregated lifecycle transitions by tool and category |
| `transitions_by_repo.csv` | Lifecycle transitions by repository, tool, and category |
| `overlap_summary.csv` | Analyzer overlap counts by category |
| `unmapped_checks.txt` | Analyzer checks without an explicit category mapping |

The generated artifacts distinguish reported findings from distinct instances. This distinction is important because multiple analyzer reports may correspond to the same normalized instance identity.

The raw analyzer outputs are retained to support inspection and regeneration of the derived tables.

## 9. Methodological Limitations and Threats to Validity

Several limitations affect the interpretation of the results.

**Manifest representation.** Helm templates are excluded rather than rendered, while Kustomize bases and patches are analyzed without generating their final composed configurations. Findings may therefore differ from those obtained from deployed manifests.

**Release sampling.** Five selected release tags are analyzed per repository. Changes occurring between these versions may remain unobserved, including temporary removals and reappearances.

**Instance identity.** The tracking key uses object kind, namespace, name, tool, and check. Object renaming can consequently appear as a removal followed by an introduction, even when the underlying logical resource continues to exist.

**Analyzer coverage.** kube-linter and kube-score implement different checks and do not necessarily analyze the same Kubernetes object kinds. Their outputs are not interchangeable measures of configuration quality.

**Parsing and collection limitations.** Manifest filtering and object inventory construction do not provide full Kubernetes rendering or schema validation. Files that cannot be loaded by an analyzer may introduce gaps in the observations.

**Interpretation of removals.** A disappearing finding does not by itself establish that a developer intentionally fixed a configuration problem. Object deletion, manifest restructuring, parser behavior, or analyzer limitations may also explain the disappearance.

**Overlap interpretation.** Analyzer overlap is aggregated across the study period. The resulting `both` classification should not be interpreted as evidence that both analyzers agreed on the same object in the same release.

**Category validity.** The category mapping is explicitly documented, but independent agreement results should not be assumed until the planned validation procedure has been completed.

Additional lifecycle-specific limitations are documented in `docs/tracking_limitations.md`.

## 10. Reproducibility

The repository provides a Makefile and supporting scripts for reproducing the collection and analysis pipeline.

The documented full workflow is:

```bash
./tools/install.sh
make all
python3 -m pytest
```

The `make all` target executes `scripts/collect.sh` followed by `python3 -m kst`. It does not independently install tools or execute tests.

The derived analysis tables can also be regenerated from the committed raw data without repeating repository collection or analyzer execution:

```bash
python3 -m kst
```

The README documents a local validation procedure equivalent to the continuous integration checks:

```bash
python3 -m pytest -q -rs
python3 -m kst --out /tmp/kube-smell-ci-check
diff -ru out /tmp/kube-smell-ci-check
```

The continuous integration workflow runs tests, regenerates derived analysis tables, and compares them against the committed outputs. It does not recollect source repositories or rerun the external analyzers.

The environment recorded for the committed results includes Fedora Linux 44, Go 1.26.9, Python 3.14.8, kube-linter v0.8.3, and kube-score v1.20.0. Additional tool versions are documented in the repository README.

The README reports that a fresh-clone reproduction produced byte-identical `out/` and `data/versions.csv` artifacts. An independent fresh-clone run on Ubuntu under WSL is documented in [reproduction.md](reproduction.md).

For reproducibility, the study's selected repositories, release tags, and resolved commit identifiers are recorded in `data/repos.json` and `data/versions.csv`.

The final study revision should be identified by its Git commit SHA when the report and accompanying artifacts are finalized.
