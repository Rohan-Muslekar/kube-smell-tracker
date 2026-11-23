"""Tests for the Kustomize renderer."""

import shutil
from pathlib import Path

import pytest
import yaml

from kst.render import build_analysis_file_list


FIXTURE = Path(__file__).parent / "fixtures" / "kustomize"

needs_kubectl = pytest.mark.skipif(
    shutil.which("kubectl") is None, reason="kubectl not installed (./tools/install.sh)")


@needs_kubectl
def test_kustomize_render(tmp_path):
    """Render a patched Deployment and exclude unreferenced YAML."""
    files, failures = build_analysis_file_list(
        FIXTURE,
        ["."],
        tmp_path / "rendered",
    )

    assert failures == []
    assert len(files) == 1

    rendered_files = [
        Path(path) for path in files
        if "rendered" in Path(path).parts
    ]
    assert len(rendered_files) == 1

    with rendered_files[0].open(encoding="utf-8") as stream:
        objects = list(yaml.safe_load_all(stream))

    assert len(objects) == 1
    deployment = objects[0]

    assert deployment["kind"] == "Deployment"
    assert deployment["metadata"]["name"] == "demo-app"
    assert deployment["spec"]["replicas"] == 3

    # Base and patch must not be analyzed separately.
    assert not any("deployment.yaml" in path for path in files)
    assert not any("patch.yaml" in path for path in files)

    # Unrelated plain YAML must remain in the analysis list.
    assert "standalone.yaml" not in files
@needs_kubectl
def test_kustomize_render_failure(tmp_path):
    """Report rendering failures and preserve healthy YAML."""
    fixture = Path(__file__).parent / "fixtures" / "kustomize_failure"

    files, failures = build_analysis_file_list(
        fixture,
        ["."],
        tmp_path / "rendered",
    )

    # Rendering fails because a referenced file is missing.
    assert len(failures) == 1
    assert "missing-deployment.yaml" in failures[0][1]

    # Healthy YAML must still be available for analysis.
    assert files == ["healthy.yaml"]

    # Failed rendering must not produce an output file.
    assert list((tmp_path / "rendered").glob("*.yaml")) == []


    assert len(failures) == 1
    assert "missing-deployment.yaml" in failures[0][1]
def test_failed_render_removes_stale_output(tmp_path):
    """A failed render must not leave an old rendered file."""
    fixture = Path(__file__).parent / "fixtures" / "kustomize_failure"
    output_dir = tmp_path / "rendered"
    output_dir.mkdir()

    stale_file = output_dir / "root.yaml"
    stale_file.write_text("old rendered content", encoding="utf-8")

    files, failures = build_analysis_file_list(
        fixture,
        ["."],
        output_dir,
    )

    assert len(failures) == 1
    assert files == ["healthy.yaml"]
    assert not stale_file.exists()
def test_invalid_kustomization(tmp_path):
    """Invalid YAML must be reported without crashing."""
    fixture = Path(__file__).parent / "fixtures" / "kustomize_invalid"

    files, failures = build_analysis_file_list(
        fixture,
        ["."],
        tmp_path / "rendered",
    )

    assert files == []
    assert len(failures) == 1
    assert failures[0][0] == "."


@needs_kubectl
def test_deprecated_bases_key(tmp_path):
    """A base listed under the old `bases:` key is not rendered on its own."""
    fixture = Path(__file__).parent / "fixtures" / "kustomize_bases"

    files, failures = build_analysis_file_list(
        fixture,
        ["."],
        tmp_path / "rendered",
    )

    assert failures == []
    assert [Path(path).name for path in files] == ["overlay.yaml"]

@needs_kubectl
def test_unreferenced_yaml_is_excluded(tmp_path):
    """Unreferenced YAML inside a Kustomization must not be linted."""
    files, failures = build_analysis_file_list(
        FIXTURE,
        ["."],
        tmp_path / "rendered",
    )

    assert failures == []

    # Only the rendered Deployment should be analyzed.
    assert len(files) == 1
    assert Path(files[0]).name == "root.yaml"

    # Unreferenced YAML must be excluded.
    assert "standalone.yaml" not in files


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


DEPLOYMENT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
spec:
  template:
    spec:
      containers:
        - name: app
          image: nginx:1.27
"""


def _two_directory_repo(root):
    """app/ is a kustomization that leaves unused.yaml out; plain/ has no kustomization."""
    _write(root / "app" / "kustomization.yaml", "resources:\n  - deployment.yaml\n")
    _write(root / "app" / "deployment.yaml", DEPLOYMENT.format(name="app"))
    _write(root / "app" / "unused.yaml", DEPLOYMENT.format(name="unused"))
    _write(root / "plain" / "service.yaml", DEPLOYMENT.format(name="plain"))
    _write(root / "plain" / "values.yaml", "replicas: 3\n")
    return root


@needs_kubectl
def test_plain_yaml_outside_a_kustomization_is_kept(tmp_path):
    """Only files under a rendered kustomization's directory are dropped."""
    repo = _two_directory_repo(tmp_path / "repo")

    files, failures = build_analysis_file_list(repo, ["."], tmp_path / "rendered")

    assert failures == []
    assert "plain/service.yaml" in files
    assert "app/unused.yaml" not in files
    assert [Path(f).name for f in files if Path(f).is_absolute()] == ["app.yaml"]


@needs_kubectl
def test_every_dropped_file_has_a_reason(tmp_path, capsys):
    """Each file that is not linted is reported as `path<TAB>reason`, like kst.manifests."""
    repo = _two_directory_repo(tmp_path / "repo")

    build_analysis_file_list(repo, ["."], tmp_path / "rendered")

    reasons = dict(line.split("\t", 1) for line in capsys.readouterr().err.splitlines())
    assert reasons == {
        "app/deployment.yaml": "consumed by a kustomization",
        "app/kustomization.yaml": "consumed by a kustomization",
        "app/unused.yaml": "not referenced by kustomization",
        "plain/values.yaml": "not a k8s object",
    }
