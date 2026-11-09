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
