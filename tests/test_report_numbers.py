import importlib.util
import pytest
import csv
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "report_numbers", Path(__file__).parent.parent / "scripts" / "report_numbers.py")
report_numbers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report_numbers)


def units(table):
    """(category, survived) units from (survived, lost) counts per category in CATS order."""
    return [(cat, ok) for cat, (s, l) in zip(report_numbers.CATS, table)
            for ok in [True] * s + [False] * l]


def test_chi_square_matches_scipy_on_the_first_tag_instances():
    # scipy.stats.chi2_contingency(correction=False) gives 24.59, p = 1.88e-05 on this table.
    x, p, v, n = report_numbers.chi_square(units([(175, 62), (350, 61), (56, 16), (95, 6)]))
    assert round(x, 2) == 24.59
    assert abs(p - 1.8809e-05) < 1e-08
    assert round(v, 3) == 0.173
    assert n == 821


def test_chi_square_is_zero_when_every_category_survives_alike():
    x, p, _, _ = report_numbers.chi_square(units([(8, 2), (4, 1), (8, 2), (4, 1)]))
    assert abs(x) < 1e-12
    assert abs(p - 1) < 1e-9


def test_exclusion_filters_every_headline_and_both_pair_rules():
    def row(repo, check, presence, removed=0, gone=0):
        return dict(repo=repo, tool="kube-linter", check=check, category="security",
                    kind="Deployment", namespace="", name="web", presence=presence,
                    removed=removed, removed_object_gone=gone, persisted=0,
                    introduced=0, introduced_new_object=0, reappeared=0)
    rows = [row("istio", "a", "11"), row("flux2", "a", "10", 1, 1),
            row("kept", "a", "11"), row("kept", "b", "10", 1)]
    result = report_numbers.headline_numbers(rows, ["istio", "flux2"])
    assert result["systems"] == ["kept"]
    assert result["instances"] == result["baseline"] == 2
    assert result["survival_percent"] == 50
    assert result["object_deletions"] == 0
    assert result["deletion_percent"] == 0
    assert result["fixes_after_known_artifacts"] == 1
    assert result["pair_tests"]["any"]["table_survived_lost"]["security"] == [1, 0]
    assert result["pair_tests"]["all"]["table_survived_lost"]["security"] == [0, 1]


def test_degenerate_test_is_not_reported_as_significant():
    assert report_numbers.chi_square([]) == (None, None, None, 0)
    assert report_numbers.chi_square([("security", True), ("image", True)]) == (None, None, None, 2)


def test_two_category_test_uses_one_degree_of_freedom():
    x, p, v, n = report_numbers.chi_square(units([(8, 2), (2, 8), (0, 0), (0, 0)]))
    assert x == pytest.approx(7.2)
    assert p == pytest.approx(0.00729035809153564)


def test_exclude_cli_writes_filtered_headlines(tmp_path):
    source = Path(__file__).parent.parent / "out" / "instances.csv"
    report_numbers.main(["--instances", str(source), "--exclude", "istio", "--out", str(tmp_path)])
    result = json.loads((tmp_path / "headlines.json").read_text())
    with source.open(newline="") as stream:
        expected = report_numbers.headline_numbers(list(csv.DictReader(stream)), ["istio"])
    assert result == expected
    assert "istio" not in result["systems"]
    assert set(result["pair_tests"]) == {"any", "all"}


def test_unknown_exclusion_is_rejected(tmp_path):
    with pytest.raises(SystemExit):
        report_numbers.main(["--exclude", "typo", "--out", str(tmp_path)])


def test_small_p_values_keep_a_significant_digit():
    assert report_numbers.fmt_p(0.0028) == "$p=0.003$"
    assert report_numbers.fmt_p(0.0005) == "$p<0.001$"
    assert report_numbers.fmt_p(0.081) == "$p=0.08$"
