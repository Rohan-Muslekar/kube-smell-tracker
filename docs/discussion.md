# Discussion — Current Baseline (Draft)

**Status:** Draft based on the current 35-tag baseline. RQ3 case-study integration and any updates to the dataset or category mapping are pending.

## RQ1: Evolution of Configuration Smells

The results indicate substantial baseline-to-final survival of configuration smells across the sampled release histories. Of the 821 smell instances present at the first sampled tag, 676 (82.3%) were also detected at the final tag. This finding suggests that many configuration issues remain detectable across the studied releases. However, baseline-to-final survival does not necessarily imply uninterrupted presence between releases.

The analysis recorded 147 smell removals, of which 108 (73.5%) coincided with the disappearance of the corresponding Kubernetes object. Therefore, most observed removals should not be interpreted as direct configuration fixes. The remaining 39 removals occurred while the object was retained and were initially classified as candidate fixes. Nine of these were identified as kube-score analyzer artifacts in the project's manual review, leaving 30 remaining candidate fixes pending further case-study evidence.

The study also recorded 41 introductions, including 16 associated with newly introduced objects. No reappearances were observed across the sampled tags. However, transitions occurring between selected releases may remain undetected.

These results demonstrate the importance of distinguishing analyzer-level changes, resource deletion, and potential configuration fixes when interpreting smell lifecycles.

## RQ2: Overlap Between Static Analysis Tools

The reported overlap between kube-linter and kube-score varies with the categories included in the comparison. Across the four smell categories, both tools flagged 134 of 241 distinct object-category pairs (55.6%). Excluding the hygiene category increased the reported overlap to 124 of 158 pairs (78.5%).

This difference demonstrates that category selection substantially influences the overlap measure. In addition, the analyzers support different checks and resource kinds, so their outputs are not directly interchangeable.

The implementation aggregates findings by repository, resource kind, namespace, resource name, and category across the sampled tags. Therefore, the overlap calculation does not require both analyzers to flag the same category at the same release tag. The reported percentages represent shared detection over the sampled history, rather than simultaneous agreement within individual releases.

These findings suggest that the two tools provide partially overlapping perspectives on Kubernetes configuration issues. However, overlap should be interpreted in light of tool coverage, category definitions, and the aggregation method.

## RQ3: Case Studies

**Pending:** Representative commit-level case studies and their supporting evidence will be integrated after the RQ3 investigation is completed.

## Interpretation Notes

- All smell-level counts exclude the `other` category.
- Lifecycle instance counts are tool-specific and may count related warnings separately.
- The 30 remaining candidate fixes should not be described as independently verified genuine fixes.
- Independent human validation of the category mapping is still pending.
- Quantitative statements reflect the current committed baseline and must be rechecked if the dataset, category mapping, or analysis outputs change.

## Supporting Project Artifacts

- `out/instances.csv`
- `out/transitions_summary.csv`
- `out/overlap_summary.csv`
- `scripts/summary.py`
- `kst/track.py`
- `kst/overlap.py`
- `docs/tracking_limitations.md`
- `docs/category_validation.md`
- `results/README.md`
