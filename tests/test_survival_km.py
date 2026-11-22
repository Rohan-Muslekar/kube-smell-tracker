from datetime import date, timedelta

import pytest

from kst.survival_km import cumulative_incidence, curves, incidence_curves, kaplan_meier


def test_five_instances_hand_computed():
    # Day 1: 4/5 survive. Day 2: event and censor tied, 4 at risk -> 3/5.
    # Day 3: 2 at risk, one event -> 3/10. Day 4: final censor, unchanged.
    points = kaplan_meier([(1, True), (2, True), (2, False), (3, True), (4, False)])
    assert [p["at_risk"] for p in points] == [5, 4, 2, 1]
    assert [p["survival"] for p in points] == pytest.approx([.8, .6, .3, .3])
    assert [p["events"] for p in points] == [1, 1, 1, 0]
    assert [p["censored"] for p in points] == [0, 1, 0, 1]


def test_late_entry_reappearance_and_censoring():
    dates = {"r": [date(2020, 1, 1) + timedelta(days=i) for i in range(5)]}
    rows = [dict(repo="r", category="security", presence=p) for p in ("00101", "00001", "11111")]
    points = curves(rows, dates, "repo")
    assert [p["time_days"] for p in points] == [0, 1, 4]
    assert [p["at_risk"] for p in points] == [3, 2, 1]
    assert [p["survival"] for p in points] == [1, .5, .5]


def test_empty_and_all_events():
    assert kaplan_meier([]) == []
    assert kaplan_meier([(1, True)] * 5)[0]["survival"] == 0


def test_alignment_error():
    with pytest.raises(ValueError):
        curves([dict(repo="r", category="image", presence="11")], {"r": [date.today()]}, "category")


def test_fix_curve_censors_deletions():
    # A removal by object deletion is not a fix: for the fix curve it is censored at that
    # tag, so only the instance whose object stayed counts as an event.
    dates = {"r": [date(2020, 1, 1) + timedelta(days=i) for i in range(3)]}
    rows = [dict(repo="r", category="security", presence="110", removed="1", removed_object_gone="1"),
            dict(repo="r", category="security", presence="110", removed="1", removed_object_gone="0"),
            dict(repo="r", category="security", presence="111", removed="0", removed_object_gone="0")]
    any_removal = curves(rows, dates, "repo")
    fix_only = curves(rows, dates, "repo", event="fix")
    assert [(p["time_days"], p["events"], p["censored"]) for p in any_removal] == [(2, 2, 1)]
    assert [(p["time_days"], p["events"], p["censored"]) for p in fix_only] == [(2, 1, 2)]
    assert fix_only[0]["survival"] == pytest.approx(2 / 3)


def test_cumulative_incidence_treats_deletion_as_a_competing_event():
    # Day 1: 4 at risk, one fix -> CIF_fix 1/4. Day 2: 3 at risk, one deletion; overall
    # survival before day 2 is 3/4, so CIF_deletion = 3/4 * 1/3 = 1/4. Day 3: one censored.
    # Day 4: the last one is fixed: survival before is 1/2, so CIF_fix = 1/4 + 1/2 = 3/4.
    points = cumulative_incidence([(1, "fix"), (2, "deletion"), (3, None), (4, "fix")])
    assert [p["at_risk"] for p in points] == [4, 3, 2, 1]
    assert [p["cif_fix"] for p in points] == pytest.approx([.25, .25, .25, .75])
    assert [p["cif_deletion"] for p in points] == pytest.approx([0, .25, .25, .25])


def test_incidence_curves_split_fixes_from_deletions():
    dates = {"r": [date(2020, 1, 1) + timedelta(days=i) for i in range(3)]}
    rows = [dict(repo="r", category="security", presence="110", removed="1", removed_object_gone=g,
                 tool="kube-linter", check="c") for g in ("0", "1")]
    points = incidence_curves(rows, dates, "category")
    assert [(p["fixes"], p["deletions"]) for p in points] == [(1, 1)]
    assert points[-1]["cif_fix"] == pytest.approx(.5)
