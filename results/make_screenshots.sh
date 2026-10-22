#!/usr/bin/env bash
# Regenerate every image in results/screenshots/ from the committed outputs.
# Run from anywhere; needs Pillow for results/render.py.
set -euo pipefail
cd "$(dirname "$0")/.."
shot() { python3 results/render.py "results/screenshots/$1.png" "$2"; }

shot 01-tests                "python3 -m pytest -q"
shot 02-analysis             "python3 -m kst && ls out/"
shot 03-study-tags           "cut -d, -f1,2,4,5,6 data/versions.csv | column -s, -t"
shot 04-headline-numbers     "python3 scripts/summary.py"
shot 05-transitions-summary  "column -s, -t out/transitions_summary.csv"
shot 06-transitions-by-repo  "grep -v ',other,' out/transitions_by_repo.csv | column -s, -t"
shot 07-tool-overlap         "column -s, -t out/overlap_summary.csv"
shot 08-spot-check           "cut -d, -f1,2,3,4,12,13 data/spot_check.csv | column -s, -t"
shot 09-load-failures        "column -t raw/load_failures.tsv"
