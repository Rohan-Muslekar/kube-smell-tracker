# Track C: survival and sensitivity result note

Input: master `8915044`, 123 valid sampled versions of stored manifests.
These are preliminary results, not the forthcoming rendered-data freeze.

## Reproduction

```bash
python -m kst
python scripts/report_numbers.py --headlines-only --out results/sensitivity/baseline
python scripts/report_numbers.py --exclude istio --out results/sensitivity/without_istio
python scripts/report_numbers.py --exclude flux2 --out results/sensitivity/without_flux2
python -m pytest -q -rs
```

The offline pipeline generates `out/km_by_category.csv` and `out/km_by_system.csv`.
`python -m kst.survival_km` regenerates just the curves from existing instances.
The headline mode does not need plots, historical rendering artifacts or cloned
study repositories. `--exclude` is repeatable, filters before aggregation, and
writes `headlines.json` instead of the legacy full-report TeX/PDF outputs. The
ordinary report command without these flags retains its existing behavior.

## Preliminary sensitivity numbers

| Dataset | Baseline survivors | Survival | Deletions / removals | Deletion share | Fixes after known artifacts |
|---|---:|---:|---:|---:|---:|
| All systems | 676/821 | 82.34% | 106/147 | 72.11% | 32 |
| Without istio | 447/592 | 75.51% | 106/147 | 72.11% | 32 |
| Without flux2 | 665/726 | 91.60% | 22/63 | 34.92% | 32 |

| Dataset | Pair rule | N | Chi-square | p | Cramer's V |
|---|---|---:|---:|---:|---:|
| All | any survives | 268 | 6.7285 | 0.081075 | 0.15845 |
| All | all survive | 268 | 30.6324 | 0.000001016 | 0.33808 |
| Without istio | any survives | 207 | 5.7675 | 0.123487 | 0.16692 |
| Without istio | all survive | 207 | 27.5980 | 0.000004411 | 0.36514 |
| Without flux2 | any survives | 246 | 4.9032 | 0.179023 | 0.14118 |
| Without flux2 | all survive | 246 | 32.6113 | 0.000000389 | 0.36410 |

All six tests have three degrees of freedom. The JSON files retain full precision,
contingency tables and expected-cell diagnostics. The any-survives tests have
1, 1 and 4 expected cells below five respectively, so asymptotic p-values require
caution. Pair aggregation removes duplicate tool/check instances within a pair,
but does not remove dependence across categories on one object or within projects.
These are descriptive sensitivity analyses, not causal evidence. Fix counts
exclude the existing known probe artifact rule; they are not newly human-verified fixes.

## Kaplan-Meier interpretation

Each non-`other` tool-specific instance contributes one observation. Time zero is
its first observed presence, including instances introduced after the baseline.
Time is elapsed days based on `data/minor_dates.csv`, aligned to valid tags in
`data/versions.csv`. The event is the first observed removal, including object
deletion and analyzer-related disappearance. A return does not reset the history:
this estimates time to first removal, not recurrent-event survival. If never
removed, the instance is right-censored at its last valid tag. A last-tag arrival
has zero follow-up and is censored at day zero.

Curves report each observed duration, number at risk immediately before that time,
events, censorings and the product-limit survival estimate. Events precede tied
censorings. Before the first listed time survival is 1. Missing dates or invalid
presence alignment are errors; small legacy fixtures without minor_dates.csv do
not generate calendar-time curves.

Baseline instances have unknown prior ages. These curves measure remaining
observed persistence from first observation, not lifetime from actual introduction.
Removal is interval-observed and assigned to the first absent tag; gaps and unequal
sampling affect timing. Pooling heterogeneous, dependent instances and administrative
censoring limit interpretation; curves are descriptive, without inferential confidence
bands. They do not establish how quickly developers fix smells.

## Completion and remaining work

Implemented standard-library KM, pipeline output, a hand-computed five-instance
test, late-entry/censor/reappearance tests, and exclusion tests for both pair rules.
Full local validation uses PyYAML 6.0.3 and a temporary kubectl v1.36.2; the three
analyzer-wrapper integration tests remain skipped because analyzer binaries are absent.

Rerun the commands unchanged after the rendered integration and category-map
adjudication. Rohan supplies the human agreement ledger; Yasaminzahra must make
and record the human adjudication decisions herself under the assignment's no-AI
rating/coding rule. No adjudication or map changes are claimed in this statistics PR.
