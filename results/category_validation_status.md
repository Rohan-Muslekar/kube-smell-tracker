# Category validation status

Last updated: 2026-11-23 (Milestone 4). The procedure is in
[docs/category_validation.md](../docs/category_validation.md); the earlier note from PR #11 is
superseded by this file.

## Sheets so far

| Sheet | Who | How it was made | Result against the map (62 checks) | Output |
|---|---|---|---|---|
| `data/category_validation/llm_rater.csv` | blind LLM (PR #19) | model, prompt in `llm_rater_prompt.txt` | 59 agree, kappa 0.93 | `results/category_validation_llm/` |
| `data/category_validation/category_rater_1.csv` | Ankit (PR #21) | AI-assisted, so not independent | 58 agree, kappa 0.91 | `results/category_validation_rater1/` |
| `data/category_validation/m4_rater2.csv` | Rojan (PR #29) | committed as "AI-assisted category review draft" (commit a44c94e) | 45 agree, kappa 0.64 | `results/category_validation_m4/rater2_vs_map/` |
| `data/category_validation/m4_rater1.csv` | Ankit | to be rated by hand, without AI | pending | |

Rater 2 against the LLM sheet: 47 agree, kappa 0.67 (`results/category_validation_m4/rater2_vs_llm/`).

None of the three completed sheets is an independent human rating. The two that involved AI
agree with the map far more (0.91 to 0.93) than the third (0.64), so agreement measured so far
should not be read as human agreement.

## Where rater 2 and the map differ

All 17 disagreements move a check *into* hygiene or resource:

| Map | Rater 2 | Checks |
|---|---|---|
| resource | hygiene | 10 |
| other | hygiene | 6 |
| other | resource | 1 |

Security (18 of 18) and image (3 of 3) agree completely. The 7 `other` checks are excluded
from every result, so only the 10 resource/hygiene checks could change a number, and they cannot
change the security or image results. The full list is
`results/category_validation_m4/rater2_vs_map/category_disagreements.csv`.

## Remaining

1. A human rating without AI tools (`m4_rater1.csv`), then
   `python3 -m kst.category_validation calculate --rater-1 data/category_validation/m4_rater1.csv --rater-2 data/category_validation/m4_rater2.csv --out results/category_validation_m4/`
   and each sheet against the map.
2. Adjudication of every disagreement in the ledger by Yasaminzahra (not a rater), with the
   rationale per check; `data/check_categories.csv` changes only through that ledger.
3. If the human kappa against the map is below 0.6, per-category claims become descriptive only
   (Milestone 4 report, Table IV).

## Commands

```bash
python3 -m kst.category_validation calculate --rater-1 data/category_validation/map_as_rater.csv \
  --rater-2 data/category_validation/m4_rater2.csv --out results/category_validation_m4/rater2_vs_map
python3 -m kst.category_validation calculate --rater-1 data/category_validation/llm_rater.csv \
  --rater-2 data/category_validation/m4_rater2.csv --out results/category_validation_m4/rater2_vs_llm
```
