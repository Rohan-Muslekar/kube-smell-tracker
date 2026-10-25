"""Prepare independent rating sheets and calculate pre-adjudication agreement."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

CATEGORIES = {"security", "resource", "image", "hygiene", "other"}


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


def agreement(mapping, first, second):
    expected, a, b = keyed(mapping), keyed(first), keyed(second)
    if expected.keys() != a.keys() or expected.keys() != b.keys():
        raise ValueError("Both rating sheets must cover exactly the mapping's checks")
    raters = []
    for sheet in (a, b):
        names = {row.get("rater", "").strip() for row in sheet.values()}
        if len(names) != 1 or not all(names):
            raise ValueError("Each sheet needs one nonempty rater name")
        raters.append(next(iter(names)))
        for row in sheet.values():
            if row.get("category") not in CATEGORIES or not row.get("rationale", "").strip():
                raise ValueError("Every rating needs a valid category and rationale")
    if raters[0].casefold() == raters[1].casefold():
        raise ValueError("Two distinct raters are required")
    n = len(expected)
    ca = Counter(row["category"] for row in a.values())
    cb = Counter(row["category"] for row in b.values())
    matches = sum(a[k]["category"] == b[k]["category"] for k in expected)
    observed = matches / n
    chance = sum(ca[c] * cb[c] for c in CATEGORIES) / (n * n)
    disagreements = [dict(tool=k[0], check=k[1],
                          rater_1_category=a[k]["category"], rater_2_category=b[k]["category"],
                          rater_1_rationale=a[k]["rationale"], rater_2_rationale=b[k]["rationale"],
                          adjudicated_category="", decision_rationale="", adjudicator="", date="")
                     for k in sorted(expected) if a[k]["category"] != b[k]["category"]]
    return {"checks": n, "raters": raters, "agreements": matches,
            "disagreements": len(disagreements), "percent_agreement": observed * 100,
            "expected_agreement": chance,
            "cohens_kappa": (observed - chance) / (1 - chance) if chance < 1 else None,
            "kappa_note": "Undefined when expected agreement is 1" if chance == 1 else "",
            "stage": "independent ratings, before adjudication"}, disagreements


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "calculate"))
    parser.add_argument("--mapping", type=Path, default=Path("data/check_categories.csv"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rater-1", type=Path)
    parser.add_argument("--rater-2", type=Path)
    args = parser.parse_args()
    try:
        mapping = read_rows(args.mapping)
        keys = keyed(mapping)
        if args.mode == "prepare":
            rows = [dict(tool=t, check=c, rater="", category="", rationale="") for t, c in sorted(keys)]
            files = {f"category_rater_{i}.csv": rows for i in (1, 2)}
            fields = list(rows[0])
        else:
            if not args.rater_1 or not args.rater_2:
                raise ValueError("calculate requires --rater-1 and --rater-2")
            summary, rows = agreement(mapping, read_rows(args.rater_1), read_rows(args.rater_2))
            files = {"category_disagreements.csv": rows, "category_agreement.json": summary}
            fields = ["tool", "check", "rater_1_category", "rater_2_category", "rater_1_rationale",
                      "rater_2_rationale", "adjudicated_category", "decision_rationale", "adjudicator", "date"]
        args.out.mkdir(parents=True, exist_ok=True)
        if any((args.out / name).exists() for name in files):
            raise ValueError("Output files already exist; use a new output directory to preserve ratings and decisions")
        for name, content in files.items():
            if name.endswith(".json"):
                (args.out / name).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
            else:
                write_rows(args.out / name, fields, content)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
