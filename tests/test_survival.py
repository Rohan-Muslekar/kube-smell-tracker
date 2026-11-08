import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "survival", Path(__file__).parent.parent / "scripts" / "survival.py")
survival = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(survival)


def _row(repo, presence, category="security"):
    return {"repo": repo, "category": category, "presence": presence}


def test_share_of_first_tag_instances_per_tag():
    rows = [_row("a", "111"), _row("a", "110"), _row("a", "100"), _row("a", "011")]
    result = survival.series(rows, {"a": ["v1", "v2", "v3"]})
    assert [i for i, _ in result["a"]] == [0, 1, 2]
    assert [share for _, share in result["a"]] == pytest.approx([100.0, 200 / 3, 100 / 3])


def test_other_category_and_systems_without_first_tag_smells_are_left_out():
    rows = [_row("a", "11"), _row("a", "10", category="other"), _row("b", "01")]
    assert survival.series(rows, {"a": ["v1", "v2"], "b": ["v1", "v2"]}) == {"a": [(0, 100.0), (1, 100.0)]}
