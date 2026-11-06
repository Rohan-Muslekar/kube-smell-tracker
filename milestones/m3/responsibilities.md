# Milestone 3: Responsibilities (Group 4)

**Due:** Sunday, November 8, 2026, 11:59 p.m. (report submitted by Rohan at 23:00).
**Deliverable:** one PDF, IEEE conference template, at most 5 pages excluding references, plus
the link to this repository.

Read sections 1 to 4 first: they explain where the project stands and why each task exists.
Then read your own task in section 6. If something is unclear, ask in the group chat before
you start, not at 16:00.

---

## 1. What Milestone 3 asks for

Milestone 3 is the *Preliminary Evidence Report*. It is graded on five things:

| Rubric item | Points | What earns full marks |
|---|---|---|
| Research questions and progress | 10 | Every change since Milestone 2 is justified, and each research question points to the table or figure that answers it. |
| Methods executed | 20 | Everything we actually ran is documented (data, tools, settings), deviations from the plan are stated, and the repository lets someone else rerun our numbers. |
| Preliminary findings | 35 | Results from real data answer at least one question, with tables or figures that show variation (for example, per system). |
| Interpretation and validity | 20 | Claims are no stronger than the evidence, surprising results are explained, and the strongest threat to validity is named **together with a check we have already run**. |
| Remaining work and contributions | 15 | A realistic plan with fallbacks, and a table of what each member completed, with links to the work. |

We decided to do the full analysis in this milestone, so that Milestone 4 is only polishing
(final number check, final report, presentation). That makes tomorrow a full day, which is why
there is a fallback in section 4.

## 2. Where the project stands after Milestone 2

**The study.** We take seven open-source projects that ship Kubernetes YAML (argo-cd, flux2,
istio Bookinfo, Knative serving, kube-prometheus, microservices-demo, Tekton pipeline). For each
we check out five release tags spread over about four years. At each tag we run two static
analyzers, kube-linter and kube-score, and treat their warnings as *configuration smells*. We
then follow each individual smell from one tag to the next to see whether it stays, goes away,
or comes back.

**Research questions.**
- RQ1 (supporting): which smell categories occur, and how often?
- RQ2 (primary): do individual smells persist, disappear, or reappear between releases?
- RQ3 (primary): what change in the project caused a smell to appear or disappear?
- RQ4 (image CVEs) is being dropped. The report states this as a scope reduction.

**How the pipeline works.** Each step is a file in this repository:

```
data/repos.json           which repos, which folders, which tags
  -> scripts/collect.sh   clone, check out each tag, keep plain Kubernetes YAML (kst/manifests.py)
  -> kst/inventory.py     list every object (kind, namespace, name) defined at that tag
  -> scripts/analyze.sh   run kube-linter and kube-score  -> raw/kube-linter/, raw/kube-score/
  -> kst/validate.py      mark a tag invalid if an analyzer crashed or printed nothing
  -> python3 -m kst       normalize -> track -> tables      -> out/*.csv
       kst/normalize.py   one row per finding; check mapped to a category (data/check_categories.csv)
       kst/track.py       follow each smell across tags and label every step
       kst/overlap.py     where the two analyzers agree or disagree
```

`make all` runs everything (needs network). `python3 -m kst` reruns only the analysis from the
committed `raw/` folder (no network). `python3 -m pytest` runs the 83 tests. CI reruns the tests
and the analysis on every push and fails if `out/` changes.

**Terms used below.**
- *Smell instance*: one smell on one object, identified by (project, tool, kind, namespace,
  name, check). The file path is not part of it, so moving an object between files keeps its
  history.
- *Transition*: what happens to an instance between two consecutive sampled tags: persisted,
  introduced, removed, or reappeared (present again after it was removed).
- *Object deletion vs. fix*: if a smell is removed because the whole object was deleted, it is
  not a fix. The object inventory tells the two apart.
- *Rendering*: kustomize and Helm keep configuration as templates or base files plus patches.
  "Rendering" means running `kubectl kustomize` or `helm template` to produce the final,
  complete objects that would actually be deployed.

**What Milestone 2 found.**
- 862 smell instances. 82.3% of the smells present at a project's first tag are still there at
  its last tag, three to four years later. Smells are sticky.
- 147 removals, but 108 (73.5%) happened because the object was deleted, not because the smell
  was fixed. 84 of those 108 come from one place: flux2's credential-sync integrations.
- Only 30 removals are real fixes once one analyzer quirk is set aside. Only 4 of those 30 have
  been traced to the commit that fixed them.
- No smell ever reappeared.
- The two analyzers agree on 55.6% of object-category pairs (78.5% without hygiene checks).

## 3. Why these tasks: the weak points in the current evidence

Each task below fixes one weak point that a reader (or the instructor) would raise.

| Weak point | Why it matters | Task that fixes it | Owner |
|---|---|---|---|
| **flux2 is linted unrendered.** flux2's manifests are kustomize bases and patch files. We lint the patch fragments as if they were whole objects. | The headline "removals are mostly deletions" rests on 84 flux2 deletions of patch fragments. If rendering changes this, the finding changes. **This is our strongest validity threat.** | Render kustomize before linting; compare rendered vs. unrendered. | Rojan, with Ankit |
| **Only five tags per project.** A smell removed and re-added between two sampled tags looks like it never changed. | "No smell ever reappeared" could be an artifact of sampling. | Use every minor release (123 tags instead of 35). | Rohan |
| **A renamed object looks like a removal plus an introduction.** | It inflates both "removed" and "introduced" and hides real history. | Detect probable renames in tracking. | Yasaminzahra |
| **The check-to-category map was made by one person.** | The categories in every table depend on it. | Two independent raters, Cohen's kappa, and adjudication. | Yasaminzahra, raters Ankit and Rojan |
| **Only 4 of 30 fixes are explained.** | RQ3 is a primary question and is barely answered. | Trace every fix and introduction to its commit. | Bayan |
| **No figure shows variation between projects.** | The findings rubric asks for variation. | Survival figure per project. | Bayan |
| **Reproduction of the new data is unchecked.** | The methods rubric asks that others can rerun our results. | Fresh-clone reproduction and CI on the new data. | Ankit |

## 4. How the day runs

Rendering and denser tags both change the raw data, so every number in the report changes once
they land. To avoid five people analysing five different datasets, there is **one integration
run** after all code is merged, and all analysis afterwards uses its output.

| When | What happens |
|---|---|
| **Nov 7, tonight** | Everyone opens their code PR (rendering, denser tags, rename detection, rendered-input support). Raters fill in the category sheets. Bayan traces the remaining fixes in the Milestone 2 data. |
| **Nov 8, 10:00** | Rohan merges all code PRs. Before merging, Rohan tags the current `master` as `milestone-2-data`, so the Milestone 2 dataset stays reproducible with `git checkout milestone-2-data`. |
| **Nov 8, 10:00 to 12:00** | **Integration run** (Rohan): `RENDER=1 make all` with the dense tag list, then commit the new `raw/`, `out/` and `data/versions.csv`. Everyone pulls `master` after this. |
| **Nov 8, 12:00 to 17:00** | Analysis on the new data (rendering comparison, dense-tag reappearances, rename check, new commit tracing, reproduction, figure). |
| **Nov 8, 17:00** | **Numbers freeze.** Everyone sends their result note (section 5) to Rohan. Nothing that changes `out/` is merged after this. |
| **Nov 8, 17:00 to 20:00** | Rohan regenerates the report tables and finishes the draft. |
| **Nov 8, 20:00** | Everyone reads the draft and checks the part about their own work. |
| **Nov 8, 23:00** | Rohan submits. |

**Fallback.** If the integration run is not committed by 12:00, the report uses the Milestone
2 data. Rendering and denser tags are then reported as checks on a subset (flux2 rendered at its
five tags; one project with dense tags), and the full runs are listed as Milestone 4 work. The
submission never waits on the risky parts.

## 5. How to work

- **Branches and PRs.** Branch from `master`, one PR per task, named in your task below. Rohan
  reviews and merges. Use a Conventional Commits prefix in commit messages (`feat:`, `fix:`,
  `docs:`, `test:`).
- **Tests.** New code comes with tests under `tests/`, and `python3 -m pytest` must pass before
  you ask for review. Small fixtures go under `tests/fixtures/`.
- **Generated data.** Do not commit changes to `raw/`, `out/` or `data/versions.csv` in your
  code PR. Only the integration run commits those, so CI stays consistent.
- **Docs.** If you change how something works, update the `docs/` file you own (section 7) in
  the same PR.
- **Result note.** By 17:00, send Rohan a short message with:
  1. the numbers the report needs (listed under "Hand-off" in your task);
  2. the exact command that produced them, so the report can say how to rerun them;
  3. two or three lines on what you did, with PR links, for the contribution table.

## 6. Tasks

### Rohan Muslekar: denser tags, integration run, report

**Goal.** Sample every minor release instead of five, run the full pipeline once on the final
configuration, and write the report.

**Steps.**
1. In `kst/select_tags.py`, add a dense mode (for example `--all`) that prints the latest patch
   of **every** minor release in the same window (minors first released on or after
   2022-10-22). Keep the five-tag mode as the default, so Milestone 2 still reproduces.
   - Pin the dataset. For minors already sampled in Milestone 2, keep the Milestone 2 tag. For
     the others, take the latest patch released on or before 2026-10-22. This stops the dataset
     from moving when projects publish new patches.
   - This gives about 123 tags: microservices-demo 6, kube-prometheus 8, argo-cd 16, flux2 16,
     istio 16, serving 15, pipeline 46.
2. Write the dense tag lists into `data/repos.json` (the `tags` field), and record the mode and
   date used. Add tests for the dense mode in `tests/test_select_tags.py`.
3. At 10:00, tag `master` as `milestone-2-data`, merge all code PRs, then run
   `RENDER=1 make all`. Check that `data/versions.csv` has no unexpected invalid tags, then
   commit the new `raw/`, `out/` and `data/versions.csv`. Tell the group when it is pushed.
4. Dense-tag check: count reappearances in the new `out/instances.csv`, and compare them with
   the same projects restricted to the five Milestone 2 tags. To restrict, copy `data/` to a
   temporary folder, keep only those tags in `versions.csv`, and run
   `python3 -m kst --data <tmp>/data --out <tmp>/out`.
5. Report: write `milestone3.tex`, regenerate tables with `make_tables.py`, build the PDF, and
   fill the contribution table from everyone's result notes.

**Files:** `kst/select_tags.py`, `data/repos.json`, `tests/test_select_tags.py`,
`README.md` (study systems section).
**Branch:** `feat/dense-tags`.
**Hand-off:** tags per project; reappearances with dense tags vs. five tags.
**Fallback:** dense tags for argo-cd only, analysed separately.

### Seyedeh Rojan Razavi: rendering kustomize manifests

**Goal.** Lint the objects that would actually be deployed, not the kustomize patch fragments,
and measure how much that changes our results.

**Background.** Today `kst/manifests.py` skips every `kustomization.yaml` (124 skipped files,
119 of them in flux2) and lints the remaining files one by one. In flux2 many of those files are
patches that only make sense after kustomize merges them into a base. `kubectl kustomize <dir>`
does that merge and prints the complete objects. You only need `kubectl` (kustomize is built
in; tested with kubectl v1.36.2, which bundles kustomize v5.8.1, on flux2 v2.5.1
`manifests/openshift`: 40 objects rendered). The separate `kustomize` binary is not needed. No included project uses Helm charts (the Helm-only
projects were excluded in Milestone 2), so Helm support is optional (step 6).

**Steps.**
1. Create `kst/render.py`. Given a checked-out repo and its manifest paths, find the
   `kustomization.yaml` files and render them with `kubectl kustomize <dir>`. Write each
   rendered output as one YAML file under `work/rendered/<repo>__<tag>/`, keeping the source
   directory in the file name, so file paths in the results still say where an object came
   from.
2. Avoid counting objects twice. Render only *top-level* kustomizations, meaning those that no
   other kustomization lists under `resources`. Drop the plain files that a rendered
   kustomization consumes (its resources and patches) from the list of files to lint. Files
   outside any kustomization are linted as before.
3. In `scripts/collect.sh`, add a `RENDER=1` environment flag. When set, call `kst/render.py`
   after checkout and pass the rendered files plus the remaining plain files to the inventory
   and to `analyze.sh`. When not set, behave exactly as now, so the Milestone 2 run still
   reproduces. If rendering fails for a directory, log it to `raw/skipped_files.txt` with the
   reason `render failed` rather than stopping the run.
4. Tests in `tests/test_render.py`, with a tiny fixture under `tests/fixtures/kustomize/`: one
   base Deployment plus one patch. Assert that:
   - the rendered output contains one complete Deployment;
   - the patch file is no longer linted on its own;
   - the inventory of the rendered output lists the same object the analyzers report.
5. After the integration run, write `scripts/compare_render.py`. It compares, per project, the
   Milestone 2 results (unrendered; read with `git show milestone-2-data:out/...`) with the new
   rendered results restricted to the same five tags (use the same restriction as Rohan's step 4). For each project, print:
   - objects;
   - smell instances;
   - removals;
   - removals by object deletion;
   - real fixes.

   This table goes into the report's validity section.
6. Optional, only if everything above is merged: Helm rendering with `helm template` in the
   same module, for future use.
7. Update `docs/methodology.md` (how rendering works, which files are dropped) and
   `docs/limitations_and_validity.md` (what the comparison showed).

**Files:** new `kst/render.py`, `tests/test_render.py`, `tests/fixtures/kustomize/`,
`scripts/compare_render.py`, the flag in `scripts/collect.sh`.
**Branch:** `feat/render-kustomize`.
**Works with:** Ankit, who makes `analyze.sh` and `validate.py` accept the rendered files. Agree
tonight on where rendered files are written.
**Hand-off:** the comparison table, plus one sentence on whether "removals are mostly
deletions" still holds after rendering.
**Fallback:** render flux2's five Milestone 2 tags by hand with `kubectl kustomize`, run both
analyzers on the output, and report the same numbers; the module moves to Milestone 4.
**Also tonight:** fill in category sheet 2 from Yasaminzahra (about 45 minutes; see her task).

### Ankit Suman: analyzers on rendered output, CI, reproduction

**Goal.** Make sure the analyzers and validation handle the rendered files, keep CI green on the
new data, and prove that someone else can reproduce the new results.

**Steps.**
1. With Rojan tonight: make `scripts/analyze.sh` and `kst/validate.py` work on files under
   `work/rendered/`. Paths in raw output must stay relative to the repository, as they are now
   (`collect.sh` strips the clone path; make sure rendered paths are stripped the same way).
   Add a test in `tests/test_analyze.py` that runs the wrapper on a rendered fixture.
2. CI (`.github/workflows/`): once the integration run is committed, check that CI passes on the
   new `raw/` and `out/`. If the runtime grows with 123 tags, keep it under the CI limits.
3. After the integration run, do a **fresh-clone reproduction** of the new `master` on Fedora
   and on WSL:
   ```bash
   git clone git@github.com:Rohan-Muslekar/kube-smell-tracker.git /tmp/kst-fresh
   cd /tmp/kst-fresh && ./tools/install.sh && RENDER=1 make all
   diff -ru <your working copy>/out /tmp/kst-fresh/out
   ```
   Record what matches and what differs in `docs/reproduction.md`.
4. Finish the open WSL comparison from Milestone 2: kube-linter `dangling-servicemonitor`
   reports for kube-prometheus v0.12.0.
5. Tonight: fill in category sheet 1 from Yasaminzahra (about 45 minutes).

**Files:** `scripts/analyze.sh`, `kst/validate.py`, `tests/test_analyze.py`,
`tests/test_validate.py`, `.github/workflows/`, `docs/reproduction.md`.
**Branch:** `feat/rendered-analysis`.
**Hand-off:** "fresh clone reproduces `out/` byte-identical on Fedora: yes/no; on WSL: yes/no",
plus what differed and why.
**Fallback:** reproduction on Fedora only.

### Yasaminzahra Valitabar: category validation and rename detection

**Goal.** Show that our smell categories are not one person's opinion, and stop renamed objects
from looking like a removal plus an introduction.

**Part A: two-rater category validation (tonight).**
1. Generate blank sheets outside the repository:
   `python3 -m kst.category_validation prepare --out ~/category-sheets`
2. Send `category_rater_1.csv` to **Ankit** and `category_rater_2.csv` to **Rojan**, each
   privately. Raters must not see `data/check_categories.csv` or each other's answers.
   Raters: for each of the 62 checks, pick security, resource, image, hygiene or other, and
   write a one-line reason. About 45 minutes. Return by tonight.
3. Copy the returned sheets unchanged to `data/category_validation/` and compute agreement
   **before** discussing any differences:
   `python3 -m kst.category_validation calculate --rater-1 data/category_validation/category_rater_1.csv --rater-2 data/category_validation/category_rater_2.csv --out results/category_validation`
4. Adjudicate the disagreements (record decision and reason in
   `category_map_differences.csv`). If a check's final category differs from
   `data/check_categories.csv`, update the map in the same PR, so the integration run uses the
   validated map.

**Part B: rename detection in `kst/track.py`.**
1. Today, if an object is renamed between two tags, its smells are labelled *removed* on the old
   name and *introduced* on the new one. Add a flag for probable renames: between the same two
   tags, an object of the same kind disappears and another appears with the same set of checks
   firing on it. Mark both sides (for example a `probable_rename` column in
   `out/instances.csv`). Do not merge their histories automatically, so the counts stay honest
   and the report can show both views.
2. Tests in `tests/test_track.py`: a rename case, a non-rename case (same kind, different
   checks), and a long history over many tags, since dense tags give up to 46 tags per project.
3. After the integration run: check `out/instances.csv` for probable renames and for any tag
   marked invalid, and confirm that the tracking results look sane on the dense data.
4. Update `docs/category_validation.md` and `docs/tracking_limitations.md`.

**Files:** `kst/track.py`, `tests/test_track.py`, `data/check_categories.csv`,
`data/category_validation/`, `results/category_validation/`.
**Branches:** `feat/category-validation` (Part A), `feat/rename-detection` (Part B).
**Hand-off:**
- percentage agreement, Cohen's kappa, and the number of checks whose category changed;
- the number of probable renames, and an example.

**Fallback:** report agreement on whatever sheets are back; rename detection moves to Milestone 4.

### Bayan Sayyadifar: RQ3 commit tracing, survival figure, case studies

**Goal.** Answer RQ3: for each smell that appeared or disappeared, find the commit that caused
it and classify the cause. Also produce the figure that shows how projects differ.

**Part A: trace the Milestone 2 transitions (tonight).**
1. In `out/instances.csv`, find all removals where the object still exists (real fixes, 30 in
   total, 4 already traced) and all introductions on existing objects (25). Some are already
   in `data/rq3_investigations.csv` from the spot-check.
2. For each untraced one, find the commit between the two tags that changed that object, for
   example
   `git -C work/<repo> log --oneline <from_tag>..<to_tag> -- <manifest file>`.
   Then read the diff and fill a row in `data/rq3_investigations.csv` with the existing
   columns:
   - commit URL;
   - what changed in the configuration;
   - evidence URL;
   - classification;
   - verification status.
3. Classification values:
   - `real_fix`: the smell was fixed on purpose;
   - `side_effect_of_fix`: the smell was introduced by an unrelated fix, like the argo-cd Redis
     case;
   - `analyzer_artifact`: the analyzer changed, not the config;
   - `object_deleted`;
   - `new_object`;
   - `persisting_smell`;
   - `probable_rename`: new; agree it with Yasaminzahra.

**Part B: new transitions after the integration run.**
1. Rendering and dense tags will reveal new fixes and introductions. Trace them the same way.
2. If there are too many to finish by 17:00, trace a sample stratified by project (for example,
   up to 5 per project), and write down how the sample was drawn.

**Part C: survival figure.**
1. Add `scripts/survival.py`. For each project, it plots the share of smell instances present at
   the first tag that are still present at each later tag (x axis = tag index or release date,
   one line per project), read from `out/instances.csv`.
2. Save the figure as vector PDF to `results/survival.pdf`, sized for one IEEE column
   (about 3.5 inches wide), so it can go straight into the report.
3. Use matplotlib if available; otherwise write the data as CSV and Rohan plots it.

**Part D: case studies.**
1. Update `docs/rq3_case_studies.md` with the final counts per classification and two or three
   cases worth telling. Good candidates: a real fix, a smell introduced by a security fix, and
   one surprise from the new data.

**Files:** `data/rq3_investigations.csv`, `scripts/survival.py`, `results/survival.pdf`,
`docs/rq3_case_studies.md`, `docs/discussion.md`.
**Branches:** `feat/rq3-tracing`, `feat/survival-figure`.
**Hand-off:**
- a count of traced transitions per classification;
- `results/survival.pdf`;
- two or three cases in two or three sentences each, with commit links.

**Fallback:** trace 10 more Milestone 2 transitions, spread across projects. Full tracing moves
to Milestone 4.

## 7. Code ownership (whole repository)

Each person owns these files: they fix them, review changes to them, and keep the matching docs
up to date. Rohan reviews and merges every PR.

| Member | Owns | Docs |
|---|---|---|
| Rohan Muslekar | `data/repos.json`, `kst/repos.py`, `kst/select_tags.py`, `scripts/collect.sh`, `kst/inventory.py`, `kst/manifests.py`, and their tests; the IEEE report | `README.md` (study systems) |
| Ankit Suman | `tools/install.sh`, `tools/kube-linter.yaml`, `scripts/analyze.sh`, `kst/validate.py`, `kst/normalize.py`, `.github/workflows/`, and their tests | `docs/reproduction.md`, `README.md` (CI) |
| Yasaminzahra Valitabar | `kst/track.py`, `data/check_categories.csv`, `kst/category_validation.py`, `data/category_validation/`, and their tests | `docs/category_validation.md`, `docs/tracking_limitations.md` |
| Bayan Sayyadifar | `kst/overlap.py`, the table writers in `kst/__main__.py`, `scripts/summary.py`, `scripts/sample_spot_check.py`, `scripts/survival.py`, `data/spot_check.csv`, `data/rq3_investigations.csv`, `results/` | `docs/rq3_case_studies.md`, `docs/discussion.md`, `results/README.md` |
| Seyedeh Rojan Razavi | `kst/render.py`, `scripts/compare_render.py`, the render flag in `scripts/collect.sh`, and their tests | `docs/methodology.md`, `docs/limitations_and_validity.md` |

## 8. Milestone 4 (polishing only)

| Member | Milestone 4 |
|---|---|
| Rohan | Final report built from this one; final check of every number against `out/` |
| Ankit | Final fresh-clone reproduction of the submitted artifact |
| Yasaminzahra | Final pass on the tracking and category docs |
| Bayan | Polish the case studies; figures for the presentation |
| Rojan | Final pass on the methodology and validity docs; presentation slides |

Anything from section 6 that fell back on Nov 8 is finished first in Milestone 4.
