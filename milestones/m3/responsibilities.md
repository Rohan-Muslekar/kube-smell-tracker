# Milestone 3: Responsibilities (Group 4)

Due **Sun Nov 8, 2026** (assumed 11:59 p.m.). Code lands in `kube-smell-tracker` through PRs.
Rohan reviews and merges every PR.

Milestone 3 does the full analysis. Milestone 4 is polishing only: final number check,
final report, presentation.

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

## 2. How the day runs

Rendering and denser tags both change the raw data, so every number changes once they land.
There is **one integration run** after the code PRs merge; all analysis and tracing after that
uses its output.

| When | Step |
|---|---|
| Nov 7 night | Code PRs open: rendering (Rojan), denser tags (Rohan), rename detection (Yasaminzahra), rendered-input support (Ankit). Category sheets rated. Bayan finishes tracing the M2 dataset. |
| **Nov 8, 10:00** | All code PRs merged. |
| Nov 8, 10:00-12:00 | **Integration run** (Rohan): `RENDER=1 make all` with denser tags; commit new `raw/`, `out/`, `data/versions.csv`. |
| Nov 8, 12:00-17:00 | Analysis on the new data (everyone, below). |
| **Nov 8, 17:00** | **Numbers freeze.** Result notes + contribution lines with PR links sent to Rohan. |
| Nov 8, 20:00 / 23:00 | Draft checked by everyone / submitted. |

**Fallback for the whole day:** if the integration run is not committed by 12:00, the report
uses the M2 data, and rendering and denser tags are reported as checks run on a subset
(flux2 rendered; one system with denser tags).

## 3. Tasks

### Rohan: denser tags, integration run, report
- `kst/select_tags.py`: a dense mode that takes **every minor release** (latest patch of each)
  in the same window, for every system. Keep the 5-tag mode so M2 reproduces.
- `scripts/collect.sh` / `data/repos.json`: record the mode used; `data/versions.csv` grows.
- Integration run and commit (see table above).
- Report: `milestones/m3/paper/milestone3.tex`, `make_tables.py`, contribution table, PDF.
- Result for the report: number of tags per system; reappearances found with dense tags
  (tests the "zero reappearance is a lower bound" threat).

### Rojan: rendering for all systems
- Branch `feat/render-kustomize`. `kst/render.py`: for each manifest directory with
  `kustomization.yaml`, run `kubectl kustomize <dir>` (no kustomize binary needed); for charts,
  `helm template`. Write rendered YAML to the per-tag work dir.
- `RENDER=1` flag in `scripts/collect.sh`; off reproduces M2 exactly.
- Tests: tiny kustomize base + patch fixture and a tiny chart under `tests/fixtures/`; assert
  rendered output holds whole objects and the inventory matches analyzer objects.
- After the integration run: comparison of rendered vs. unrendered on the same tags for every
  system: objects, instances, removals, "object deleted" removals, real fixes. Script it
  (`scripts/compare_render.py`) so it reruns. This is the check behind the strongest threat.
- Update `docs/methodology.md` and `docs/limitations_and_validity.md`.

### Ankit: analyzers on rendered output, CI, reproduction
- `scripts/analyze.sh` and `kst/validate.py` accept rendered output (pair with Rojan tonight).
- CI: run the tests plus the offline analysis on the new committed raw data; `out/` must match.
- After the integration run: fresh-clone reproduction of the new `master`
  (`./tools/install.sh && RENDER=1 make all`, then `diff -ru out <fresh>/out`), on Fedora and
  WSL. Finish the open kube-prometheus `dangling-servicemonitor` comparison.
- Rate category sheet 1 tonight (~45 min).
- Result for the report: reproduction yes/no + what differed.

### Yasaminzahra: category validation + tracking upgrades
- Tonight: `python3 -m kst.category_validation prepare --out ~/category-sheets`; send
  `category_rater_1.csv` to Ankit and `category_rater_2.csv` to Rojan. When back:
  `python3 -m kst.category_validation calculate --rater-1 data/category_validation/category_rater_1.csv --rater-2 data/category_validation/category_rater_2.csv --out results/category_validation`,
  adjudicate, commit sheets and `category_agreement.json`.
- `kst/track.py`: **rename detection**: an object that disappears and a new object of the same
  kind with the same smells appearing in the same step, flagged as a probable rename instead of
  removal + introduction. Tests for it, and for tracking across many dense tags.
- After the integration run: check the tracking output (renames found, any tag marked invalid).
- Result for the report: % agreement, Cohen's kappa, checks that changed category; renames found.

### Bayan: full RQ3 tracing, figures, case studies
- Tonight: trace **all** remaining real fixes (26) and introductions on existing objects in the
  M2 data into `data/rq3_investigations.csv`.
- After the integration run: trace the new fixes and introductions it reveals. If there are too
  many by 17:00, trace a sample stratified by system and say so.
- `scripts/survival.py`: per system, share of first-tag instances still present at each later
  tag, from `out/instances.csv`; output `results/survival.pdf` (vector).
- Update `docs/rq3_case_studies.md` with the final cases.
- Result for the report: count per cause (real fix / side effect of fix / analyzer artifact /
  object deleted / new object / rename) over all traced transitions; the figure; 2-3 cases.

## 4. Milestone 4 (polishing only)

| Member | Milestone 4 |
|---|---|
| Rohan | Final report from the M3 paper; final numbers check |
| Ankit | Final fresh-clone reproduction of the submitted artifact |
| Yasaminzahra | Tracking and category docs final pass |
| Bayan | Case-study write-up polish; figures for the presentation |
| Rojan | Methodology/validity docs final pass; presentation slides |
