"""Tests for the Kustomize renderer."""

from pathlib import Path

import yaml

from kst.render import build_analysis_file_list


FIXTURE = Path(__file__).parent / "fixtures" / "kustomize"


def test_kustomize_render(tmp_path):
    """Render a patched Deployment and preserve standalone YAML."""
    files, failures = build_analysis_file_list(
        FIXTURE,
        ["."],
        tmp_path / "rendered",
    )

    assert failures == []
    assert len(files) == 2

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
    assert "standalone.yaml" in files
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
