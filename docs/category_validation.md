# Independent category validation

Coordinator: Yasaminzahra Valitabar. Status: rating sheets prepared; independent
ratings, agreement results and adjudicated decisions are pending.

## Procedure

1. Freeze the repository commit and `data/check_categories.csv` used for the review.
   Record that commit, both rater names and review dates in the final results note.
2. Assign two people, each receiving only their own sheet from
   `data/category_validation/category_rater_1.csv` or `category_rater_2.csv`.
   Do not share the existing mapping, its rationale, or the other person's answers
   during independent rating. Disclose prior exposure to the mapping if applicable.
3. Each person reviews every `(tool, check)` using the pinned analyzer's check
   documentation/source and records their name, one category and a rationale
   with a source reference. Discuss category definitions before rating, not answers.
4. Return both completed sheets to the coordinator. Preserve the original sheets.
   Calculate agreement before discussing differences:

   ```bash
   python -m kst.category_validation calculate --rater-1 data/category_validation/category_rater_1.csv --rater-2 data/category_validation/category_rater_2.csv --out results/category_validation
   ```

5. Review `category_disagreements.csv` together. Fill `adjudicated_category`,
   `decision_rationale`, `adjudicator`, and `date` for each disagreement; preserve
   both original ratings. If unresolved, involve a third team member and record
   the decision. Compare all agreed/adjudicated categories with the original map,
   including checks where both raters agreed on a different category.
6. Update `data/check_categories.csv` with the approved categories and rationale.
   Run the tests and analysis again, inspect changed outputs and document their
   effect on prevalence and category-level summaries. Check-ID instance identity
   remains unchanged; changing `other` membership changes the smell totals.

## Shared category definitions

| Category | Primary concern |
|---|---|
| `security` | Permissions, privilege, secret exposure and security isolation |
| `resource` | Resource allocation, availability, probes and runtime reliability |
| `image` | Image references, versions, pull policy and supply-chain configuration |
| `hygiene` | Namespace/reference consistency and configuration maintainability |
| `other` | Style or opinionated policies outside the four smell categories |

For overlapping checks, choose the primary consequence and explain the boundary.
Rate `other` as well: exclusion from the analysis needs independent validation.

## Agreement calculation

The unit is a unique `(tool, check)`, with equal weight for each check, including
`other`. Percentage agreement is `100 * matches / N`. Cohen's unweighted kappa
is `(Po - Pe) / (1 - Pe)`, where `Po = matches / N` and
`Pe = sum(count_rater1[c] * count_rater2[c]) / N²` over the five categories.
If `Pe = 1`, kappa is undefined and is written as JSON `null`, not zero or one.

The calculator rejects missing/duplicate checks, blank or invalid ratings,
missing rationale and identical rater names. It cannot prove independence;
the procedure and disclosed review history establish that. It refuses to overwrite
existing result files so that adjudication notes are preserved.

No empirical agreement value is reported yet. The automated calculation test
uses synthetic ratings with 75% agreement and kappa 0.5; those are test values,
not this study's results.

To regenerate blank sheets for a changed map, use a new directory:

```bash
python -m kst.category_validation prepare --out data/category_validation_next
```

## Coordination message

“Please independently classify every check in your assigned CSV using the five
definitions above and the pinned tool documentation. Add your name and a short
source-backed rationale for each row. Do not consult the existing category map or
the other rater's answers. Send the completed sheet to Yasaminzahra before we
discuss disagreements. We will agree on a return date before starting.”
