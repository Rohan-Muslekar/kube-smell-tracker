"""Recount first-tag instances and real fixes per category under every category rating sheet.

Usage: python3 scripts/category_sensitivity.py [--out results/category_sensitivity.csv]

The category result (security is what gets fixed) should not depend on who drew the category
map. Each sheet in data/category_validation/ relabels every (tool, check); this script applies
each labelling to out/instances.csv and counts, per category, the instances present at the
first tag and the real fixes among them (a removal that leaves the object in place, minus the
kube-score gRPC-probe artifact, as in kst.survival_km).

It also asks whether one check carries the result: for every security check with a fix, the
map is rerun with that check moved to resource (sheet name `map_move_<tool>:<check>`).
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kst.survival_km import is_fix  # noqa: E402

SHEETS = {
    "map": "data/category_validation/map_as_rater.csv",
    "llm": "data/category_validation/llm_rater.csv",
    "rater1_ai_assisted": "data/category_validation/category_rater_1.csv",
    "rater2_ai_assisted": "data/category_validation/m4_rater2.csv",
}


def load_labels(path):
    with open(path, newline="") as handle:
        return {(r["tool"], r["check"]): r["category"].strip().casefold()
                for r in csv.DictReader(handle)}


def fixes_by_category(instances, labels):
    """Return {category: {"baseline": n, "fixes": n}} with categories taken from `labels`."""
    counts = defaultdict(lambda: {"baseline": 0, "fixes": 0})
    for row in instances:
        key = (row["tool"], row["check"])
        if key not in labels:
            raise KeyError(f"{key[0]},{key[1]} is not rated in the sheet")
        cell = counts[labels[key]]
        if row["at_baseline"] == "1":
            cell["baseline"] += 1
        if is_fix(row):
            cell["fixes"] += 1
    return {category: dict(cell) for category, cell in sorted(counts.items())}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--instances", default=ROOT / "out" / "instances.csv", type=Path)
    parser.add_argument("--out", default=ROOT / "results" / "category_sensitivity.csv", type=Path)
    args = parser.parse_args()
    with open(args.instances, newline="") as handle:
        instances = list(csv.DictReader(handle))
    labellings = {sheet: load_labels(ROOT / path) for sheet, path in SHEETS.items()}
    base = labellings["map"]
    fixed = sorted({(r["tool"], r["check"]) for r in instances
                    if base[(r["tool"], r["check"])] == "security" and is_fix(r)})
    for key in fixed:
        labellings[f"map_move_{key[0]}:{key[1]}"] = {**base, key: "resource"}
    rows = []
    for sheet, labels in labellings.items():
        for category, cell in fixes_by_category(instances, labels).items():
            rows.append({"sheet": sheet, "category": category, **cell})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sheet", "category", "baseline", "fixes"])
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        rate = row["fixes"] / row["baseline"] if row["baseline"] else 0
        print(f"{row['sheet']:58} {row['category']:9} baseline {row['baseline']:4}  "
              f"fixes {row['fixes']:2}  rate {rate:.3f}")


if __name__ == "__main__":
    main()
