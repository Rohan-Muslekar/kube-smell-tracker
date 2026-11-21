from datetime import date, timedelta

import pytest

from kst.survival_km import curves, kaplan_meier


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
