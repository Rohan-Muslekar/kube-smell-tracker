import json
from pathlib import Path

from kst.normalize import Finding, categorize, load_categories, parse_kube_linter, parse_kube_score

FIX = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIX / name).read_text())


def test_parse_kube_linter_fields():
    findings = parse_kube_linter(_load("kube-linter.json"), "kube-prometheus", "v0.19.0")
    assert findings[0] == Finding(
        repo="kube-prometheus", version="v0.19.0", tool="kube-linter", check="dangling-networkpolicy",
        category="", kind="NetworkPolicy", namespace="monitoring", name="alertmanager-main",
        file="manifests/alertmanager-networkPolicy.yaml")
    assert len(findings) == 3


def test_parse_kube_score_only_failed_checks():
    findings = parse_kube_score(_load("kube-score.json"), "kube-prometheus", "v0.19.0")
    assert sorted(f.check for f in findings) == [
        "container-ephemeral-storage-request-and-limit", "container-image-pull-policy",
        "deployment-replicas", "pod-probes"]
    f = findings[0]
    assert (f.tool, f.kind, f.namespace, f.name) == ("kube-score", "Deployment", "monitoring", "blackbox-exporter")


def test_missing_namespace_is_empty():
    linter = parse_kube_linter(_load("kube-linter.json"), "kube-prometheus", "v0.19.0")
    assert linter[1].kind == "ClusterRoleBinding" and linter[1].namespace == ""
    score = parse_kube_score(_load("kube-score-no-namespace.json"), "microservices-demo", "v0.10.7")
    assert score and all(f.namespace == "" for f in score)


def test_file_is_repo_relative():
    score = parse_kube_score(_load("kube-score-no-namespace.json"), "microservices-demo", "v0.10.7")
    assert {f.file for f in score} == {"kubernetes-manifests/adservice.yaml"}


def test_unmapped_checks_reported(tmp_path):
    cats = tmp_path / "cats.csv"
    cats.write_text("tool,check,category,rationale\nkube-linter,dangling-networkpolicy,hygiene,x\n")
    findings = parse_kube_linter(_load("kube-linter.json"), "kube-prometheus", "v0.19.0")
    mapped, unmapped = categorize(findings, load_categories(str(cats)))
    assert mapped[0].category == "hygiene"
    assert unmapped == {("kube-linter", "access-to-secrets"), ("kube-linter", "dnsconfig-options")}


def test_stray_namespace_on_cluster_scoped_object_is_dropped():
    # A ClusterRole that carries metadata.namespace at one tag and not the next is the same object.
    data = {"Reports": [{"Check": "access-to-secrets", "Object": {
        "Metadata": {"FilePath": "manifests/role.yaml"},
        "K8sObject": {"Namespace": "monitoring", "Name": "metrics",
                      "GroupVersionKind": {"Kind": "ClusterRole"}}}}]}
    assert parse_kube_linter(data, "kube-prometheus", "v0.12.0")[0].namespace == ""
