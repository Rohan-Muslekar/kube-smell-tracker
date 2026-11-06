# Milestone 3: Responsibilities (Group 4)

Due **Sun Nov 8, 2026** (assumed 11:59 p.m.). Code lands in `kube-smell-tracker` through PRs.
Rohan reviews and merges every PR.

## 1. Code ownership (whole repo)

Each person owns these files: they fix them, review changes to them, and keep the matching
`docs/` file up to date.

| Member | Owns (files) | Docs file |
|---|---|---|
| **Rohan Muslekar** | `data/repos.json`, `kst/repos.py`, `kst/select_tags.py`, `scripts/collect.sh`, `kst/inventory.py`, `kst/manifests.py`, their tests; the IEEE report (`milestones/m3/paper/`, `make_tables.py`) | `README.md` (study systems section) |
| **Ankit Suman** | `tools/install.sh`, `tools/kube-linter.yaml`, `scripts/analyze.sh`, `kst/validate.py`, `kst/normalize.py`, `.github/workflows/`, their tests | `docs/reproduction.md`, `README.md` (CI section) |
| **Yasaminzahra Valitabar** | `kst/track.py`, `data/check_categories.csv`, `kst/category_validation.py`, `data/category_validation/`, their tests | `docs/category_validation.md`, `docs/tracking_limitations.md` |
| **Bayan Sayyadifar** | `kst/overlap.py`, table writers in `kst/__main__.py`, `scripts/summary.py`, `scripts/sample_spot_check.py`, `data/spot_check.csv`, `data/rq3_investigations.csv`, `results/` | `docs/rq3_case_studies.md`, `docs/discussion.md`, `results/README.md` |
| **Seyedeh Rojan Razavi** | **new** `kst/render.py` (kustomize and Helm rendering), its tests and fixtures, the render flag in `scripts/collect.sh` | `docs/methodology.md`, `docs/limitations_and_validity.md` |

## 2. Milestone 3 tasks (due Nov 8, 12:00 noon)

Every task ends in a merged PR **or** a short result note (numbers + command) sent to Rohan.
The report needs the numbers by **noon Nov 8**. If a task cannot finish, use its fallback;
the full version moves to Milestone 4 and the report says so.

### Rojan: rendering check (the check behind our strongest validity threat)
Why: 84 of our 108 "object deleted" removals come from unrendered kustomize patch fragments in
flux2. If rendering changes that, our main RQ2 removal finding changes.
- Branch `feat/render-kustomize`.
- `kst/render.py`: for a manifest directory containing `kustomization.yaml`, run
  `kubectl kustomize <dir>` (kustomize binary is not needed) and write the rendered YAML to the
  per-tag work dir; `helm template` for charts.
- Flag in `scripts/collect.sh` (e.g. `RENDER=1`), default off so the M2 run still reproduces.
- Test: one tiny kustomize base + patch fixture under `tests/fixtures/`, assert the rendered
  output holds whole objects.
- **Result needed for the report:** flux2 at its 5 tags, rendered vs. unrendered: number of
  objects, smell instances, removals, "object deleted" removals. One small table.
- Fallback: render flux2 by hand for the 5 tags (`kubectl kustomize`), run both analyzers,
  report the same numbers; module and flag go to M4.

### Ankit: analyzers on rendered output + reproduction
- Make `scripts/analyze.sh` and `kst/validate.py` accept Rojan's rendered output (pair with her).
- Fresh-clone reproduction of current `master` (`./tools/install.sh && make all`, then
  `diff -ru out /tmp/fresh/out`); finish the open WSL comparison of kube-prometheus
  `dangling-servicemonitor`. Record in `docs/reproduction.md`.
- Keep CI green after the merges.
- **Result needed:** one line "fresh clone reproduces out/ byte-identical: yes/no" + what differed.
- Fallback: reproduction only.

### Yasaminzahra: two-rater category validation (kappa)
- Run `python3 -m kst.category_validation prepare --out ~/category-sheets` and send
  `category_rater_1.csv` to **Ankit** and `category_rater_2.csv` to **Rojan** (raters chosen so
  the coordinator does not rate; swap if needed). About 62 checks, ~45 minutes each.
- Raters return sheets by **Nov 7 night**. Then
  `python3 -m kst.category_validation calculate --rater-1 data/category_validation/category_rater_1.csv --rater-2 data/category_validation/category_rater_2.csv --out results/category_validation`
- Adjudicate disagreements, commit sheets + `category_agreement.json`.
- **Result needed:** % agreement, Cohen's kappa, number of checks whose category changed after
  adjudication.
- Fallback: report agreement on what is returned; adjudication goes to M4.

### Bayan: RQ3 commit tracing + survival figure
- Trace the remaining real fixes (26 not yet traced) and the introductions on existing objects
  to their commits in `data/rq3_investigations.csv` (same columns as now).
- Add `scripts/survival.py` (or a function in `results/render.py`) that plots, per system, the
  share of first-tag instances still present at each later tag, from `out/instances.csv`.
  Output `results/survival.pdf` (vector, for the paper).
- **Result needed:** count per classification (real fix / side effect of fix / analyzer
  artifact / object deleted / new object) over all traced cases; the figure.
- Fallback: trace 10 more, stratified by system; full tracing goes to M4.

### Rohan: report + denser-tag stretch
- Write `milestones/m3/paper/milestone3.tex`, run `make_tables.py`, add the new tables from the
  results above, fill the contribution table, build the PDF.
- Stretch (only if time): denser tags for one system that changes (argo-cd): every minor between
  the sampled tags, to test "zero reappearance is a lower bound".
- Review and merge all PRs by noon Nov 8.

## 3. Milestone 4 continuation (stated in the report as next steps)

| Member | Continues with |
|---|---|
| Rohan | denser tags for all systems that change; final numbers freeze |
| Ankit | CI covering the rendered run; final fresh-clone reproduction |
| Yasaminzahra | tracking on denser tags; rename detection (object moved/renamed = removal + introduction today) |
| Bayan | full RQ3 tracing of all fixes and introductions; case-study write-up |
| Rojan | Helm rendering for any chart-only candidates; rerun RQ1/RQ2 on rendered manifests for all systems |
