import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "deletion_commits", Path(__file__).parent.parent / "scripts" / "deletion_commits.py")
deletion_commits = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deletion_commits)

TAGS = {"a": ["v1", "v2", "v3"]}


def row(presence, gone="1", category="security", repo="a"):
    return {"repo": repo, "presence": presence, "removed_object_gone": gone, "category": category}


def test_deletions_are_counted_on_the_tag_pair_where_they_happen():
    rows = [row("110"), row("110"), row("100")]
    assert deletion_commits.deletion_steps(rows, TAGS) == {("a", "v2", "v3"): 2, ("a", "v1", "v2"): 1}


def test_fixes_and_other_category_are_left_out():
    rows = [row("110", gone="0"), row("110", category="other")]
    assert deletion_commits.deletion_steps(rows, TAGS) == {}
