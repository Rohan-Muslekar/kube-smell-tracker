from kst.normalize import Finding
from kst.track import classify, track
from dataclasses import replace

import pytest


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


WEB = ("Deployment", "", "web")


def test_removed_with_object_deleted():
    objects = {("r", "v1"): {WEB}, ("r", "v2"): set()}
    rows = track([_f("v1")], {"r": ["v1", "v2"]}, objects)
    assert rows[0]["removed"] == 1 and rows[0]["removed_object_gone"] == 1


def test_removed_while_object_stays_is_a_candidate_fix():
    objects = {("r", "v1"): {WEB}, ("r", "v2"): {WEB}}
    rows = track([_f("v1")], {"r": ["v1", "v2"]}, objects)
    assert rows[0]["removed"] == 1 and rows[0]["removed_object_gone"] == 0


def test_introduced_with_new_object():
    objects = {("r", "v1"): set(), ("r", "v2"): {WEB}}
    rows = track([_f("v2")], {"r": ["v1", "v2"]}, objects)
    assert rows[0]["introduced"] == 1 and rows[0]["introduced_new_object"] == 1


def test_introduced_on_existing_object():
    objects = {("r", "v1"): {WEB}, ("r", "v2"): {WEB}}
    rows = track([_f("v2")], {"r": ["v1", "v2"]}, objects)
    assert rows[0]["introduced"] == 1 and rows[0]["introduced_new_object"] == 0


@pytest.mark.parametrize("field,value", [
    ("repo", "another"), ("tool", "kube-score"), ("kind", "StatefulSet"),
    ("namespace", "production"), ("name", "api"), ("check", "another-check"),
])
def test_each_identity_field_separates_instances(field, value):
    first = _f("v1")
    second = replace(_f("v2"), **{field: value})
    rows = track([first, second], {"r": ["v1", "v2"], "another": ["v1", "v2"]})
    assert len(rows) == 2
    assert sorted(r["presence"] for r in rows) == ["01", "10"]


def test_duplicates_and_rendered_file_moves_do_not_inflate_transitions():
    findings = [_f("v1", file="base/web.yaml")] * 3
    findings += [_f("v2", file="rendered/all.yaml")] * 4
    row, = track(findings, {"r": ["v1", "v2", "v3"]})
    assert row["presence"] == "110"
    assert (row["persisted"], row["removed"], row["introduced"]) == (1, 1, 0)


def test_denser_tags_reveal_hidden_removal_and_reappearance():
    findings = [_f("v1"), _f("v3"), _f("v4"), _f("v6")]
    sparse, = track(findings, {"r": ["v1", "v6"]})
    dense, = track(findings, {"r": ["v1", "v2", "v3", "v4", "v5", "v6"]})
    assert sparse["persisted"] == 1
    assert dense["presence"] == "101101"
    assert (dense["removed"], dense["reappeared"], dense["persisted"]) == (2, 2, 1)


def test_repeated_removals_split_fix_and_object_deletion():
    tags = ["v1", "v2", "v3", "v4"]
    objects = {("r", tag): ({WEB} if tag != "v4" else set()) for tag in tags}
    row, = track([_f("v1"), _f("v3")], {"r": tags}, objects)
    assert row["removed"] == 2
    assert row["removed_object_gone"] == 1
    assert row["reappeared"] == 1
    assert row["introduced_new_object"] == 0


def test_same_name_in_other_namespace_does_not_hide_deletion():
    objects = {("r", "v1"): {WEB}, ("r", "v2"): {("Deployment", "other", "web")}}
    row, = track([_f("v1")], {"r": ["v1", "v2"]}, objects)
    assert row["removed_object_gone"] == 1


def test_missing_inventory_is_not_silently_a_fix():
    with pytest.raises(KeyError):
        track([_f("v1")], {"r": ["v1", "v2"]}, {("r", "v1"): {WEB}})


def test_unordered_findings_follow_supplied_tag_order():
    row, = track([_f("v10"), _f("v2")], {"r": ["v1", "v2", "v10"]})
    assert row["presence"] == "011"
    assert (row["introduced"], row["persisted"]) == (1, 1)


def test_empty_inputs_and_invalid_only_findings():
    assert classify([]) == []
    assert track([], {"r": ["v1"]}) == []
    assert track([_f("invalid")], {"r": ["v1"]}) == []
