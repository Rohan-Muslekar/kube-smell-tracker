# kube-smell-tracker

Artifact for *Tracking the Lifecycle of Kubernetes Configuration Smells Across Versions*
(ENGR 5570G, Group 4). It runs two static analyzers over the Kubernetes manifests of seven
open-source projects at five release tags each. Each smell instance is then followed from tag
to tag and labelled introduced, persisted, removed or reappeared.

## Reproduce

```bash
./tools/install.sh          # builds the pinned analyzers into tools/bin
make all                    # clones repos into work/, runs both analyzers, writes raw/ and out/
python3 -m pytest           # unit and pipeline tests
```

`make all` runs `./scripts/collect.sh` and then `python3 -m kst`. Re-running only the analysis
on the committed `raw/` needs no network: `python3 -m kst`.

## Results

[`results/`](results/) has screenshots of the results with a short explanation of each
([results/README.md](results/README.md)) and every command used to produce them
([results/commands.md](results/commands.md)). `python3 scripts/summary.py` prints the headline
numbers.

The committed outputs were checked against a fresh clone of this repository: after
`./tools/install.sh && make all`, `out/` and `data/versions.csv` were byte-identical. The raw
analyzer files differ only in two ways: kube-linter's run timestamp (`Summary.CheckEndTime`) and
the order in which kube-score lists checks. None of the outputs depend on either.

## Environment used for the committed outputs

| Item | Version |
|---|---|
| OS | Fedora Linux 44, kernel 6.19.10 |
| Go (builds the analyzers) | go1.26.9 |
| kube-linter | v0.8.3 (`go install golang.stackrox.io/kube-linter/cmd/kube-linter@v0.8.3`), run with `--add-all-built-in` and the pinned `--config tools/kube-linter.yaml` (so a `.kube-linter.yaml` inside an analyzed repo is never read) |
| kube-score | v1.20.0 (`go install github.com/zegl/kube-score/cmd/kube-score@v1.20.0`) |
| Python | 3.14.8, standard library only (pytest 9.1.1 for tests) |
| git / jq / bash | 2.56.0 / 1.8.1 / 5.3.9 |

Both analyzers report `development` from their `version` subcommand when built with
`go install`. `tools/install.sh` prints the module version from `go version -m` instead.

## Study systems

`data/repos.json` lists each included repository: URL, manifest path(s), the five tags,
and the reason for inclusion. Excluded candidates are listed with the reason.

Selection criteria:
1. The repository ships plain Kubernetes YAML in the repository, not only Helm charts or release assets.
2. It has commits in the last six months and at least 500 stars.
3. It has at least five release tags spanning at least 12 months.

The tags are the latest patch of five minor releases, evenly spaced over the minors first released
since 2022-10-22, with the newest included, as of 2026-10-22. They are reproducible with
`python3 -m kst.select_tags work/<repo> 2022-10-22`; a later run also sees newer releases, so
`data/repos.json` is the record of the tags used. The commit SHA of every tag is in
`data/versions.csv`.

## Pipeline

1. **Collect** (`scripts/collect.sh`) does the following for each repo and tag:
   - checks out the tag
   - keeps the YAML files under the manifest path that are plain Kubernetes objects (`kst/manifests.py`). It skips kustomization files, Helm-templated files and non-Kubernetes YAML, and logs every skipped file to `raw/skipped_files.txt`.
   - lists the objects defined in the kept files (`raw/objects/`)
   - runs both analyzers (`scripts/analyze.sh`, writing `raw/kube-linter/`, `raw/kube-score/`)
   - lints each file alone to find files kube-linter cannot load (unparseable YAML, `kind: List`), which it otherwise skips silently, and logs them to `raw/load_failures.tsv`

   A tag is invalid when either analyzer's stdout is empty or not a JSON array or object (`kst/validate.py`; kube-score prints nothing when it crashes), or when no manifests remain. Invalid tags are left out of tracking, so a crashed run does not look like removed smells. All 35 tags are valid.
2. **Normalize** (`kst/normalize.py`) produces one finding per analyzer report:
   - kube-score checks count when graded below 10 and not skipped
   - file paths are made relative to the repo root
   - each check is mapped to a category through `data/check_categories.csv`, which covers every check seen and gives a rationale for each one
   - categories: security, resource (resource and reliability), image (image and supply chain), hygiene, other (style, opinionated defaults and kube-linter's example ownership policies; left out of the smell analysis)
   - cluster-scoped kinds (ClusterRole, CustomResourceDefinition, ...) always get an empty namespace, as Kubernetes ignores one there
3. **Track** (`kst/track.py`) follows each instance across tags.
   - **Identity:** the instance key is `(repo, tool, kind, namespace, name, check)`. The file path is not part of it, so moving an object to another file keeps its history.
   - **Labels:** for each pair of consecutive tags, an instance is persisted, introduced, removed or reappeared (present again after an earlier removal).
   - **Removals:** a removal counts as `removed_object_gone` when the object itself no longer exists, and as a fix otherwise.
   - **Introductions:** an introduction counts as `introduced_new_object` when it arrived together with a new object.
4. **Overlap** (`kst/overlap.py`) compares the two analyzers before any de-duplication, on the object kinds that kube-score scores. Each (repo, kind, namespace, name, category) counts once over all tags; it is "both" when both tools flagged that object in that category at the same tag (in any check of the category, not necessarily the same check).

## Outputs (`out/`)

| File | Columns |
|---|---|
| `findings.csv` | repo, version, tool, check, category, kind, namespace, name, file, dup_count (identical reports in one tag, e.g. one per container) |
| `prevalence.csv` | repo, version, tool, category, findings (reports), instances (distinct keys) |
| `instances.csv` | one row per instance: key fields, category, presence (e.g. `11100` over the five tags), at_baseline, introduced, persisted, removed, reappeared, removed_object_gone, introduced_new_object |
| `transitions_summary.csv` | the instance counts summed per tool and category |
| `transitions_by_repo.csv` | the same per repo, tool and category |
| `overlap_summary.csv` | category, linter_only, score_only, both (distinct object-category pairs) |
| `unmapped_checks.txt` | checks missing from the category map; must be empty, otherwise `python3 -m kst` exits non-zero |

`data/spot_check.csv` holds the manual check of 20 instances. They are drawn by
`scripts/sample_spot_check.py` with seed 5570: 5 each of persisted, fixed, object deleted and
introduced. Each was confirmed or rejected by reading the YAML at both tags, with the cause noted.

## Known limitations

- Helm charts are not rendered, and kustomize bases and patches are linted unrendered. For flux2, this means patch fragments are analyzed as if they were complete objects.
- A renamed object appears as one removal plus one introduction. The spot-check found no renames.
- The object inventory (`kst/inventory.py`) reads the top level of each YAML document without a full YAML parser. Objects inside a `kind: List` are not listed. The inventory matched every object either analyzer reported.
- kube-score scores only workload-related kinds (it never scores RBAC objects), so the overlap table is limited to the kinds it scores.
- Files kube-linter cannot load are logged, not analyzed (`raw/load_failures.tsv`). If a file failed at one tag and loaded at the next, its smells would look introduced or removed; in the committed data every such file fails at every tag where it exists. A multi-document file where only some documents fail to parse is not detected.
- Instance counts are per tool: a problem both tools flag is two instances. The paper also reports merged counts.
