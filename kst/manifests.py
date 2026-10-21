"""Decide which YAML files under a manifest path are plain Kubernetes objects.

Usage: python3 -m kst.manifests FILE...   (run from the repo clone)
Prints kept files on stdout and "file<TAB>reason" for skipped files on stderr.
"""
import os
import re
import sys

# Helm-specific template actions. Control actions like if/with/range/end are left out:
# Prometheus alert text and dashboards use them too, as data rather than templating.
HELM = re.compile(r"\{\{-?\s*(\.Values|\.Release|\.Chart|\.Capabilities|include\b|template\b|define\b|toYaml\b|tpl\b)")
API_VERSION = re.compile(r"^apiVersion:", re.M)
KIND = re.compile(r"^kind:", re.M)


def skip_reason(path, text):
    """Return why the file is not linted, or None when it is a plain Kubernetes manifest."""
    if os.path.basename(path) in ("kustomization.yaml", "kustomization.yml"):
        return "kustomization"
    if HELM.search(text):
        return "templated"
    if not (API_VERSION.search(text) and KIND.search(text)):
        return "not a k8s object"
    return None


def main(paths):
    for path in paths:
        with open(path, errors="replace") as f:
            reason = skip_reason(path, f.read())
        if reason is None:
            print(path)
        else:
            print(f"{path}\t{reason}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
