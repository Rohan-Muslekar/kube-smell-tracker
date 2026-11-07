# Category validation result note

Prepared against master `fc84c26`. Blank independent sheets were generated outside
the repository with:

```powershell
python -m kst.category_validation prepare --out C:\Users\yasam\category-sheets
```

Each sheet covers the 62 mapped checks, without the current category or rationale.
Sheet 1 is for Ankit; sheet 2 is for Rojan. Private delivery and both returned
ratings are pending. Percentage agreement, Cohen's kappa and the final number of
changed categories are therefore **not yet available**. No category-map changes
have been made without ratings and adjudication.

The calculator now prepares `category_map_differences.csv` as a single decision
ledger covering both rater disagreements and jointly agreed departures from the
original map, with final-category, reason, adjudicator and date fields. Agreement
is still calculated before adjudication. Original ratings are retained unchanged.

After both sheets return, run:

```bash
python -m kst.category_validation calculate --rater-1 data/category_validation/category_rater_1.csv --rater-2 data/category_validation/category_rater_2.csv --out results/category_validation
```

Complete all ledger decisions, count final categories differing from the original
map, and update the approved mapping in the same PR. Post those numbers and this
command to Rohan before the freeze. If only one sheet returns, report the missing
second rating explicitly; two-rater agreement cannot be calculated from one rater.
