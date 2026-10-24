#!/usr/bin/env bash
# Build the pinned analyzer versions into tools/bin (nothing is installed system-wide).
set -euo pipefail
cd "$(dirname "$0")/.."
export GOBIN="$PWD/tools/bin"
go install golang.stackrox.io/kube-linter/cmd/kube-linter@v0.8.3
go install github.com/zegl/kube-score/cmd/kube-score@v1.20.0
# `version` prints "development" for go-installed builds; the module line has the real version.
go version -m "$GOBIN/kube-linter" | grep -E "^\s+mod\s"
go version -m "$GOBIN/kube-score" | grep -E "^\s+mod\s"
