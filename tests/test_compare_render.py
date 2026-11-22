import csv
import subprocess
import sys
from pathlib import Path


def test_compares_stored_and_rendered_systems(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "compare_render.py"
    header = "repo,category,tool,check,presence,removed,removed_object_gone,reappeared\n"
    for source in ("stored", "rendered"):
        root = tmp_path / source
        inventories = root / "raw" / "objects"
        inventories.mkdir(parents=True)
        (root / "out").mkdir()
        (inventories / "demo__v1.tsv").write_text(
            "Deployment\t\tapp\ta.yaml\nDeployment\t\tapp\tb.yaml\n"
        )
        (inventories / "demo__v3.tsv").write_text("Deployment\t\tapp\ta.yaml\n")
        if source == "stored":
            (inventories / "demo__v2.tsv").write_text("Deployment\t\tapp\ta.yaml\n")
            (inventories / "quiet__v1.tsv").write_text("")
            rows = (
                "demo,security,kube-linter,check,101,1,1,1\n"
                "demo,security,kube-linter,check,100,1,0,0\n"
                "demo,hygiene,kube-score,pod-probes-identical,100,1,0,0\n"
                "demo,other,kube-score,other,100,1,0,0\n"
            )
        else:
            (inventories / "demo__v2.tsv").write_text("")
            rows = "demo,security,kube-linter,check,111,0,0,0\n"
        (root / "out" / "instances.csv").write_text(header + rows)

    result = subprocess.run(
        [sys.executable, str(script), "--stored", "stored", "--rendered", "rendered"],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    )

    with (tmp_path / "results" / "render_comparison.csv").open(newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows == [
        ["system", "source", "object_version_observations", "instances", "baseline", "survivors",
         "survival_pct", "removals", "deletions", "deletion_pct", "real_fixes", "reappearances"],
        ["demo", "stored", "3", "3", "3", "1", "33.3", "3", "1", "33.3", "1", "1"],
        ["demo", "rendered", "2", "1", "1", "1", "100.0", "0", "0", "", "0", "0"],
        ["quiet", "stored", "0", "0", "0", "0", "", "0", "0", "", "0", "0"],
        ["quiet", "rendered"] + [""] * 10,
    ]
    assert [line.split("\t") for line in result.stdout.splitlines()] == rows
