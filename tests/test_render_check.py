import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "render_check", Path(__file__).parent.parent / "scripts" / "render_check.py")
render_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_check)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_only_unreferenced_kustomizations_are_top_level(tmp_path):
    _write(tmp_path / "m/base/kustomization.yaml", "resources:\n- deploy.yaml\n")
    _write(tmp_path / "m/base/deploy.yaml", "apiVersion: apps/v1\nkind: Deployment\n")
    _write(tmp_path / "m/install/kustomization.yaml",
           "resources:\n  - ../base\n  - https://example.com/remote.yaml\npatches:\n  - path: patch.yaml\n")
    _write(tmp_path / "m/install/patch.yaml", "apiVersion: apps/v1\nkind: Deployment\n")
    _write(tmp_path / "m/plain.yaml", "apiVersion: v1\nkind: ConfigMap\n")

    top, used = render_check.plan(tmp_path, ["m"])

    assert top == [(tmp_path / "m/install").resolve()]
    assert (tmp_path / "m/install/patch.yaml").resolve() in used
    assert (tmp_path / "m/base/deploy.yaml").resolve() in used
    assert (tmp_path / "m/plain.yaml").resolve() not in used


def test_list_items_with_keys_are_not_paths(tmp_path):
    _write(tmp_path / "k/kustomization.yaml", "images:\n  - name: app\n    newName: ghcr.io/app\n")
    _write(tmp_path / "k/app", "not a path reference\n")
    assert render_check.local_refs(tmp_path / "k/kustomization.yaml") == set()
