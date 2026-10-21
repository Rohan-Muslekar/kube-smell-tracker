"""Run scripts/analyze.sh with the pinned analyzers (skipped when tools/install.sh has not been run)."""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
pytestmark = pytest.mark.skipif(not (ROOT / "tools/bin/kube-linter").exists() or
                                not (ROOT / "tools/bin/kube-score").exists(),
                                reason="analyzers not built; run ./tools/install.sh")

DEPLOYMENT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
      - name: web
        image: nginx
"""


def _analyze(clone, *files):
    subprocess.run([str(ROOT / "scripts/analyze.sh"), "lint.json", "score.json", "err", *files],
                   cwd=clone, check=True, capture_output=True, text=True)
    return json.loads((clone / "lint.json").read_text())


def test_config_file_in_analyzed_repo_is_ignored(tmp_path):
    (tmp_path / "web.yaml").write_text(DEPLOYMENT)
    baseline = len(_analyze(tmp_path, "web.yaml")["Reports"])
    (tmp_path / ".kube-linter.yaml").write_text("checks:\n  exclude: [latest-tag, run-as-non-root]\n")
    assert len(_analyze(tmp_path, "web.yaml")["Reports"]) == baseline
