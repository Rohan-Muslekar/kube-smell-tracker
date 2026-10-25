# Discussion — Current Baseline (Draft)

**Status:** Draft based on the current 35-tag baseline. RQ3 case-study integration, independent category validation, and any updates to the dataset remain pending.

## RQ1: Configuration Smell Prevalence

The study analyzed Kubernetes configuration artifacts from seven open-source projects across five release tags each, covering 35 valid versions.

The current baseline contains 862 configuration smell instances after excluding findings categorized as `other`. These include 483 kube-linter instances and 379 kube-score instances. Resource and reliability smells are the most prevalent categories for both analyzers, followed by security and privilege smells.

These counts represent analyzer-specific instances. Therefore, the same underlying configuration problem may be counted separately when detected by both tools.

## RQ2: Configuration Smell Lifecycle

The results suggest substantial persistence across the sampled releases. Of the 821 smell instances present at the first sampled tag, 676 (82.3%) remained present at the final sampled tag.

The analysis recorded 147 removals, but 108 (73.5%) occurred because the corresponding Kubernetes object disappeared. Therefore, these removals should not automatically be interpreted as fixes.

Of the remaining 39 removals, nine were identified as kube-score analyzer artifacts involving probe checks. This leaves 30 candidate fixes requiring further commit-level investigation before all can be classified as genuine maintenance fixes.

The study also recorded 41 introductions, including 16 associated with newly introduced objects. No reappearances were observed across the five sampled tags per project. However, changes occurring between sampled releases may not be visible.

## Supplementary Analysis: Static Analyzer Overlap

The two analyzers identified overlapping categories of configuration problems, but their coverage was not identical.

Across the supported object kinds, both tools flagged 134 of 241 distinct object-category pairs (55.6%). When hygiene findings were excluded, overlap increased to 124 of 158 pairs (78.5%).

These results are aggregated across the sampled version history. They should not be interpreted as proof that both tools detected each shared object-category pair at the same release tag.

Differences in analyzer checks, supported Kubernetes object kinds, and category coverage help explain the observed disagreement.

## RQ3: Maintenance Change Case Studies

Detailed commit-level case studies remain pending. These investigations will help distinguish deliberate configuration fixes, regressions, object deletions, and analyzer-related artifacts.

The findings from RQ3 will be integrated after the case-study investigation is completed.

## Interpretation and Validation Notes

- Findings categorized as `other` are excluded from the configuration smell analysis.
- Lifecycle instance counts are analyzer-specific rather than deduplicated across tools.
- Object deletion is distinguished from candidate configuration fixes.
- The 30 remaining candidate fixes have not all been independently verified through commit-level investigation.
- Independent two-rater category validation remains pending.
- The numerical results describe the current baseline and should be rechecked if the analysis outputs change.

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
