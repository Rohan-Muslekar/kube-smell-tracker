# Milestone 4 and Final: Responsibilities (Group 4)

**Covers:** everything from now to the final report.
**Key dates:** Milestone 4 report due Nov 20 (Rohan submits). Presentation on Nov 27 or Dec 4
(our assigned slot). Final report and reproducibility artifact due **Dec 11, 11:59 p.m.**

Read sections 1 to 4 first, then your own task in section 6. Ask in the group chat if anything
is unclear, before you start.

---

## 1. What is left, in one paragraph

Milestone 3 already answered all three research questions on stored manifests. Milestone 4 is
our plan for finishing, and it promises six steps (E1 to E6 below). The final report will be
graded on whether we did them. Nothing new gets added: we rerun the same analysis on
**rendered** manifests, validate the two things a human coded (check categories and RQ3
causes), tighten the statistics, and freeze one reproducible dataset.

## 2. Why these tasks

| Weak point in Milestone 3 | What fixes it | Step |
|---|---|---|
| Main results use stored manifests. Rendering changes one finding: deletions outnumber fixes per object and category (36 vs 24 pairs). | Make `RENDER=1` the default and rerun everything | E1 |
| Rendering adds transitions nobody has traced (48 introductions instead of 41) | Trace them to commits | E2 |
| The category map is checked only by an LLM and an AI-assisted sheet | Two blind **human** ratings, kappa, adjudication | E3 |
| Every RQ3 cause was coded by one person | Second coder on 20 rows, kappa | E4 |
| Fix ages are medians of left-censored data; the category test treats dependent instances as independent | Kaplan–Meier survival curves, pair-level tests, runs without istio and without flux2 | E5 |
| The final numbers must regenerate from one command | Tag `final-data`, fresh clone on two machines | E6 |

**Already checked (Nov 19):** `RENDER=1` on flux2 and microservices-demo works. All 22 tags
are valid, and flux2 matches the Milestone 3 rendering check exactly. The only difference is
microservices-demo's `loadgenerator.yaml`: its `kustomization.yaml` comments the file out, but
`render.py` still lints it as a plain file (16 extra instances). Rojan's first fix below
handles this.

## 3. Work in parallel: nobody waits for a peer

Every task below starts **today** and needs only what is already on `master` (or a file in
this PR). No member waits for another member. The only person who joins the pieces is Rohan,
at the integration run and the number freeze.

```
Track A  Rojan         renderer fixes + RENDER=1 default; rater 2       ─┐
Track B  Ankit         compare_render.py, CI; rater 1                   ─┤
Track C  Yasaminzahra  Kaplan–Meier + --exclude sensitivity             ─┼─> Rohan: integration run (Nov 23)
Track D  Bayan         second coder (E4); rendered tracing (E2)         ─┤          kappa, numbers, freeze (Nov 25)
Track E  Rohan         Milestone 4 report; reviews; merges              ─┘
```

How the old dependencies were removed:

| Used to wait for | Now |
|---|---|
| Bayan's tracing waited for the integration run | The rendered transitions are already known from the Nov 19 run: `data/rq3_rendered_todo.csv` (21 rows) |
| Ankit's comparison waited for rendered data | The script takes any two `out/` folders; Ankit makes rendered data himself in 3 minutes (`RENDER=1 ./scripts/collect.sh flux2`) or tests on fixtures |
| Ankit reviewed Rojan's PR | Rohan reviews every PR |
| Raters waited for Yasaminzahra's sheets | Each rater makes their own blank sheet with one command |
| Kappa waited for both sheets | Rohan runs `calculate` (one command) when both are in; Yasaminzahra's code does not depend on it |
| Yasaminzahra's statistics waited for rendered `out/` | The code reads whatever `out/` holds; build and test it on today's data, it reruns unchanged on the rendered data |

## 4. Schedule

| Date | What | Who |
|---|---|---|
| Nov 22 | Track A merged: renderer fixes, `RENDER=1` default | Rojan |
| Nov 23 | Both rating sheets in the repo | Ankit, Rojan |
| Nov 23 | Track B merged: `compare_render.py`, CI | Ankit |
| Nov 23 | Integration run on rendered data; kappa from the two sheets | Rohan |
| Nov 24 | Track D merged: second-coder sheet, kappa, rendered traces | Bayan |
| Nov 24 | Track C merged: Kaplan–Meier, sensitivity runs | Yasaminzahra |
| Nov 24 | Adjudicate the category disagreements (the one task after others) | Yasaminzahra |
| Nov 25, 20:00 | **Number freeze.** Each person sends their slide(s) | all |
| Nov 26 | Rehearsal (full run-through, timed) | all |
| Nov 27 / Dec 4 | Presentation | all |
| Dec 1 | Fresh clone on Fedora and WSL from tag `final-data` | Rohan, Ankit |
| Dec 8 | Final report draft; each person checks their own part by Dec 9 | Rohan; all |
| Dec 11 | Submit report and artifact | Rohan |

If you will miss a date, say so in the chat **before** it passes. Every task has a fallback
(section 6), so a late task makes the report weaker but never blocks anyone else.

## 5. How to work

- One branch and one PR per task. Branch names are given below. Rohan merges.
- CI must pass. Never edit `out/` by hand: regenerate it with `python3 -m kst`.
- Every PR adds or updates tests for any code it changes (`python3 -m pytest -q`).
- **Ratings and coding are done by you, without AI tools.** In Milestone 3 we could only report
  an LLM rating and an AI-assisted sheet, which is not independent. A human rating is the whole
  point of E3 and E4.
- Do not open earlier rating sheets or the map before you finish your own sheet
  (`data/check_categories.csv`, `data/category_validation/`, `results/category_validation_*`).
- When you finish, send in the chat: the PR link, the result in two or three lines, and
  anything that did not work. That text goes into the contribution table.

## 6. Tasks

### Track A. Seyedeh Rojan Razavi: rendering as the default (E1) and rater 2 (E3)

**Goal.** One command (`make all`) produces rendered results that match the rendering check.

**Steps.**
1. **Unreferenced files.** In `kst/render.py`, a YAML file inside a rendered kustomization's
   directory that the kustomization does not reference (via `resources`, `patches`,
   `components` and the like) is not deployed, so exclude it from linting. Log it to
   `raw/skipped_files.txt` with reason `not referenced by kustomization`. Test case:
   microservices-demo `kubernetes-manifests/loadgenerator.yaml` (commented out of
   `kubernetes-manifests/kustomization.yaml`). Add a fixture to `tests/test_render.py`.
2. **Relative paths.** `raw/objects/<repo>__<tag>.tsv` currently stores absolute paths
   (`/home/.../work/rendered/...`), so two machines never produce identical files. Write
   paths relative to the repository root (`work/rendered/flux2__v2.5.1/manifests__crds.yaml`).
   Add a test.
3. **Skip reasons.** With `RENDER=1`, every file that is not linted must appear in
   `raw/skipped_files.txt` with a reason: consumed by a kustomization, not referenced, or
   render failed.
4. **Default on.** Make `RENDER=1` the default in `Makefile` and `scripts/collect.sh`
   (`RENDER=0` keeps the old behaviour). Update the README: PyYAML 6.0.3 is required for
   collection; the offline analysis (`python3 -m kst`) still uses the standard library only.
5. **Check.** On flux2 and microservices-demo, run
   `./scripts/collect.sh flux2 && ./scripts/collect.sh microservices-demo && python3 -m kst`
   and confirm the totals: 911 instances overall, flux2 162 instances and 116 removals. Put the
   numbers in the PR description.
6. **Rater 2 (E3, by Nov 23, about 1 hour).** Make your own blank sheet:
   `python3 -m kst.category_validation prepare --out /tmp/sheet` and rate
   `/tmp/sheet/category_rater_2.csv` on your own, without AI, using only the check definitions and
   the analyzer documentation. Commit it as `data/category_validation/m4_rater2.csv`.

**Files:** `kst/render.py`, `scripts/collect.sh`, `Makefile`, `README.md`,
`tests/test_render.py`, `tests/fixtures/`.
**Branch:** `feat/render-default`.
**Fallback:** if a fix is not ready by Nov 22, Rohan uses the rendering check script
(`scripts/render_check.py`, commit `1e314b0`) for the rendered numbers.

### Track B. Ankit Suman: stored-vs-rendered comparison, CI, reproduction (E1, E6) and rater 1 (E3)

**Goal.** Show exactly what rendering changes, keep CI green on the rendered data, and prove
that a stranger can regenerate it.

**Steps.**
1. **CI.** Install PyYAML in the workflow so that `tests/test_render.py` runs in CI. CI keeps
   rerunning the offline analysis and fails if `out/` changes.
2. **`scripts/compare_render.py --stored <dir> --rendered <dir>`.** Each `<dir>` is a
   repository folder with `out/` and `raw/objects/`. Per system, report objects, instances,
   survival, removals, deletion share, real fixes and reappearances, stored vs rendered, and
   write `results/render_comparison.csv`. Test it on a tiny fixture. To try it on real data
   without waiting for anyone: copy your clone, run `RENDER=1 ./scripts/collect.sh flux2 &&
   python3 -m kst` in the copy (about 3 minutes), and compare it with your normal clone. Expected:
   flux2 97 vs 162 instances, 84 vs 116 removals. After Rohan's integration run, the same command
   compares tag `milestone-3-data` with `master`.
3. **Rater 1 again (E3, by Nov 23, about 1 hour).** Make your own blank sheet
   (`python3 -m kst.category_validation prepare --out /tmp/sheet`) and rate
   `/tmp/sheet/category_rater_1.csv` by hand, without
   AI and without opening your earlier sheet, the map or the LLM sheet. Commit it as
   `data/category_validation/m4_rater1.csv`.
4. **Fresh clone (E6, Dec 1).** On WSL: clone the repository at tag `final-data`, run
   `./tools/install.sh && make all && python3 -m kst`, and `diff -r` `out/` and
   `data/versions.csv` against the tag. Record the time taken and any differences in
   `docs/reproduction.md`.

**Files:** `.github/workflows/`, `scripts/compare_render.py`, `tests/`, `docs/reproduction.md`.
**Branch:** `feat/compare-render`.
**Fallback:** if the comparison is late, Rohan reports the rendering check table from Milestone 3. If WSL cannot run kubectl, record the error. The Fedora rerun stands alone.

### Track C. Yasaminzahra Valitabar: final statistics (E5) and adjudication (E3)

**Goal.** Human agreement on the category map, and statistics that do not overstate the
evidence.

**Steps.**
Build steps 1 and 2 on today's `out/`; they rerun unchanged on the rendered data.

1. **Kaplan–Meier (E5).** Add a standard-library function, for example `kst/survival_km.py`, that
   estimates the survival of smell instances per category and per system. An instance is
   "at risk" from the first tag where it appears; its "event" is removal; instances still
   present at the last tag are censored. Write the curve points to `out/km_by_category.csv` and
   `out/km_by_system.csv`. Test it on a hand-computed example of five instances.
2. **Sensitivity runs (E5).** `scripts/report_numbers.py` already computes the chi-square and
   Cramér's V on object–category pairs under both pair rules ("any instance survives" and "all
   survive"). Add a `--exclude <repo>` option so every headline number (survival, deletion
   share, fixes, both tests) can be recomputed without istio and without flux2. Test it.
3. **Adjudication (Nov 24, the only step that comes after others).** When Rohan has run
   `calculate` on the two sheets, decide each disagreement in the ledger (decision and
   rationale per check). If the adjudicated category differs from the map, update
   `data/check_categories.csv` in the same PR. You built the validation tooling and are not a
   rater, so you are the right adjudicator.
4. Send the curves, the sensitivity numbers and the adjudicated changes in the chat by Nov 25.

**Files:** `kst/category_validation.py` (if needed), `results/category_validation_m4/`,
`data/check_categories.csv`, a new `kst/survival_km.py`, `scripts/report_numbers.py`, `tests/`.
**Branches:** `feat/category-agreement`, `feat/km-survival`.
**Fallback:** if one sheet is missing, report the other rater against the map, labelled as a
single human rating. If Kaplan–Meier is not done, Rohan reports the share surviving per year.

### Track D. Bayan Sayyadifar: second coder (E4) and rendered transitions (E2)

**Goal.** A second, independent reading of the RQ3 causes, and causes for the transitions
that rendering adds.

**Steps.**
1. **Sample (today).** Write `scripts/sample_rq3_recode.py`. It draws 20 rows from
   `data/rq3_investigations.csv` with seed 5570, stratified by `classification`
   (real_fix, side_effect_of_fix, analyzer_artifact, new_object, object_deleted; at least 2 per
   class). It writes `data/rq3_recode_sheet.csv` with the row key, the tags, the commit
   URL and an **empty** `classification` column. It must not copy the first coder's code or
   notes, and it must refuse to overwrite an existing sheet. Add a test.
2. **Recode (by Nov 24).** For each row, open the commit diff and the YAML at both tags, then
   choose the class using the codebook in Milestone 3 (real fix: the diff changes the setting
   the check reads; side effect: a commit made for another reason adds the smell; new object;
   analyzer artifact; object deleted). Do it yourself, without AI, and without looking at the
   original rows.
3. **Agreement.** Add `scripts/rq3_agreement.py`, which compares your sheet with the original
   rows and prints agreement and Cohen's kappa. Reuse the kappa function in
   `kst/category_validation.py`; don't write a new one. List the disagreements. Rohan and you
   resolve each one using the evidence link.
4. **Rendered transitions (E2, start now).** `data/rq3_rendered_todo.csv` lists every
   transition that rendering adds and nobody has traced (from the rendered run on Nov 19):
   - 9 introductions on two new flux2 objects: the `flux-edit` and `flux-view` ClusterRoles
     (v0.39.0 to v0.40.2) and the `source-watcher` Deployment (v2.6.4 to v2.7.5);
   - 12 deleted objects (116 smells): flux2's credentials-sync CronJobs, Deployments and
     RoleBindings, all v2.6.4 to v2.7.5. Confirm whether commit 9cad95d (Milestone 3) removes
     them.

   flux2's rendered objects come from its kustomizations, so look at
   `git log <from>..<to> -- manifests/` in flux2 and the kustomization that pulls the object in.
   Add one row per transition (or per deleted object) to `data/rq3_investigations.csv` with the
   commit, configuration change, evidence URL and class. Run `python3 scripts/check_rq3.py`;
   it must pass.
5. **Presentation (by Nov 25).** Prepare the RQ3 slide with the three cases (argo-cd Redis
   authentication fix, istio `runAsUser` removal, microservices-demo ServiceAccount refactoring).

**Files:** `scripts/sample_rq3_recode.py`, `scripts/rq3_agreement.py`, `data/rq3_recode_sheet.csv`,
`data/rq3_investigations.csv`, `tests/`.
**Branches:** `feat/rq3-second-coder`, `data/rq3-rendered`.
**Fallback:** if tracing runs late, trace the rendered transitions per commit (one row per
commit instead of per smell) and say so in the report.

### Track E. Rohan Muslekar: integration run, kappa, numbers, report

**Steps.**
1. **Milestone 4 report** (due Nov 20).
2. **Before the integration run**, tag the current master as `milestone-3-data`.
3. **Review and merge** every PR within a day (no peer waits for a peer review).
4. **Integration run (Nov 23)**, after Track A is merged: `make all`, check that
   `data/versions.csv` has no invalid tags, commit `raw/`, `out/` and `data/versions.csv`, and
   compare with the rendering check using Ankit's `compare_render.py`. If the run shows a
   transition that is not in `data/rq3_rendered_todo.csv`, trace it yourself.
5. **Kappa (Nov 23)**: `python3 -m kst.category_validation calculate --rater-1
   data/category_validation/m4_rater1.csv --rater-2
   data/category_validation/m4_rater2.csv --out results/category_validation_m4/`, plus
   each rater against the LLM sheet. Hand the disagreements to Yasaminzahra.
6. **Number freeze (Nov 25)**: regenerate every number with `scripts/report_numbers.py --out`,
   build the slides from them, and assemble everyone's slides.
7. **Final data (by Dec 1)**: make `RENDER=1` the default in the `report_numbers.py` inputs,
   tag `final-data`, and do the Fedora fresh clone.
8. **Final report**: draft by Dec 8, apply everyone's checks, submit on Dec 11.

## 7. Presentation

Each person presents the part they built:

| Part | Who |
|---|---|
| Question, systems, pipeline | Rohan |
| Rendering: what it changes | Rojan |
| RQ1 and RQ2 results, survival | Yasaminzahra |
| RQ3 cases and causes | Bayan |
| Validation and reproducibility | Ankit |

Slides use the frozen numbers only. Anything unfinished on Nov 25 is presented as work in
progress, with its fallback.

## 8. Final report

Rohan writes it. By Dec 9, each person checks the sections about their own work: every number
must match `out/`, and every claim must have an artifact link. Unfinished tasks become
limitations, stated plainly. Nothing in the report is retyped by hand; tables and numbers come
from `report_numbers.py`.
