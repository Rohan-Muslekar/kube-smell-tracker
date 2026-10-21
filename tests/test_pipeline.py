import csv
import subprocess
import sys
from pathlib import Path

FIX = Path(__file__).parent / "fixtures" / "pipeline"
ROOT = Path(__file__).parent.parent


def _run(out):
    return subprocess.run([sys.executable, "-m", "kst", "--raw", str(FIX / "raw"), "--data", str(FIX / "data"),
                           "--out", str(out)], cwd=ROOT, capture_output=True, text=True)


def _rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def test_pipeline_on_fixtures(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    for name in ("findings.csv", "prevalence.csv", "instances.csv", "transitions_summary.csv",
                 "transitions_by_repo.csv", "overlap_summary.csv", "unmapped_checks.txt"):
        assert (tmp_path / name).exists(), name
    summary = {(r["tool"], r["category"]): [int(r[c]) for c in
               ("at_baseline", "introduced", "persisted", "removed", "reappeared")]
               for r in _rows(tmp_path / "transitions_summary.csv")}
    assert summary == {
        ("kube-linter", "image"): [1, 1, 0, 1, 0],
        ("kube-linter", "security"): [1, 0, 1, 0, 0],
        ("kube-score", "security"): [1, 0, 0, 1, 0],
    }
    overlap = {r["category"]: (int(r["linter_only"]), int(r["score_only"]), int(r["both"]))
               for r in _rows(tmp_path / "overlap_summary.csv")}
    assert overlap == {"image": (2, 0, 0), "security": (1, 0, 1)}
    split = {(r["tool"], r["category"]): (int(r["removed_object_gone"]), int(r["introduced_new_object"]))
             for r in _rows(tmp_path / "transitions_summary.csv")}
    # web keeps existing in v2, so both removals are fixes; api is a new object in v2.
    assert split == {("kube-linter", "image"): (0, 1), ("kube-linter", "security"): (0, 0),
                     ("kube-score", "security"): (0, 0)}


def test_unmapped_check_fails_the_run(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "versions.csv").write_text((FIX / "data" / "versions.csv").read_text())
    (data / "check_categories.csv").write_text("tool,check,category,rationale\n")
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, "-m", "kst", "--raw", str(FIX / "raw"), "--data", str(data),
                             "--out", str(out)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert "kube-linter,latest-tag" in (out / "unmapped_checks.txt").read_text()
