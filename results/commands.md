# Commands

Every command used to produce the results and the screenshots, in order, run from the
repository root. The environment (OS, Go, Python and analyzer versions) is listed in the main
[README](../README.md#environment-used-for-the-committed-outputs).

## Build the analyzers

```bash
./tools/install.sh
```

Builds kube-linter v0.8.3 and kube-score v1.20.0 into `tools/bin/` and prints their module
versions from `go version -m`.

## Collect analyzer output

```bash
./scripts/collect.sh
```

Clones the seven repositories into `work/`, checks out each tag in `data/repos.json`, and writes
`raw/kube-linter/`, `raw/kube-score/`, `raw/objects/`, `raw/skipped_files.txt`,
`raw/load_failures.tsv` and `data/versions.csv`. Needs network access. The outputs are
committed, so this step can be skipped.

## Analyze

```bash
python3 -m kst
```

Reads `raw/` and writes every table in `out/`. Needs no network.

## Test

```bash
python3 -m pytest -q
```

## Headline numbers

```bash
python3 scripts/summary.py
```

## Tables shown in the screenshots

```bash
cut -d, -f1,2,4,5,6 data/versions.csv | column -s, -t
column -s, -t out/transitions_summary.csv
grep -v ',other,' out/transitions_by_repo.csv | column -s, -t
column -s, -t out/overlap_summary.csv
cut -d, -f1,2,3,4,12,13 data/spot_check.csv | column -s, -t
column -t raw/load_failures.tsv
```

## Screenshots

```bash
pip install pillow          # only needed for the screenshots
./results/make_screenshots.sh
```

Runs each command above through `results/render.py` and saves the output as a PNG in
`results/screenshots/`. Re-running it gives the same images, apart from the test run time in
`01-tests.png`.

## Spot-check sample

```bash
python3 scripts/sample_spot_check.py
```

Draws the 20 spot-check instances (seed 5570) into `data/spot_check.csv`. It refuses to
overwrite the existing file, which holds the manual verdicts.
