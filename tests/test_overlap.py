from kst.normalize import Finding
from kst.overlap import overlap, overlap_summary


def _f(tool, check, category, kind="Deployment", name="web"):
    return Finding(repo="r", version="v1", tool=tool, check=check, category=category,
                   kind=kind, namespace="", name=name, file="web.yaml")


def test_same_object_and_category_from_both_tools():
    rows = overlap([_f("kube-linter", "run-as-non-root", "security"),
                    _f("kube-score", "container-security-context-user-group-id", "security")])
    assert overlap_summary(rows) == [{"category": "security", "linter_only": 0, "score_only": 0, "both": 1}]


def test_linter_alone():
    rows = overlap([_f("kube-linter", "latest-tag", "image")])
    assert overlap_summary(rows) == [{"category": "image", "linter_only": 1, "score_only": 0, "both": 0}]


def test_other_category_excluded():
    rows = overlap([_f("kube-linter", "sorted-keys", "other")])
    assert rows == []


def test_kinds_filter_drops_objects_one_tool_never_scores():
    rows = overlap([_f("kube-linter", "access-to-secrets", "security", kind="ClusterRole")],
                   kinds={"Deployment"})
    assert rows == []
