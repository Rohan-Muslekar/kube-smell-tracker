import pytest

from kst import category_validation
from kst.category_validation import agreement


def sheets(a, b, mapped=None):
    mapping = [{"tool": "tool", "check": str(i), "category": (mapped or a)[i]} for i in range(len(a))]
    def ratings(categories, name):
        return [dict(row, rater=name, category=c, rationale="Check documentation")
                for row, c in zip(mapping, categories)]
    return mapping, ratings(a, "First"), ratings(b, "Second")


def keyed_sheets(a, b, mapped=None):
    mapping, first, second = sheets(a, b, mapped)
    return category_validation.keyed(mapping), first, second


def test_known_agreement_and_disagreements():
    summary, disagreements, _ = agreement(*keyed_sheets(
        ["security", "security", "resource", "resource"],
        ["security", "resource", "resource", "resource"]))
    assert summary["percent_agreement"] == 75
    assert summary["expected_agreement"] == 0.5
    assert summary["cohens_kappa"] == 0.5
    assert len(disagreements) == 1
    assert disagreements[0]["check"] == "1"
    assert disagreements[0]["adjudicated_category"] == ""


def test_single_category_kappa_is_undefined():
    summary, _, _ = agreement(*keyed_sheets(["security"], ["security"]))
    assert summary["percent_agreement"] == 100
    assert summary["cohens_kappa"] is None


@pytest.mark.parametrize("problem", ["missing", "duplicate", "blank", "invalid", "same_rater", "no_reason"])
def test_incomplete_or_invalid_ratings_rejected(problem):
    mapping, a, b = keyed_sheets(["security", "resource"], ["security", "resource"])
    if problem == "missing":
        b.pop()
    elif problem == "duplicate":
        b.append(b[0])
    elif problem == "blank":
        b[0]["category"] = ""
    elif problem == "invalid":
        b[0]["category"] = "unknown"
    elif problem == "same_rater":
        for row in b:
            row["rater"] = "First"
    else:
        b[0]["rationale"] = ""
    with pytest.raises(ValueError):
        agreement(mapping, a, b)


def test_short_row_is_rejected_with_a_clear_error():
    mapping, a, b = keyed_sheets(["security"], ["security"])
    b[0]["rationale"] = None  # csv.DictReader fills missing trailing columns with None
    with pytest.raises(ValueError, match="rationale"):
        agreement(mapping, a, b)


def test_category_spacing_and_case_are_ignored():
    mapping, a, b = keyed_sheets(["security", "resource"], ["security", "resource"])
    b[0]["category"] = " Security "
    summary, _, _ = agreement(mapping, a, b)
    assert summary["agreements"] == 2


def test_invalid_category_error_names_the_check():
    mapping, a, b = keyed_sheets(["security", "resource"], ["security", "resource"])
    b[1]["category"] = "unknown"
    with pytest.raises(ValueError, match=r"tool,1"):
        agreement(mapping, a, b)


def test_agreed_category_that_differs_from_map_is_listed():
    summary, disagreements, changes = agreement(*keyed_sheets(
        ["hygiene", "security"], ["hygiene", "resource"], mapped=["other", "security"]))
    assert summary["agreed_differs_from_map"] == 1
    assert [(c["check"], c["mapped_category"], c["agreed_category"]) for c in changes] == [("0", "other", "hygiene")]
    assert disagreements[0]["mapped_category"] == "security"


def run(*argv):
    category_validation.main(list(argv))


def fill(path, name, categories):
    rows = category_validation.read_rows(path)
    for row, category in zip(rows, categories):
        row.update(rater=name, category=category, rationale="Check documentation")
    category_validation.write_rows(path, list(rows[0]), rows)


@pytest.fixture
def rated(tmp_path):
    mapping = tmp_path / "map.csv"
    category_validation.write_rows(mapping, ["tool", "check", "category", "rationale"],
                                   [dict(tool="t", check=c, category="security", rationale="r") for c in "ab"])
    run("prepare", "--mapping", str(mapping), "--out", str(tmp_path / "sheets"))
    fill(tmp_path / "sheets" / "category_rater_1.csv", "First", ["security", "image"])
    fill(tmp_path / "sheets" / "category_rater_2.csv", "Second", ["security", "resource"])
    return ["calculate", "--mapping", str(mapping), "--rater-1", str(tmp_path / "sheets" / "category_rater_1.csv"),
            "--rater-2", str(tmp_path / "sheets" / "category_rater_2.csv")]


def test_short_csv_row_fails_with_usage_error_not_traceback(rated, tmp_path, capsys):
    sheet = tmp_path / "sheets" / "category_rater_2.csv"
    lines = sheet.read_text().splitlines()
    sheet.write_text("\n".join(lines[:-1] + ["t,b,Second,resource"]) + "\n")
    with pytest.raises(SystemExit) as stop:
        run(*rated, "--out", str(tmp_path / "result"))
    assert stop.value.code == 2
    assert "rationale" in capsys.readouterr().err


def test_failed_write_leaves_no_outputs_and_can_be_rerun(rated, tmp_path, monkeypatch):
    out = tmp_path / "result"
    real = category_validation.Path.write_text

    def broken(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(category_validation.Path, "write_text", broken)
    with pytest.raises(SystemExit):
        run(*rated, "--out", str(out))
    assert sorted(p.name for p in out.iterdir()) == []
    monkeypatch.setattr(category_validation.Path, "write_text", real)
    run(*rated, "--out", str(out))
    assert sorted(p.name for p in out.iterdir()) == [
        "category_agreement.json", "category_disagreements.csv", "category_map_differences.csv"]
