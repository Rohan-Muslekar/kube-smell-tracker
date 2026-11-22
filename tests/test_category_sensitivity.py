import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "category_sensitivity", Path(__file__).parent.parent / "scripts" / "category_sensitivity.py")
category_sensitivity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(category_sensitivity)


def inst(check, removed="0", gone="0", baseline="1", tool="kube-linter", category="security"):
    return {"tool": tool, "check": check, "category": category, "at_baseline": baseline,
            "removed": removed, "removed_object_gone": gone}


def test_instances_take_the_sheet_category_not_the_map_category():
    rows = [inst("a", removed="1"), inst("b")]
    labels = {("kube-linter", "a"): "resource", ("kube-linter", "b"): "security"}
    assert category_sensitivity.fixes_by_category(rows, labels) == {
        "resource": {"baseline": 1, "fixes": 1}, "security": {"baseline": 1, "fixes": 0}}


def test_deletions_and_the_probe_artifact_are_not_fixes():
    rows = [inst("a", removed="1", gone="1"),
            inst("pod-probes-identical", removed="1", tool="kube-score")]
    labels = {("kube-linter", "a"): "security", ("kube-score", "pod-probes-identical"): "resource"}
    assert category_sensitivity.fixes_by_category(rows, labels) == {
        "resource": {"baseline": 1, "fixes": 0}, "security": {"baseline": 1, "fixes": 0}}


def test_a_check_missing_from_the_sheet_is_an_error():
    try:
        category_sensitivity.fixes_by_category([inst("a")], {})
    except KeyError as error:
        assert "kube-linter" in str(error)
    else:
        raise AssertionError("expected KeyError")


def test_fixes_count_only_instances_present_at_the_first_tag():
    rows = [inst("a", removed="1"), inst("a", removed="1", baseline="0")]
    labels = {("kube-linter", "a"): "security"}
    assert category_sensitivity.fixes_by_category(rows, labels) == {
        "security": {"baseline": 1, "fixes": 1}}
