# Category validation status

Last updated: 2026-11-23 (Milestone 4). The procedure is in
[docs/category_validation.md](../docs/category_validation.md); the earlier note from PR #11 is
superseded by this file.

## Sheets so far

| Sheet | Who | How it was made | Result against the map (62 checks) | Output |
|---|---|---|---|---|
| `data/category_validation/llm_rater.csv` | blind LLM (PR #19) | Claude Opus 5.5; prompt in `llm_rater_prompt.txt` | 59 agree, kappa 0.93 | `results/category_validation_llm/` |
| `data/category_validation/category_rater_1.csv` | Ankit (PR #21) | AI-assisted, so not independent | 58 agree, kappa 0.91 | `results/category_validation_rater1/` |
| `data/category_validation/m4_rater2.csv` | Rojan (PR #29) | committed as "AI-assisted category review draft" (commit a44c94e) | 45 agree, kappa 0.64 | `results/category_validation_m4/rater2_vs_map/` |
| `data/category_validation/m4_rater1.csv` | filed under Ankit (PR #37, replaced) | AI-assisted, so not independent | 53 agree, kappa 0.80 | `results/category_validation_m4/rater1_vs_map/` |
| `data/category_validation/m4_rater3.csv` | filed under Rohan (PR #37, replaced) | AI-assisted, so not independent | 60 agree, kappa 0.96 | `results/category_validation_m4/rater3_vs_map/` |

Rater 2 against the LLM sheet: 47 agree, kappa 0.67 (`results/category_validation_m4/rater2_vs_llm/`).

The two AI-assisted Milestone 4 sheets agree with each other on 55 of 62 checks, kappa 0.85
(`results/category_validation_m4/rater1_vs_rater3/`). The sheets first merged in #37 were
described as hand-made; they were AI-generated, and this branch replaces them with AI-assisted
sheets labelled as such. No independent human category rating exists yet.

Against the other sheets: m4_rater1 56 agree with the LLM (kappa 0.87) and 43 with rater 2 (0.60);
m4_rater3 61 with the LLM (0.98) and 46 with rater 2 (0.65).

The category sensitivity (`results/category_sensitivity.csv`) includes both sheets: security
keeps 23 fixes (rate 0.095) and resource stays at most 0.013 under every sheet.

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

1. Open: an independent human rating on a blank sheet from `prepare`, made without AI.
2. Open: human adjudication of its disagreements. The #38 adjudication was drafted from the
   AI-generated sheets and is reverted; `data/check_categories.csv` is back to the Milestone 3 map.
3. If the human kappa against the map is below 0.6, per-category claims become descriptive only
   (Milestone 4 report, Table III).

## Commands

```bash
python3 -m kst.category_validation calculate --rater-1 data/category_validation/map_as_rater.csv \
  --rater-2 data/category_validation/m4_rater2.csv --out results/category_validation_m4/rater2_vs_map
python3 -m kst.category_validation calculate --rater-1 data/category_validation/llm_rater.csv \
  --rater-2 data/category_validation/m4_rater2.csv --out results/category_validation_m4/rater2_vs_llm
```

The commands for the m4_rater1/m4_rater3 sheets are in [m4_commands.md](m4_commands.md), section E3.
