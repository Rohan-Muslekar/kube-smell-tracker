import importlib.util
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
