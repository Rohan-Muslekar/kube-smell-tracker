"""Tests for the fully blinded RQ3 comparison and shared Cohen's kappa."""
import csv
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rq3_agreement.py"
spec = importlib.util.spec_from_file_location("rq3_agreement", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(i, label, commit_url="https://example.org/commit/abc"):
    return dict(repo="flux2", object_kind="Deployment", namespace="flux-system",
                object_name=f"object-{i}", check="no-liveness-probe", from_tag="v1",
                to_tag="v2", transition="introduced", classification=label,
                commit_url=commit_url, evidence_url="https://example.org/evidence")


def fixture():
    labels = (list(mod.CATEGORIES) * 4)  # 20 examples, five categories
    source = [row(i, label) for i, label in enumerate(labels)]
    sheet = [dict(r, classification=r["classification"])
             for r in source]
    return source, sheet


def test_perfect_agreement():
    source, sheet = fixture()
    summary, differences = mod.calculate(sheet, source)
    assert summary["n"] == 20
    assert summary["agreements"] == 20
    assert summary["percent_agreement"] == 100
    assert summary["cohens_kappa"] == pytest.approx(1.0)
    assert differences == []


def test_one_disagreement_has_ledger_and_lower_kappa():
    source, sheet = fixture()
    sheet[0]["classification"] = "new_object"
    summary, differences = mod.calculate(sheet, source)
    assert summary["agreements"] == 19
    assert summary["percent_agreement"] == 95.0
    assert 0 < summary["cohens_kappa"] < 1.0
    assert len(differences) == 1
    assert differences[0]["first_coder"] == "real_fix"
    assert differences[0]["second_coder"] == "new_object"
    assert differences[0]["adjudicated_class"] == ""


def test_blank_sheet_is_rejected_before_original_is_needed():
    source, sheet = fixture()
    sheet[7]["classification"] = ""
    with pytest.raises(ValueError, match="Finish independent human coding"):
        mod.validate_blind_sheet(sheet)
    with pytest.raises(ValueError, match="classification is blank"):
        mod.calculate(sheet, source)


def test_invalid_class_duplicate_and_count_rejected():
    _, sheet = fixture()
    bad = [dict(r) for r in sheet]
    bad[0]["classification"] = "made_up_class"
    with pytest.raises(ValueError, match="invalid classification"):
        mod.validate_blind_sheet(bad)
    bad = [dict(r) for r in sheet]
    bad[0]["object_name"] = bad[1]["object_name"]
    with pytest.raises(ValueError, match="duplicate key"):
        mod.validate_blind_sheet(bad)
    with pytest.raises(ValueError, match="must contain 20"):
        mod.validate_blind_sheet(sheet[:19])


def test_missing_source_match_rejected():
    source, sheet = fixture()
    source.pop()
    with pytest.raises(ValueError, match="no unique match"):
        mod.calculate(sheet, source)


def test_agreement_helper_undefined_when_all_same():
    from kst.category_validation import cohens_kappa
    assert cohens_kappa(["a", "a"], ["a", "a"]) is None
    assert cohens_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0
    with pytest.raises(ValueError):
        cohens_kappa(["a"], [])


def test_kappa_is_also_reported_without_rows_the_transition_already_decides():
    # An object_deleted transition can only be coded object_deleted, so those rows
    # agree by construction; the judged kappa leaves them out.
    source, sheet = fixture()
    for rows in (source, sheet):
        for r in rows:
            if r["classification"] == "object_deleted":
                r["transition"] = "object_deleted"
    sheet[0]["classification"] = "new_object"
    summary, _ = mod.calculate(sheet, source)
    judged = summary["judged_rows"]
    assert judged["n"] == 16
    assert judged["agreements"] == 15
    assert judged["cohens_kappa"] < summary["cohens_kappa"]
