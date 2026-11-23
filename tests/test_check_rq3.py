import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "check_rq3", Path(__file__).parent.parent / "scripts" / "check_rq3.py")
check_rq3 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_rq3)

TAGS = ["v1", "v2", "v3"]


def test_transition_on_its_consecutive_pair_passes():
    assert check_rq3.step_problem("110", TAGS, "fixed", "v2", "v3") is None
    assert check_rq3.step_problem("011", TAGS, "introduced", "v1", "v2") is None


def test_pair_that_skips_a_tag_is_reported():
    assert "not consecutive" in check_rq3.step_problem("100", TAGS, "fixed", "v1", "v3")


def test_pair_where_the_presence_does_not_change_is_reported():
    assert "no fixed" in check_rq3.step_problem("110", TAGS, "fixed", "v1", "v2")


def _row(name, transition="fixed"):
    return {"repo": "r", "object_kind": "Deployment", "namespace": "ns", "object_name": name,
            "check": "c", "from_tag": "v1", "to_tag": "v2", "transition": transition,
            "commit_url": "https://example.org/commit/abc1234"}


def test_rows_whose_instance_is_not_in_out_are_listed_apart_from_problems():
    # A trace made on stored manifests can name an object that rendering removes
    # (a patch fragment); that is not a broken trace, but it must be listed.
    presence = {("r", "Deployment", "ns", "kept", "c"): "10"}
    tags = {"r": ["v1", "v2"]}
    rows = [_row("kept"), _row("fragment"), _row("kept", "introduced")]
    problems, absent = check_rq3.check_rows(rows, presence, tags, lambda *a: True)
    assert [line for line, _ in absent] == [3]
    assert [line for line, _ in problems] == [4]
