"""Prepare independent rating sheets and calculate pre-adjudication agreement."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

CATEGORIES = {"security", "resource", "image", "hygiene", "other"}
DISAGREEMENT_FIELDS = ["tool", "check", "mapped_category", "rater_1_category", "rater_2_category",
                       "rater_1_rationale", "rater_2_rationale", "adjudicated_category",
                       "decision_rationale", "adjudicator", "date"]


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def keyed(rows):
    result = {}
    for row in rows:
        key = (row["tool"], row["check"])
        if not all(key) or key in result:
            raise ValueError(f"Missing or duplicate check identity: {key}")
        result[key] = row
    if not result:
        raise ValueError("No checks supplied")
    return result


def text(row, field):
    """A stripped cell; csv.DictReader gives None for columns missing from a short row."""
    return (row.get(field) or "").strip()


def agreement(expected, first, second):
    """`expected` is the mapping keyed by (tool, check), as returned by keyed()."""
    a, b = keyed(first), keyed(second)
    if expected.keys() != a.keys() or expected.keys() != b.keys():
        raise ValueError("Both rating sheets must cover exactly the mapping's checks")
    raters = []
    for number, sheet in enumerate((a, b), 1):
        names = {text(row, "rater") for row in sheet.values()}
        if len(names) != 1 or not all(names):
            raise ValueError(f"Sheet {number} needs one nonempty rater name")
        raters.append(next(iter(names)))
        for key, row in sheet.items():
            row["category"] = text(row, "category").casefold()
            if row["category"] not in CATEGORIES or not text(row, "rationale"):
                raise ValueError(f"Sheet {number}, {key[0]},{key[1]}: every rating needs a valid category and rationale")
    if raters[0].casefold() == raters[1].casefold():
        raise ValueError("Two distinct raters are required")
    n = len(expected)
    ca = Counter(row["category"] for row in a.values())
    cb = Counter(row["category"] for row in b.values())
    matches = sum(a[k]["category"] == b[k]["category"] for k in expected)
    observed = matches / n
    chance = sum(ca[c] * cb[c] for c in CATEGORIES) / (n * n)
    mapped = {k: text(row, "category") for k, row in expected.items()}
    disagreements = [dict(tool=k[0], check=k[1], mapped_category=mapped[k],
                          rater_1_category=a[k]["category"], rater_2_category=b[k]["category"],
                          rater_1_rationale=a[k]["rationale"], rater_2_rationale=b[k]["rationale"],
                          adjudicated_category="", decision_rationale="", adjudicator="", date="")
                     for k in sorted(expected) if a[k]["category"] != b[k]["category"]]
    # Agreement alone is not enough: both raters may agree on a category the map does not use.
    map_differences = [dict(tool=k[0], check=k[1], mapped_category=mapped[k], agreed_category=a[k]["category"])
                       for k in sorted(expected)
                       if a[k]["category"] == b[k]["category"] and mapped[k] and a[k]["category"] != mapped[k]]
    return {"checks": n, "raters": raters, "agreements": matches,
            "disagreements": len(disagreements), "percent_agreement": observed * 100,
            "expected_agreement": chance,
            "cohens_kappa": (observed - chance) / (1 - chance) if chance < 1 else None,
            "kappa_note": "Undefined when expected agreement is 1" if chance == 1 else "",
            "agreed_differs_from_map": len(map_differences),
            "stage": "independent ratings, before adjudication"}, disagreements, map_differences


def write_all(out, files):
    """Write every output or none: files go to temporary names first and are renamed at the end."""
    out.mkdir(parents=True, exist_ok=True)
    if any((out / name).exists() for name in files):
        raise ValueError("Output files already exist; use a new output directory to preserve ratings and decisions")
    staged = []
    try:
        for name, (fields, content) in files.items():
            tmp = out / f".{name}.tmp"
            staged.append(tmp)
            if name.endswith(".json"):
                tmp.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
            else:
                write_rows(tmp, fields, content)
        for tmp in staged:
            tmp.rename(out / tmp.name[1:-4])
    finally:
        for tmp in staged:
            tmp.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "calculate"))
    parser.add_argument("--mapping", type=Path, default=Path("data/check_categories.csv"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rater-1", type=Path)
    parser.add_argument("--rater-2", type=Path)
    args = parser.parse_args(argv)
    try:
        keys = keyed(read_rows(args.mapping))
        if args.mode == "prepare":
            rows = [dict(tool=t, check=c, rater="", category="", rationale="") for t, c in sorted(keys)]
            files = {f"category_rater_{i}.csv": (list(rows[0]), rows) for i in (1, 2)}
        else:
            if not args.rater_1 or not args.rater_2:
                raise ValueError("calculate requires --rater-1 and --rater-2")
            summary, rows, changes = agreement(keys, read_rows(args.rater_1), read_rows(args.rater_2))
            files = {"category_disagreements.csv": (DISAGREEMENT_FIELDS, rows),
                     "category_map_differences.csv": (["tool", "check", "mapped_category", "agreed_category"], changes),
                     "category_agreement.json": (None, summary)}
        write_all(args.out, files)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
