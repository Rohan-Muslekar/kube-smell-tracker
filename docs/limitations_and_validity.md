# Limitations and Threats to Validity — Current Baseline (Draft)

**Status:** Draft based on the current 35-tag baseline. Revisions may be required after RQ3 case-study integration, category validation, or dataset updates.

## Construct Validity

Configuration smells were operationalized using findings from two static analyzers, kube-linter and kube-score, and mapped into four smell categories: security, resource, image, and hygiene. Checks classified as `other` were excluded from smell-level results. Although a two-rater category-validation procedure and agreement calculator have been prepared, independent ratings, agreement measurements, and adjudicated decisions remain pending. Therefore, category assignments and the exclusion of certain checks may affect the reported prevalence and category-level comparisons. Furthermore, the disappearance of an analyzer finding does not necessarily demonstrate that the underlying configuration issue was resolved.

## Internal Validity

Smell instances are tracked using repository, tool, resource kind, namespace, resource name, and check identifier. Changes to these identity fields may split the history of the same underlying resource, while deletion and recreation between sampled tags may remain undetected. The tracking process also depends on consistent object inventories, which are extracted without fully parsing YAML or expanding Kubernetes `List` objects. Consequently, incomplete inventories, unsupported configurations, and analyzer behavior may affect the interpretation of lifecycle transitions.

Of the 147 recorded smell removals, 108 coincided with object disappearance. The remaining 39 were initially candidate fixes, including nine removals classified as analyzer artifacts during the project's manual review. The other 30 are counted as fixes. Only the four in the spot-check have been traced to commits so far, so the rest rely on the analyzer output and the object inventory.

## External Validity

The study examines seven selected open-source repositories at five release tags each. The findings may not generalize to other Kubernetes projects, private deployments, or different release histories.

The collection pipeline does not render Helm charts, excludes Helm-templated files, and processes certain Kustomize inputs without rendering. Consequently, generated configurations may be omitted, while some patch fragments may be analyzed outside their complete deployment context. These restrictions limit the configurations represented in the study.

## Conclusion Validity

Sampling five release tags per repository may conceal introductions, removals, or reappearances occurring between the selected versions. Accordingly, zero observed reappearances should not be interpreted as evidence that none occurred between releases.

Instance counts are analyzer-specific, meaning that related warnings from different tools may be counted separately. Moreover, the tool-overlap calculation groups findings by repository, resource kind, namespace, resource name, and category across all sampled tags; it does not require both analyzers to report the category at the same tag. The reported overlap percentages therefore describe shared detection across the sampled history rather than simultaneous agreement at individual releases.

## Pending Validation

- Independent human category ratings, agreement statistics, and adjudication.
- Commit-level tracing of the 26 fixes and the introductions outside the spot-check (RQ3).
- Validation using denser release histories and rendered manifests, if those datasets become available.
- Final verification of numerical claims after any dataset, category-mapping, or analysis changes.

## Supporting Project Artifacts

- `docs/tracking_limitations.md`
- `docs/category_validation.md`
- `results/tracking_validation.md`
- `results/README.md`
- `out/instances.csv`
- `out/transitions_summary.csv`
- `out/overlap_summary.csv`
- `kst/track.py`
- `kst/overlap.py`
- `kst/manifests.py`
- `scripts/summary.py`
