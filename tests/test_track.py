from kst.normalize import Finding
from kst.track import classify, track


def _f(version, name="web", file="deploy/web.yaml", check="run-as-non-root"):
    return Finding(repo="r", version=version, tool="kube-linter", check=check, category="security",
                   kind="Deployment", namespace="", name=name, file=file)


def test_classify_persisted():
    assert classify([True, True]) == ["persisted"]


def test_classify_introduced():
    assert classify([False, True]) == ["introduced"]


def test_classify_removed_then_reappeared():
    assert classify([True, False, True]) == ["removed", "reappeared"]


def test_classify_introduced_removed_reappeared():
    assert classify([False, True, False, True]) == ["introduced", "removed", "reappeared"]


def test_classify_single_version():
    assert classify([True]) == []


def test_classify_absent_pair():
    assert classify([True, False, False]) == ["removed", "absent"]


def test_duplicate_key_counts_once():
    rows = track([_f("v1"), _f("v1")], {"r": ["v1"]})
    assert len(rows) == 1
    assert rows[0]["presence"] == "1" and rows[0]["at_baseline"] == 1


def test_invalid_version_not_counted_as_removed():
    # v2 is missing from the valid versions, so its (empty) results are ignored.
    rows = track([_f("v1"), _f("v3")], {"r": ["v1", "v3"]})
    assert rows[0]["presence"] == "11"
    assert rows[0]["persisted"] == 1 and rows[0]["removed"] == 0


def test_file_move_keeps_identity():
    rows = track([_f("v1", file="a.yaml"), _f("v2", file="b.yaml")], {"r": ["v1", "v2"]})
    assert len(rows) == 1 and rows[0]["persisted"] == 1


def test_counts_per_label():
    rows = track([_f("v2"), _f("v4")], {"r": ["v1", "v2", "v3", "v4"]})
    r = rows[0]
    assert r["presence"] == "0101" and r["at_baseline"] == 0
    assert (r["introduced"], r["persisted"], r["removed"], r["reappeared"]) == (1, 0, 1, 1)
