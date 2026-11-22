"""Compare fully completed human RQ3 recoding with the original coder's data.

This intentionally *refuses* to reveal original labels until all 20 second-coder
labels have been entered. Do not run until blind human coding is finished.
"""
import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kst.category_validation import cohens_kappa, read_rows, write_all  # noqa: E402

KEY_FIELDS = (
    "repo", "object_kind", "namespace", "object_name", "check",
    "from_tag", "to_tag", "transition",
)
CATEGORIES = (
    "real_fix", "side_effect_of_fix", "analyzer_artifact",
    "new_object", "object_deleted",
)
REPORT_FIELDS = (*KEY_FIELDS, "first_coder", "second_coder", "commit_url",
                 "evidence_url", "adjudicated_class", "decision_rationale")


def field(row, name):
    return (row.get(name) or "").strip()


def key(row):
    return tuple(field(row, item) for item in KEY_FIELDS)


def index_rows(rows, name):
    by_key = {}
    for number, row in enumerate(rows, start=2):
        k = key(row)
        if not all(k[i] for i in (0, 1, 3, 4, 5, 6, 7)):
            raise ValueError(f"{name} line {number}: incomplete key")
        if k in by_key:
            raise ValueError(f"{name} line {number}: duplicate key: {k}")
        by_key[k] = row
    return by_key


def validate_blind_sheet(rows, expected_size=20):
    """Do this *before* accessing the first coder's CSV."""
    if len(rows) != expected_size:
        raise ValueError(f"Sheet must contain {expected_size} rows; found {len(rows)}")
    indexed = index_rows(rows, "Second-coder sheet")
    for number, row in enumerate(rows, start=2):
        label = field(row, "classification")
        if not label:
            raise ValueError(f"Second-coder sheet line {number}: classification is blank. "
                             "Finish independent human coding before comparing.")
        if label not in CATEGORIES:
            raise ValueError(f"Second-coder sheet line {number}: invalid classification {label!r}")
    return indexed


def calculate(sheet_rows, source_rows):
    """Return summary and disagreement ledger without altering either source file."""
    second = validate_blind_sheet(sheet_rows)
    first = index_rows(source_rows, "Original investigations")
    missing = set(second) - set(first)
    if missing:
        raise ValueError(f"{len(missing)} recoded rows have no unique match in source")

    ordered = sorted(second)
    first_labels = []
    second_labels = []
    disagreements = []
    for k in ordered:
        a, b = first[k], second[k]
        first_class, second_class = field(a, "classification"), field(b, "classification")
        if first_class not in CATEGORIES:
            raise ValueError(f"Original row {k} has unexpected class {first_class!r}")
        first_labels.append(first_class)
        second_labels.append(second_class)
        if first_class != second_class:
            disagreements.append(dict(zip(KEY_FIELDS, k), first_coder=first_class,
                                      second_coder=second_class,
                                      commit_url=field(a, "commit_url") or field(b, "commit_url"),
                                      evidence_url=field(a, "evidence_url"),
                                      adjudicated_class="", decision_rationale=""))
    matches = sum(a == b for a, b in zip(first_labels, second_labels))
    n = len(ordered)
    ca, cb = Counter(first_labels), Counter(second_labels)
    chance = sum(ca[c] * cb[c] for c in CATEGORIES) / (n*n)
    summary = {
        "stage": "independent coding, prior to adjudication",
        "n": n,
        "agreements": matches,
        "disagreements": len(disagreements),
        "percent_agreement": 100 * matches / n,
        "expected_agreement": chance,
        "cohens_kappa": cohens_kappa(first_labels, second_labels),
        "kappa_note": "Undefined when expected agreement is 1" if chance == 1 else "",
        "first_coder_counts": dict(sorted(ca.items())),
        "second_coder_counts": dict(sorted(cb.items())),
        "judged_rows": judged_agreement(ordered, first_labels, second_labels),
    }
    return summary, disagreements


def judged_agreement(keys, first_labels, second_labels):
    """Agreement on the rows where the class is a judgment.

    The sheet shows the transition, and an object_deleted transition leaves only one
    possible class, so those rows agree by construction and inflate kappa.
    """
    transition = KEY_FIELDS.index("transition")
    pairs = [(a, b) for k, a, b in zip(keys, first_labels, second_labels)
             if k[transition] != "object_deleted"]
    if not pairs:
        return {"n": 0, "agreements": 0, "cohens_kappa": None}
    first, second = zip(*pairs)
    return {"n": len(pairs), "agreements": sum(a == b for a, b in pairs),
            "excluded_transition": "object_deleted",
            "cohens_kappa": cohens_kappa(first, second)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sheet", type=Path, default=ROOT / "data/rq3_recode_sheet.csv")
    parser.add_argument("--source", type=Path, default=ROOT / "data/rq3_investigations.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "results/rq3_agreement")
    args = parser.parse_args(argv)
    try:
        # Deliberately validate *before* reading original labels.
        sheet = read_rows(args.sheet)
        validate_blind_sheet(sheet)
        source = read_rows(args.source)
        summary, differences = calculate(sheet, source)
        write_all(args.out, {
            "rq3_agreement.json": (None, summary),
            "rq3_disagreements.csv": (REPORT_FIELDS, differences),
        })
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))
    kappa = summary["cohens_kappa"]
    print(f"Agreement: {summary['agreements']}/{summary['n']} "
          f"({summary['percent_agreement']:.1f}%)")
    print(f"Cohen's kappa: {kappa:.4f}" if kappa is not None
          else "Cohen's kappa: undefined (expected agreement = 1)")
    judged = summary["judged_rows"]
    if judged["cohens_kappa"] is not None:
        print(f"Cohen's kappa without object_deleted rows ({judged['n']} rows): "
              f"{judged['cohens_kappa']:.4f}")
    print(f"Disagreements: {summary['disagreements']}")
    print(f"Wrote {args.out / 'rq3_agreement.json'} "
          f"and {args.out / 'rq3_disagreements.csv'}")


if __name__ == "__main__":
    main()
