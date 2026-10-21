#!/usr/bin/env bash
# Run kube-linter and kube-score on manifest files. Run it from the repo clone, with paths relative to it.
# Usage: analyze.sh LINT_OUT SCORE_OUT ERR_PREFIX FILE...
# Writes each tool's JSON to LINT_OUT / SCORE_OUT and its stderr to ERR_PREFIX.linter.err / .score.err.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LINTER="$ROOT/tools/bin/kube-linter"
SCORER="$ROOT/tools/bin/kube-score"
lint_out="$1" score_out="$2" err="$3"; shift 3

# Both tools exit non-zero when they find problems, so the exit code is ignored;
# kst.validate checks the output instead.
"$LINTER" lint "$@" --config "$ROOT/tools/kube-linter.yaml" --add-all-built-in --format json > "$lint_out" 2> "$err.linter.err" || true
"$SCORER" score "$@" --output-format json > "$score_out" 2> "$err.score.err" || true
