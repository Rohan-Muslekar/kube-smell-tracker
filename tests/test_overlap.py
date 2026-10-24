from kst.normalize import Finding
from kst.overlap import overlap, overlap_summary


def _f(tool, check, category, kind="Deployment", name="web", version="v1"):
    return Finding(repo="r", version=version, tool=tool, check=check, category=category,
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


def test_object_counted_once_across_tags():
    # The same object and category at three tags is one pair, "both" because both tools agree at v2.
    rows = overlap([_f("kube-linter", "run-as-non-root", "security", version=v) for v in ("v1", "v2", "v3")]
                   + [_f("kube-score", "container-security-context-user-group-id", "security", version="v2")])
    assert overlap_summary(rows) == [{"category": "security", "linter_only": 0, "score_only": 0, "both": 1}]
