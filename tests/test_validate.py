import pytest

from kst.validate import output_problem


@pytest.mark.parametrize("text, problem", [
    ("", "empty output"),
    ("\n", "empty output"),
    ("Failed to score files", "not JSON"),
    ("null", "not a JSON array or object"),
    ('"x"', "not a JSON array or object"),
])
def test_bad_analyzer_output(tmp_path, text, problem):
    # kube-score prints nothing on stdout when it crashes; `jq empty` accepted that as valid.
    path = tmp_path / "out.json"
    path.write_text(text)
    assert output_problem(path) == problem


@pytest.mark.parametrize("text", ['{"Reports": null}', "[]"])
def test_good_analyzer_output(tmp_path, text):
    path = tmp_path / "out.json"
    path.write_text(text)
    assert output_problem(path) is None
