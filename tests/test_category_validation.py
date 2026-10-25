import pytest

from kst.category_validation import agreement


def sheets(a, b):
    mapping = [{"tool": "tool", "check": str(i)} for i in range(len(a))]
    def ratings(categories, name):
        return [dict(row, rater=name, category=c, rationale="Check documentation")
                for row, c in zip(mapping, categories)]
    return mapping, ratings(a, "First"), ratings(b, "Second")


def test_known_agreement_and_disagreements():
    summary, disagreements = agreement(*sheets(
        ["security", "security", "resource", "resource"],
        ["security", "resource", "resource", "resource"]))
    assert summary["percent_agreement"] == 75
    assert summary["expected_agreement"] == 0.5
    assert summary["cohens_kappa"] == 0.5
    assert len(disagreements) == 1
    assert disagreements[0]["check"] == "1"
    assert disagreements[0]["adjudicated_category"] == ""


def test_single_category_kappa_is_undefined():
    summary, _ = agreement(*sheets(["security"], ["security"]))
    assert summary["percent_agreement"] == 100
    assert summary["cohens_kappa"] is None


@pytest.mark.parametrize("problem", ["missing", "duplicate", "blank", "invalid", "same_rater", "no_reason"])
def test_incomplete_or_invalid_ratings_rejected(problem):
    mapping, a, b = sheets(["security", "resource"], ["security", "resource"])
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
