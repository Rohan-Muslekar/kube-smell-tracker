from pathlib import Path

from kst.inventory import main, objects


def test_single_object_without_namespace():
    text = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\n  labels:\n    app: web\nspec: {}\n"
    assert objects(text) == [("Deployment", "", "web")]


def test_multi_document_with_namespace_and_comments():
    text = ("# Copyright\n---\napiVersion: v1\nkind: Service\nmetadata:\n  labels:\n    name: not-this\n"
            "  name: api\n  namespace: shop\nspec:\n  selector:\n    name: also-not-this\n"
            "---\n---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: \"cfg\"\n  namespace: 'shop'\n")
    assert objects(text) == [("Service", "shop", "api"), ("ConfigMap", "shop", "cfg")]


def test_document_without_kind_ignored():
    assert objects("foo: bar\n---\n") == []


def test_list_kind_items_are_not_parsed():
    # A v1 List wraps objects in items; we record only top-level objects and say so in the README.
    text = "apiVersion: v1\nkind: List\nitems:\n- apiVersion: v1\n  kind: Service\n  metadata:\n    name: x\n"
    assert objects(text) == [("List", "", "")]


def test_stray_namespace_on_cluster_scoped_object_is_dropped():
    text = "kind: ClusterRoleBinding\nmetadata:\n  name: resolvers\n  namespace: tekton-pipelines\n"
    assert objects(text) == [("ClusterRoleBinding", "", "resolvers")]

def test_inventory_uses_relative_paths(capsys):
    """Absolute project paths must be stored as relative paths."""
    project_root = Path(__file__).resolve().parent.parent
    manifest = project_root / "tests" / "fixtures" / "kustomize" / "standalone.yaml"

    main([str(manifest)])

    output = capsys.readouterr().out
    assert "tests/fixtures/kustomize/standalone.yaml" in output
    assert str(project_root) not in output