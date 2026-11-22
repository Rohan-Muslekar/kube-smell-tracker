#!/usr/bin/env bash
# Build the pinned analyzer versions and download the pinned kubectl into tools/bin
# (nothing is installed system-wide).
set -euo pipefail
cd "$(dirname "$0")/.."
export GOBIN="$PWD/tools/bin"
go install golang.stackrox.io/kube-linter/cmd/kube-linter@v0.8.3
go install github.com/zegl/kube-score/cmd/kube-score@v1.20.0
# `version` prints "development" for go-installed builds; the module line has the real version.
go version -m "$GOBIN/kube-linter" | grep -E "^\s+mod\s"
go version -m "$GOBIN/kube-score" | grep -E "^\s+mod\s"

# kubectl renders the kustomize manifests (RENDER=1, the default). Pinned, checksum-verified.
KUBECTL_VERSION=v1.36.2
case "$(uname -m)" in
  x86_64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
  *) echo "unsupported architecture $(uname -m); install kubectl $KUBECTL_VERSION yourself" >&2; exit 1 ;;
esac
os="$(uname -s | tr '[:upper:]' '[:lower:]')"
url="https://dl.k8s.io/release/$KUBECTL_VERSION/bin/$os/$arch/kubectl"
curl -fsSLo "$GOBIN/kubectl" "$url"
echo "$(curl -fsSL "$url.sha256")  $GOBIN/kubectl" | sha256sum --check --status
chmod +x "$GOBIN/kubectl"
"$GOBIN/kubectl" version --client
